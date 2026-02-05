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
                headers={"Content-Type": "application/json"}
            )
        return self.session
    
    async def get_report(self, user_id: Optional[int] = None, sector_id: Optional[int] = None, include_sector_name: bool = True) -> Dict[str, Any]:
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
    
    async def create_user(self, user_data: Dict[str, Any], chat_id: int) -> Dict[str, Any]:
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
    
    async def update_health_status(self, user_id: int, status: str, disease: Optional[str] = None) -> Dict[str, Any]:
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


# Глобальный экземпляр клиента
api_client = APIClient()