# app/api_client.py - исправленная версия с правильными отступами
import aiohttp
from app.core.config import settings
from typing import Optional, Dict, Any


class APIClient:
    def __init__(self):
        self.base_url = settings.API_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                base_url=self.base_url,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"Content-Type": "application/json"},
            )
        return self.session

    async def get_report(
        self,
        user_id: Optional[int] = None,
        sector_id: Optional[int] = None,
        include_sector_name: bool = True,
    ) -> Dict[str, Any]:
        """Получить отчет через API"""
        session = await self.get_session()
        url = "/health/report"
        params = {}

        if user_id:
            params["user_id"] = user_id
        if sector_id:
            params["sector_id"] = sector_id
        if include_sector_name:
            params["include_sector_name"] = "true"

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except aiohttp.ClientConnectorError as e:
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    async def get_user(self, user_id: int) -> Dict[str, Any]:
        """Получить информацию о пользователе"""
        session = await self.get_session()
        url = f"/users/{user_id}"

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return {"error": "User not found in the system"}
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except aiohttp.ClientConnectorError as e:
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    async def create_user(
        self, user_data: Dict[str, Any], chat_id: int
    ) -> Dict[str, Any]:
        """Создать нового пользователя"""
        session = await self.get_session()
        url = "/users/"
        params = {"chat_id": chat_id}

        try:
            async with session.post(url, json=user_data, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except aiohttp.ClientConnectorError as e:
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    async def update_health_status(
        self, user_id: int, status: str, disease: Optional[str] = None
    ) -> Dict[str, Any]:
        """Обновить статус здоровья пользователя"""
        session = await self.get_session()
        url = f"/users/{user_id}/health"

        # Подготовка данных
        health_data = {"status": status}

        # Добавляем заболевание только если статус "болен" и оно указано
        if status == "болен" and disease:
            health_data["disease"] = disease
        elif status != "болен":
            # Для других статусов явно указываем пустое заболевание
            health_data["disease"] = ""

        try:
            async with session.put(url, json=health_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except aiohttp.ClientConnectorError as e:
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    async def get_sectors(self) -> Dict[str, Any]:
        """Получить список секторов"""
        session = await self.get_session()
        url = "/health/sectors"

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except aiohttp.ClientConnectorError as e:
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    async def check_health(self) -> bool:
        """Проверить доступность API"""
        session = await self.get_session()
        url = "/"

        try:
            async with session.get(url) as response:
                return response.status == 200
        except:
            return False

    async def close(self):
        """Закрыть сессию"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Зарегистрировать пользователя (упрощенный метод)"""
        session = await self.get_session()
        url = "/users/register"

        try:
            async with session.post(url, json=user_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def toggle_user_report(self, user_id: int) -> Dict[str, Any]:
        """Переключить статус отчетов пользователя"""
        session = await self.get_session()
        url = f"/admin/users/{user_id}/toggle-report"

        try:
            async with session.put(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def toggle_user_admin(self, user_id: int) -> Dict[str, Any]:
        """Переключить админ статус пользователя"""
        session = await self.get_session()
        url = f"/admin/users/{user_id}/toggle-admin"

        try:
            async with session.put(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def search_users(self, query: str) -> Dict[str, Any]:
        """Поиск пользователей по имени, фамилии или username"""
        session = await self.get_session()

        try:
            # Используем эндпоинт /users/ с параметрами поиска
            params = {"search": query, "limit": 10}
            async with session.get("/users/", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def search_users_by_name(self, name: str) -> Dict[str, Any]:
        """Поиск пользователей по имени или фамилии"""
        return await self.search_users(name)

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """Получить всех пользователей"""
        session = await self.get_session()
        url = "/users/"
        params = {"skip": skip, "limit": limit}

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def search_users_api(
        self, query: str, skip: int = 0, limit: int = 10
    ) -> Dict[str, Any]:
        """Поиск пользователей через API"""
        session = await self.get_session()
        url = "/users/search/"
        params = {"q": query, "skip": skip, "limit": limit}

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def get_admin_users_list(
        self, skip: int = 0, limit: int = 100
    ) -> Dict[str, Any]:
        """Получить список пользователей для админ-панели"""
        session = await self.get_session()
        url = "/users/admin/list"
        params = {"skip": skip, "limit": limit}

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    # ========== МЕТОДЫ ДЛЯ СИСТЕМЫ ДЕЖУРНЫХ ==========

    async def get_duty_pool(
        self, sector_id: int, active_only: bool = True
    ) -> Dict[str, Any]:
        """Получить пул дежурных для сектора"""
        session = await self.get_session()
        url = f"/duty/pool/sector/{sector_id}"
        params = {"active_only": str(active_only).lower()}

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    # Здесь уже должны быть заполненные user_name и sector_name
                    return data
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def add_to_duty_pool(
        self, user_id: int, sector_id: int, added_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Добавить пользователя в пул дежурных"""
        session = await self.get_session()
        url = "/duty/pool"
        data = {"user_id": user_id, "sector_id": sector_id, "added_by": added_by}

        try:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def remove_from_duty_pool(
        self, user_id: int, sector_id: int
    ) -> Dict[str, Any]:
        """Удалить пользователя из пула дежурных"""
        session = await self.get_session()
        url = f"/duty/pool/{user_id}/{sector_id}"

        try:
            async with session.delete(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def assign_weekly_duty(
        self, sector_id: int, week_start: str, created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Автоматически назначить дежурного на неделю"""
        session = await self.get_session()
        url = "/duty/assign-weekly"
        params = {"sector_id": sector_id, "week_start": week_start}
        if created_by:
            params["created_by"] = created_by

        try:
            async with session.post(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def get_duty_schedule(
        self,
        sector_id: Optional[int] = None,
        user_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Получить расписание дежурств"""
        session = await self.get_session()
        url = "/duty/schedule"
        params = {}

        if sector_id:
            params["sector_id"] = sector_id
        if user_id:
            params["user_id"] = user_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def get_monthly_schedule(
        self, sector_id: int, year: int, month: int
    ) -> Dict[str, Any]:
        """Получить расписание на месяц"""
        session = await self.get_session()
        url = "/duty/schedule/monthly"
        params = {"sector_id": sector_id, "year": year, "month": month}

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def get_today_duty(self, sector_id: Optional[int] = None) -> Dict[str, Any]:
        """Кто дежурит сегодня"""
        session = await self.get_session()
        url = "/duty/schedule/today"
        params = {}
        if sector_id:
            params["sector_id"] = sector_id

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def get_duty_statistics(
        self,
        sector_id: Optional[int] = None,
        user_id: Optional[int] = None,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Получить статистику дежурств"""
        session = await self.get_session()
        url = "/duty/statistics"
        params = {}

        if sector_id:
            params["sector_id"] = sector_id
        if user_id:
            params["user_id"] = user_id
        if year:
            params["year"] = year

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def get_sector_statistics_summary(
        self, sector_id: int, year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Получить сводку статистики по сектору"""
        session = await self.get_session()
        url = f"/duty/statistics/sector/{sector_id}/summary"
        params = {}
        if year:
            params["year"] = year

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def get_eligible_users(
        self, sector_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Получить список пользователей, которые могут быть дежурными"""
        session = await self.get_session()
        url = "/duty/eligible-users"
        params = {}
        if sector_id:
            params["sector_id"] = sector_id

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def toggle_user_eligible(
        self, user_id: int, eligible: bool
    ) -> Dict[str, Any]:
        """Включить/выключить возможность быть дежурным"""
        session = await self.get_session()
        url = f"/duty/eligible-users/{user_id}/toggle"
        params = {"eligible": str(eligible).lower()}

        try:
            async with session.post(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def assign_duty_for_period(
        self,
        sector_id: int,
        period: str,  # "day", "week", "month", "year"
        start_date: str,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Назначить дежурного на период"""
        session = await self.get_session()
        url = "/duty/assign"
        params = {"sector_id": sector_id, "period": period, "start_date": start_date}
        if created_by:
            params["created_by"] = created_by

        try:
            async with session.post(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def plan_yearly_schedule(
        self, sector_id: int, year: int, working_days_only: bool = True
    ) -> Dict[str, Any]:
        """Спланировать дежурства на весь год"""
        session = await self.get_session()
        url = "/duty/plan-year"
        params = {
            "sector_id": sector_id,
            "year": year,
            "working_days_only": working_days_only,
        }

        try:
            async with session.post(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def check_availability(
        self, sector_id: int, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Проверить доступность дежурных на период"""
        session = await self.get_session()
        url = f"/duty/availability/{sector_id}"
        params = {"start_date": start_date, "end_date": end_date}

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def get_week_schedule(
        self, sector_id: Optional[int] = None, week_start: Optional[str] = None
    ) -> Dict[str, Any]:
        """Получить график дежурств на неделю"""
        session = await self.get_session()
        url = "/duty/schedule/week"
        params = {}
        if sector_id:
            params["sector_id"] = sector_id
        if week_start:
            params["week_start"] = week_start

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def get_month_schedule(
        self,
        sector_id: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Получить график дежурств на месяц"""
        session = await self.get_session()
        url = "/duty/schedule/month"
        params = {}
        if sector_id:
            params["sector_id"] = sector_id
        if year:
            params["year"] = year
        if month:
            params["month"] = month

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def get_year_schedule(
        self, sector_id: Optional[int] = None, year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Получить годовую статистику дежурств"""
        session = await self.get_session()
        url = "/duty/schedule/year"
        params = {}
        if sector_id:
            params["sector_id"] = sector_id
        if year:
            params["year"] = year

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def get_duty_statistics_chart(
        self,
        sector_id: Optional[int] = None,
        user_id: Optional[int] = None,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Получить данные для построения графиков"""
        session = await self.get_session()
        url = "/duty/statistics/chart"
        params = {}
        if sector_id:
            params["sector_id"] = sector_id
        if user_id:
            params["user_id"] = user_id
        if year:
            params["year"] = year

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}


# Глобальный экземпляр клиента
api_client = APIClient()
