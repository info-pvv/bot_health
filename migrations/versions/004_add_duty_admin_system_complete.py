# migrations/versions/004_add_duty_admin_system_complete.py
"""
Полная миграция для системы дежурных администраторов
Включает:
- Поле is_duty_eligible в таблицу users
- Таблицу duty_admin_pool (пул дежурных)
- Таблицу duty_schedule (расписание дежурств)
- Таблицу duty_statistics (статистика по годам)
- Функции для автоматического назначения и получения статистики
- Индексы и комментарии
"""

migration = {
    "id": "004_add_duty_admin_system_complete",
    "description": "Complete duty admin system with statistics and functions",
    "up": [
        ## ========== ЧАСТЬ 1: ДОБАВЛЕНИЕ ПОЛЯ ==========
        """
        ALTER TABLE public.users 
        ADD COLUMN IF NOT EXISTS is_duty_eligible BOOLEAN DEFAULT false;
        """,
        """
        COMMENT ON COLUMN public.users.is_duty_eligible 
        IS 'Может ли пользователь быть дежурным администратором';
        """,
        ## ========== ЧАСТЬ 2: ТАБЛИЦА ПУЛА ДЕЖУРНЫХ ==========
        """
        CREATE TABLE IF NOT EXISTS public.duty_admin_pool (
            pool_id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
            sector_id BIGINT NOT NULL REFERENCES public.sectors(sector_id) ON DELETE CASCADE,
            is_active BOOLEAN DEFAULT true,
            added_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            added_by BIGINT REFERENCES public.users(user_id) ON DELETE SET NULL,
            CONSTRAINT unique_duty_admin_per_sector UNIQUE(user_id, sector_id)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_duty_pool_user 
        ON public.duty_admin_pool(user_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_duty_pool_sector 
        ON public.duty_admin_pool(sector_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_duty_pool_active 
        ON public.duty_admin_pool(is_active);
        """,
        """
        COMMENT ON TABLE public.duty_admin_pool 
        IS 'Пул пользователей, которые могут быть дежурными администраторами';
        """,
        ## ========== ЧАСТЬ 3: ТАБЛИЦА РАСПИСАНИЯ ==========
        """
        CREATE TABLE IF NOT EXISTS public.duty_schedule (
            duty_id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
            sector_id BIGINT NOT NULL REFERENCES public.sectors(sector_id) ON DELETE CASCADE,
            duty_date DATE NOT NULL,
            week_start DATE NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_by BIGINT REFERENCES public.users(user_id) ON DELETE SET NULL,
            CONSTRAINT unique_duty_per_day UNIQUE(sector_id, duty_date)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_duty_schedule_user 
        ON public.duty_schedule(user_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_duty_schedule_sector 
        ON public.duty_schedule(sector_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_duty_schedule_date 
        ON public.duty_schedule(duty_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_duty_schedule_week 
        ON public.duty_schedule(week_start);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_duty_schedule_composite 
        ON public.duty_schedule(sector_id, week_start, duty_date);
        """,
        """
        COMMENT ON TABLE public.duty_schedule 
        IS 'Расписание дежурств администраторов';
        """,
        """
        COMMENT ON COLUMN public.duty_schedule.duty_date 
        IS 'Конкретная дата дежурства';
        """,
        """
        COMMENT ON COLUMN public.duty_schedule.week_start 
        IS 'Начало недели дежурства (для группировки)';
        """,
        ## ========== ЧАСТЬ 4: ТАБЛИЦА СТАТИСТИКИ ==========
        """
        CREATE TABLE IF NOT EXISTS public.duty_statistics (
            stat_id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
            sector_id BIGINT NOT NULL REFERENCES public.sectors(sector_id) ON DELETE CASCADE,
            year INTEGER NOT NULL,
            total_duties INTEGER DEFAULT 0,
            last_duty_date DATE,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_user_sector_year UNIQUE(user_id, sector_id, year)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_duty_stats_user_year 
        ON public.duty_statistics(user_id, year);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_duty_stats_sector_year 
        ON public.duty_statistics(sector_id, year);
        """,
        """
        COMMENT ON TABLE public.duty_statistics 
        IS 'Статистика дежурств по годам';
        """,
        ## ========== ЧАСТЬ 5: ФУНКЦИЯ АВТОМАТИЧЕСКОГО НАЗНАЧЕНИЯ ==========
        """
        CREATE OR REPLACE FUNCTION assign_weekly_duty_admin(
            p_sector_id BIGINT,
            p_week_start DATE,
            p_assigned_by BIGINT DEFAULT NULL
        ) RETURNS TABLE (
            assigned_user_id BIGINT,
            user_name TEXT,
            week_dates DATE[],
            message TEXT
        ) LANGUAGE plpgsql AS $$
        DECLARE
            v_user_id BIGINT;
            v_user_record RECORD;
            v_year INTEGER;
            v_date DATE;
            v_dates DATE[];
            v_available_count INTEGER;
        BEGIN
            -- Проверяем, есть ли доступные дежурные в пуле
            SELECT COUNT(*) INTO v_available_count
            FROM public.duty_admin_pool dap
            WHERE dap.sector_id = p_sector_id 
              AND dap.is_active = true;
            
            IF v_available_count = 0 THEN
                RETURN QUERY SELECT 
                    NULL::BIGINT,
                    NULL::TEXT,
                    NULL::DATE[],
                    'В пуле нет активных дежурных для этого сектора'::TEXT;
                RETURN;
            END IF;
            
            -- Проверяем, не назначено ли уже дежурство на эту неделю
            IF EXISTS (
                SELECT 1 FROM public.duty_schedule 
                WHERE sector_id = p_sector_id 
                  AND week_start = p_week_start
            ) THEN
                RETURN QUERY SELECT 
                    NULL::BIGINT,
                    NULL::TEXT,
                    NULL::DATE[],
                    'Дежурство на эту неделю уже назначено'::TEXT;
                RETURN;
            END IF;
            
            v_year := EXTRACT(YEAR FROM p_week_start);
            
            -- Выбираем пользователя с наименьшим количеством дежурств
            SELECT 
                dap.user_id,
                u.username,
                u.first_name,
                u.last_name,
                COALESCE(ds.total_duties, 0) as duty_count
            INTO v_user_record
            FROM 
                public.duty_admin_pool dap
                JOIN public.users u ON dap.user_id = u.user_id
                LEFT JOIN public.duty_statistics ds ON dap.user_id = ds.user_id 
                    AND ds.sector_id = dap.sector_id 
                    AND ds.year = v_year
            WHERE 
                dap.sector_id = p_sector_id 
                AND dap.is_active = true
            ORDER BY 
                COALESCE(ds.total_duties, 0) ASC,
                ds.last_duty_date ASC NULLS FIRST,
                RANDOM()
            LIMIT 1;
            
            IF v_user_record.user_id IS NULL THEN
                RETURN QUERY SELECT 
                    NULL::BIGINT,
                    NULL::TEXT,
                    NULL::DATE[],
                    'Не удалось выбрать дежурного'::TEXT;
                RETURN;
            END IF;
            
            v_user_id := v_user_record.user_id;
            
            -- Создаем массив дат на неделю
            v_dates := ARRAY(
                SELECT p_week_start + (n - 1)::INTEGER
                FROM generate_series(1, 7) AS n
            );
            
            -- Назначаем дежурства на каждый день
            FOREACH v_date IN ARRAY v_dates LOOP
                INSERT INTO public.duty_schedule (
                    user_id, sector_id, duty_date, week_start, created_by
                ) VALUES (
                    v_user_id, p_sector_id, v_date, p_week_start, p_assigned_by
                );
            END LOOP;
            
            -- Обновляем статистику
            INSERT INTO public.duty_statistics (
                user_id, sector_id, year, total_duties, last_duty_date, updated_at
            ) VALUES (
                v_user_id, p_sector_id, v_year, 7, v_dates[7], CURRENT_TIMESTAMP
            )
            ON CONFLICT (user_id, sector_id, year) 
            DO UPDATE SET
                total_duties = duty_statistics.total_duties + 7,
                last_duty_date = EXCLUDED.last_duty_date,
                updated_at = EXCLUDED.updated_at;
            
            RETURN QUERY SELECT 
                v_user_id,
                CONCAT(v_user_record.last_name, ' ', v_user_record.first_name)::TEXT,
                v_dates,
                'Дежурство успешно назначено'::TEXT;
        END;
        $$;
        """,
        ## ========== ЧАСТЬ 6: ФУНКЦИЯ ПОЛУЧЕНИЯ СТАТИСТИКИ ==========
        """
        CREATE OR REPLACE FUNCTION get_sector_duty_stats(
            p_sector_id BIGINT,
            p_year INTEGER DEFAULT EXTRACT(YEAR FROM CURRENT_DATE)
        ) RETURNS TABLE (
            user_id BIGINT,
            full_name TEXT,
            username VARCHAR(255),
            total_duties_this_year INTEGER,
            last_duty_date DATE,
            in_pool BOOLEAN
        ) LANGUAGE sql AS $$
            SELECT 
                u.user_id,
                CONCAT(u.last_name, ' ', u.first_name) as full_name,
                u.username,
                COALESCE(ds.total_duties, 0) as total_duties_this_year,
                ds.last_duty_date,
                CASE WHEN dap.user_id IS NOT NULL THEN true ELSE false END as in_pool
            FROM 
                public.users u
                LEFT JOIN public.duty_admin_pool dap ON u.user_id = dap.user_id 
                    AND dap.sector_id = p_sector_id 
                    AND dap.is_active = true
                LEFT JOIN public.duty_statistics ds ON u.user_id = ds.user_id 
                    AND ds.sector_id = p_sector_id 
                    AND ds.year = p_year
            WHERE 
                u.is_duty_eligible = true
            ORDER BY 
                in_pool DESC,
                ds.total_duties DESC NULLS LAST,
                u.last_name;
        $$;
        """,
        ## ========== ЧАСТЬ 7: ФУНКЦИЯ ПОЛУЧЕНИЯ РАСПИСАНИЯ ==========
        """
        CREATE OR REPLACE FUNCTION get_monthly_duty_schedule(
            p_sector_id BIGINT,
            p_year INTEGER,
            p_month INTEGER
        ) RETURNS TABLE (
            duty_date DATE,
            user_id BIGINT,
            user_name TEXT,
            day_of_week TEXT
        ) LANGUAGE sql AS $$
            SELECT 
                ds.duty_date,
                u.user_id,
                CONCAT(u.last_name, ' ', u.first_name) as user_name,
                TO_CHAR(ds.duty_date, 'Day') as day_of_week
            FROM 
                public.duty_schedule ds
                JOIN public.users u ON ds.user_id = u.user_id
            WHERE 
                ds.sector_id = p_sector_id
                AND EXTRACT(YEAR FROM ds.duty_date) = p_year
                AND EXTRACT(MONTH FROM ds.duty_date) = p_month
            ORDER BY 
                ds.duty_date;
        $$;
        """,
    ],
    "down": [
        ## ========== ОТКАТ ВСЕХ ИЗМЕНЕНИЙ ==========
        "DROP FUNCTION IF EXISTS get_monthly_duty_schedule(BIGINT, INTEGER, INTEGER);",
        "DROP FUNCTION IF EXISTS get_sector_duty_stats(BIGINT, INTEGER);",
        "DROP FUNCTION IF EXISTS assign_weekly_duty_admin(BIGINT, DATE, BIGINT);",
        "DROP INDEX IF EXISTS public.idx_duty_stats_sector_year;",
        "DROP INDEX IF EXISTS public.idx_duty_stats_user_year;",
        "DROP TABLE IF EXISTS public.duty_statistics;",
        "DROP INDEX IF EXISTS public.idx_duty_schedule_composite;",
        "DROP INDEX IF EXISTS public.idx_duty_schedule_week;",
        "DROP INDEX IF EXISTS public.idx_duty_schedule_date;",
        "DROP INDEX IF EXISTS public.idx_duty_schedule_sector;",
        "DROP INDEX IF EXISTS public.idx_duty_schedule_user;",
        "DROP TABLE IF EXISTS public.duty_schedule;",
        "DROP INDEX IF EXISTS public.idx_duty_pool_active;",
        "DROP INDEX IF EXISTS public.idx_duty_pool_sector;",
        "DROP INDEX IF EXISTS public.idx_duty_pool_user;",
        "DROP TABLE IF EXISTS public.duty_admin_pool;",
        "ALTER TABLE public.users DROP COLUMN IF EXISTS is_duty_eligible;",
    ],
}
