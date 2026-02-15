# migrations/versions/006_add_duty_planning_functions.py
"""
Миграция для добавления функций планирования дежурств
Добавляет:
- Функцию get_working_days_count для подсчета рабочих дней
- Функцию assign_yearly_duty_schedule для автоматического распределения дежурств на год
"""

migration = {
    "id": "006_add_duty_planning_functions",
    "description": "Add duty planning functions for automatic yearly scheduling",
    "up": [
        ## ========== ЧАСТЬ 1: ФУНКЦИЯ ПОДСЧЕТА РАБОЧИХ ДНЕЙ ==========
        """
        CREATE OR REPLACE FUNCTION public.get_working_days_count(
            start_date date,
            end_date date
        )
        RETURNS integer
        LANGUAGE sql
        IMMUTABLE
        AS $$
            SELECT COUNT(*)::integer
            FROM generate_series(start_date, end_date, '1 day'::interval) AS d
            WHERE EXTRACT(dow FROM d) NOT IN (0, 6);
        $$;
        """,
        """
        COMMENT ON FUNCTION public.get_working_days_count(date, date) IS 
        'Возвращает количество рабочих дней (пн-пт) в указанном периоде';
        """,
        ## ========== ЧАСТЬ 2: ФУНКЦИЯ РАСПРЕДЕЛЕНИЯ ДЕЖУРСТВ НА ГОД ==========
        """
        CREATE OR REPLACE FUNCTION public.assign_yearly_duty_schedule(
            p_sector_id bigint,
            p_year integer,
            p_working_days_only boolean DEFAULT true
        )
        RETURNS TABLE(
            month integer,
            week integer,
            assigned_user_id bigint,
            user_name text
        )
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_start_date date;
            v_end_date date;
            v_days_in_year integer;
            v_users_count integer;
            v_days_per_user integer;
            v_remainder integer;
            v_current_date date;
            v_user_cursor CURSOR FOR 
                SELECT u.user_id, 
                       CONCAT(u.last_name, ' ', u.first_name) as full_name,
                       COALESCE(ds.total_duties, 0) as duty_count
                FROM duty_admin_pool dap
                JOIN users u ON dap.user_id = u.user_id
                LEFT JOIN duty_statistics ds ON u.user_id = ds.user_id 
                    AND ds.sector_id = dap.sector_id 
                    AND ds.year = p_year
                WHERE dap.sector_id = p_sector_id 
                  AND dap.is_active = true
                ORDER BY duty_count ASC, RANDOM();
        BEGIN
            -- Определяем границы года
            v_start_date := MAKE_DATE(p_year, 1, 1);
            v_end_date := MAKE_DATE(p_year, 12, 31);
            
            -- Получаем количество дней в году с учетом выходных
            IF p_working_days_only THEN
                v_days_in_year := get_working_days_count(v_start_date, v_end_date);
            ELSE
                v_days_in_year := (v_end_date - v_start_date) + 1;
            END IF;
            
            -- Получаем количество активных дежурных в пуле
            SELECT COUNT(*) INTO v_users_count
            FROM duty_admin_pool
            WHERE sector_id = p_sector_id AND is_active = true;
            
            -- Если нет дежурных - выходим
            IF v_users_count = 0 THEN
                RAISE NOTICE 'Нет активных дежурных в пуле для сектора %', p_sector_id;
                RETURN;
            END IF;
            
            -- Рассчитываем базовое количество дней на одного пользователя
            v_days_per_user := v_days_in_year / v_users_count;
            v_remainder := v_days_in_year % v_users_count;
            
            -- Назначаем дежурства
            v_current_date := v_start_date;
            
            <<user_loop>>
            FOR user_rec IN v_user_cursor LOOP
                DECLARE
                    v_user_days integer;
                BEGIN
                    -- Определяем сколько дней назначить этому пользователю
                    v_user_days := v_days_per_user;
                    IF v_remainder > 0 THEN
                        v_user_days := v_user_days + 1;
                        v_remainder := v_remainder - 1;
                    END IF;
                    
                    -- Назначаем дни
                    FOR i IN 1..v_user_days LOOP
                        -- Проверяем, не вышли ли за пределы года
                        IF v_current_date > v_end_date THEN
                            EXIT user_loop;
                        END IF;
                        
                        -- Пропускаем выходные если нужно
                        IF p_working_days_only AND EXTRACT(dow FROM v_current_date) IN (0, 6) THEN
                            v_current_date := v_current_date + 1;
                            CONTINUE;
                        END IF;
                        
                        -- Проверяем, не назначено ли уже дежурство на эту дату
                        IF NOT EXISTS (
                            SELECT 1 FROM duty_schedule 
                            WHERE sector_id = p_sector_id 
                              AND duty_date = v_current_date
                        ) THEN
                            -- Создаем запись в расписании
                            INSERT INTO duty_schedule (
                                user_id, 
                                sector_id, 
                                duty_date, 
                                week_start, 
                                created_at,
                                created_by
                            ) VALUES (
                                user_rec.user_id,
                                p_sector_id,
                                v_current_date,
                                date_trunc('week', v_current_date)::date,
                                CURRENT_TIMESTAMP,
                                NULL
                            );
                            
                            -- Обновляем статистику пользователя
                            INSERT INTO duty_statistics (
                                user_id,
                                sector_id,
                                year,
                                total_duties,
                                last_duty_date,
                                updated_at
                            ) VALUES (
                                user_rec.user_id,
                                p_sector_id,
                                p_year,
                                1,
                                v_current_date,
                                CURRENT_TIMESTAMP
                            )
                            ON CONFLICT (user_id, sector_id, year) 
                            DO UPDATE SET
                                total_duties = duty_statistics.total_duties + 1,
                                last_duty_date = EXCLUDED.last_duty_date,
                                updated_at = EXCLUDED.updated_at;
                            
                            -- Возвращаем информацию для отчета
                            month := EXTRACT(MONTH FROM v_current_date);
                            week := EXTRACT(WEEK FROM v_current_date);
                            assigned_user_id := user_rec.user_id;
                            user_name := user_rec.full_name;
                            RETURN NEXT;
                        END IF;
                        
                        v_current_date := v_current_date + 1;
                    END LOOP;
                END;
            END LOOP user_loop;
            
            -- Если остались незанятые дни, назначаем их по кругу
            WHILE v_current_date <= v_end_date LOOP
                IF NOT (p_working_days_only AND EXTRACT(dow FROM v_current_date) IN (0, 6)) THEN
                    IF NOT EXISTS (
                        SELECT 1 FROM duty_schedule 
                        WHERE sector_id = p_sector_id 
                          AND duty_date = v_current_date
                    ) THEN
                        -- Выбираем пользователя с наименьшим количеством дежурств
                        WITH user_duty_counts AS (
                            SELECT 
                                dap.user_id,
                                CONCAT(u.last_name, ' ', u.first_name) as full_name,
                                COALESCE(ds.total_duties, 0) as total
                            FROM duty_admin_pool dap
                            JOIN users u ON dap.user_id = u.user_id
                            LEFT JOIN duty_statistics ds ON u.user_id = ds.user_id 
                                AND ds.sector_id = dap.sector_id 
                                AND ds.year = p_year
                            WHERE dap.sector_id = p_sector_id 
                              AND dap.is_active = true
                            ORDER BY total ASC, RANDOM()
                            LIMIT 1
                        )
                        INSERT INTO duty_schedule (
                            user_id, sector_id, duty_date, week_start, created_at
                        )
                        SELECT 
                            user_id,
                            p_sector_id,
                            v_current_date,
                            date_trunc('week', v_current_date)::date,
                            CURRENT_TIMESTAMP
                        FROM user_duty_counts
                        RETURNING user_id, 
                                  EXTRACT(MONTH FROM v_current_date) as month,
                                  EXTRACT(WEEK FROM v_current_date) as week;
                    END IF;
                END IF;
                v_current_date := v_current_date + 1;
            END LOOP;
            
        END;
        $$;
        """,
        """
        COMMENT ON FUNCTION public.assign_yearly_duty_schedule(bigint, integer, boolean) IS 
        'Автоматически распределяет дежурства на год между администраторами в пуле. 
        Параметры:
        - p_sector_id: ID сектора
        - p_year: год планирования
        - p_working_days_only: true - только рабочие дни, false - все дни включая выходные';
        """,
        ## ========== ЧАСТЬ 3: ДОПОЛНИТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ПРОВЕРКИ ЗАНЯТОСТИ ==========
        """
        CREATE OR REPLACE FUNCTION public.check_duty_availability(
            p_sector_id bigint,
            p_start_date date,
            p_end_date date
        )
        RETURNS TABLE(
            user_id bigint,
            user_name text,
            total_duties_in_period integer,
            available_days integer,
            is_available boolean
        )
        LANGUAGE sql
        AS $$
            WITH duty_counts AS (
                SELECT 
                    u.user_id,
                    CONCAT(u.last_name, ' ', u.first_name) as user_name,
                    COUNT(ds.duty_id) as duties_count
                FROM duty_admin_pool dap
                JOIN users u ON dap.user_id = u.user_id
                LEFT JOIN duty_schedule ds ON u.user_id = ds.user_id 
                    AND ds.sector_id = dap.sector_id
                    AND ds.duty_date BETWEEN p_start_date AND p_end_date
                WHERE dap.sector_id = p_sector_id 
                  AND dap.is_active = true
                GROUP BY u.user_id, u.last_name, u.first_name
            )
            SELECT 
                user_id,
                user_name,
                duties_count as total_duties_in_period,
                (p_end_date - p_start_date + 1) - duties_count as available_days,
                duties_count = 0 as is_available
            FROM duty_counts
            ORDER BY duties_count ASC, user_name;
        $$;
        """,
        """
        COMMENT ON FUNCTION public.check_duty_availability(bigint, date, date) IS 
        'Проверяет доступность дежурных в указанном периоде';
        """,
    ],
    "down": [
        ## ========== ОТКАТ ВСЕХ ИЗМЕНЕНИЙ ==========
        "DROP FUNCTION IF EXISTS public.check_duty_availability(bigint, date, date);",
        "DROP FUNCTION IF EXISTS public.assign_yearly_duty_schedule(bigint, integer, boolean);",
        "DROP FUNCTION IF EXISTS public.get_working_days_count(date, date);",
    ],
}
