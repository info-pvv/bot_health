# migrations/versions/005_initial_duty_data_complete.py
"""
Миграция для добавления начальных данных дежурных администраторов
Добавляет:
- Каранов, Митичев, Попов в пул дежурных
- Назначение Митичева на неделю 16-22.02.2026
- Обновление статистики для Митичева
"""

migration = {
    "id": "005_initial_duty_data_complete",
    "description": "Add initial duty admins and schedule with statistics",
    "up": [
        # 1. Отмечаем пользователей как потенциальных дежурных
        """
        UPDATE public.users 
        SET is_duty_eligible = true 
        WHERE user_id IN (1097205631, 496601766, 568964940);
        """,
        # 2. Добавляем в пул дежурных для сектора СТС
        """
        INSERT INTO public.duty_admin_pool (user_id, sector_id, added_by)
        VALUES 
            (1097205631, -1001567110550, 568964940),
            (496601766, -1001567110550, 568964940),
            (568964940, -1001567110550, 568964940)
        ON CONFLICT (user_id, sector_id) 
        DO UPDATE SET 
            is_active = true,
            added_by = EXCLUDED.added_by;
        """,
        # 3. Назначаем Митичева дежурным на неделю 16-22.02.2026
        """
        DO $$
        DECLARE
            v_date DATE;
            v_user_id BIGINT := 496601766;
            v_sector_id BIGINT := -1001567110550;
            v_week_start DATE := '2026-02-16'::DATE;
            v_created_by BIGINT := 568964940;
            v_year INTEGER := 2026;
            v_dates DATE[];
        BEGIN
            -- Удаляем существующие записи на эту неделю
            DELETE FROM public.duty_schedule 
            WHERE sector_id = v_sector_id AND week_start = v_week_start;
            
            -- Создаем массив дат
            v_dates := ARRAY(
                SELECT v_week_start + (n - 1)::INTEGER
                FROM generate_series(1, 7) AS n
            );
            
            -- Создаем записи на 7 дней
            FOREACH v_date IN ARRAY v_dates LOOP
                INSERT INTO public.duty_schedule (
                    user_id, sector_id, duty_date, week_start, created_by
                ) VALUES (
                    v_user_id, v_sector_id, v_date, v_week_start, v_created_by
                );
            END LOOP;
            
            -- Обновляем статистику
            INSERT INTO public.duty_statistics (
                user_id, sector_id, year, total_duties, last_duty_date, updated_at
            ) VALUES (
                v_user_id, v_sector_id, v_year, 7, v_dates[7], CURRENT_TIMESTAMP
            )
            ON CONFLICT (user_id, sector_id, year) 
            DO UPDATE SET
                total_duties = duty_statistics.total_duties + 7,
                last_duty_date = EXCLUDED.last_duty_date,
                updated_at = EXCLUDED.updated_at;
        END;
        $$;
        """,
    ],
    "down": [
        # 1. Удаляем статистику для Митичева за 2026 год
        """
        DELETE FROM public.duty_statistics 
        WHERE user_id = 496601766 
          AND sector_id = -1001567110550 
          AND year = 2026;
        """,
        # 2. Удаляем расписание Митичева
        """
        DELETE FROM public.duty_schedule 
        WHERE sector_id = -1001567110550 
          AND week_start = '2026-02-16'::DATE;
        """,
        # 3. Удаляем пользователей из пула
        """
        DELETE FROM public.duty_admin_pool 
        WHERE sector_id = -1001567110550 
          AND user_id IN (1097205631, 496601766, 568964940);
        """,
        # 4. Снимаем отметку is_duty_eligible
        """
        UPDATE public.users 
        SET is_duty_eligible = false 
        WHERE user_id IN (1097205631, 496601766, 568964940);
        """,
    ],
}
