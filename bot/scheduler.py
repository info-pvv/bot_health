# bot/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import pytz
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


class ReportScheduler:
    """Планировщик для рассылки отчетов"""

    def __init__(self, bot):
        """
        Инициализация планировщика

        Args:
            bot: Экземпляр aiogram Bot
        """
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
        logger.info("🕐 Планировщик инициализирован")

    async def send_sector_report(
        self, chat_id: int, sector_id: Optional[int] = None
    ) -> bool:
        """
        Отправить отчет по сектору в указанный чат с информацией о дежурном
        """
        try:
            from app.api_client import api_client
            from bot.utils.formatters import format_report, format_duty_info

            # Получаем отчет о здоровье
            report_data = await api_client.get_report(
                sector_id=sector_id, include_sector_name=True
            )

            if "error" in report_data:
                error_msg = f"❌ Ошибка при получении отчета: {report_data['error']}"
                await self.bot.send_message(chat_id, error_msg)
                logger.error(
                    f"Ошибка отчета для чата {chat_id}: {report_data['error']}"
                )
                return False

            # Получаем информацию о дежурном администраторе на сегодня
            duty_info = await self.get_today_duty_info(sector_id)

            # Форматируем отчет с информацией о дежурном
            formatted_report = format_report(report_data, duty_info)

            # Отправляем (разбиваем если слишком длинный)
            if len(formatted_report) > 4000:
                parts = [
                    formatted_report[i : i + 4000]
                    for i in range(0, len(formatted_report), 4000)
                ]
                for part in parts:
                    await self.bot.send_message(chat_id, part, parse_mode="Markdown")
            else:
                await self.bot.send_message(
                    chat_id, formatted_report, parse_mode="Markdown"
                )

            logger.info(f"✅ Отчет отправлен в чат {chat_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки отчета в чат {chat_id}: {e}")
            try:
                await self.bot.send_message(
                    chat_id, f"❌ Ошибка отправки отчета: {str(e)}"
                )
            except:
                pass
            return False

    async def get_today_duty_info(
        self, sector_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Получить информацию о дежурном администраторе на сегодня

        Args:
            sector_id: ID сектора (если None - для всех секторов)

        Returns:
            Dict с информацией о дежурном или None
        """
        try:
            from app.api_client import api_client

            today_data = await api_client.get_today_duty(sector_id=sector_id)

            if "error" in today_data:
                logger.warning(
                    f"Не удалось получить информацию о дежурном: {today_data['error']}"
                )
                return None

            duties = today_data.get("duties", [])

            if not duties:
                return None

            # Если указан конкретный сектор, берем первого
            if sector_id:
                for duty in duties:
                    if duty.get("sector_id") == sector_id:
                        return {
                            "user_name": duty.get("user_name", "Неизвестно"),
                            "sector_name": duty.get(
                                "sector_name", f"Сектор {sector_id}"
                            ),
                        }
                return None

            # Если сектор не указан, возвращаем всех дежурных
            return {
                "multiple": True,
                "duties": [
                    {
                        "user_name": d.get("user_name", "Неизвестно"),
                        "sector_name": d.get(
                            "sector_name", f"Сектор {d.get('sector_id')}"
                        ),
                    }
                    for d in duties
                ],
            }

        except Exception as e:
            logger.error(f"Ошибка получения информации о дежурном: {e}")
            return None

    async def send_all_sectors_reports(self):
        """Разослать отчеты по всем секторам с информацией о дежурных"""
        logger.info("📨 Начинаю рассылку отчетов по всем секторам...")

        try:
            from app.api_client import api_client

            # Получаем список всех секторов
            sectors_data = await api_client.get_sectors()

            if "error" in sectors_data:
                logger.error(f"❌ Ошибка получения секторов: {sectors_data['error']}")
                return

            sectors = sectors_data.get("sectors", [])
            logger.info(f"📊 Найдено секторов для рассылки: {len(sectors)}")

            # Для каждого сектора отправляем отчет
            for sector in sectors:
                sector_id = sector.get("sector_id")
                sector_name = sector.get("name", f"Сектор {sector_id}")

                logger.info(f"📨 Обрабатываю сектор: {sector_name} (ID: {sector_id})")

                try:
                    success = await self.send_sector_report(sector_id, sector_id)
                    if success:
                        logger.info(f"  ✅ Отправлено в сектор {sector_id}")
                except Exception as e:
                    logger.error(f"  ❌ Ошибка отправки {sector_id}: {e}")

            logger.info("✅ Рассылка завершена")

        except Exception as e:
            logger.error(f"❌ Критическая ошибка рассылки: {e}")

    async def get_sector_admins(self, sector_id: int) -> List[int]:
        """Получить список админов сектора

        Args:
            sector_id: ID сектора

        Returns:
            List[int]: Список chat_id админов
        """
        try:
            from app.api_client import api_client

            # Получаем всех пользователей через API
            users_data = await api_client.get_all_users(limit=1000)

            logger.debug(f"Получены данные пользователей: {type(users_data)}")

            # Проверяем, что данные получены и это словарь
            if not users_data:
                logger.warning("Данные пользователей не получены (пустой ответ)")
                return []

            # Проверяем формат ответа
            if isinstance(users_data, dict):
                # Если это словарь с ошибкой
                if "error" in users_data:
                    logger.error(
                        f"Ошибка API при получении пользователей: {users_data['error']}"
                    )
                    return []

                # Если это словарь с пользователями в ключе "users"
                if "users" in users_data:
                    users = users_data["users"]
                else:
                    # Пытаемся найти список пользователей в других ключах
                    users = []
                    for key, value in users_data.items():
                        if isinstance(value, list):
                            users = value
                            break
            elif isinstance(users_data, list):
                # Если это просто список
                users = users_data
            else:
                logger.error(
                    f"Неизвестный формат данных пользователей: {type(users_data)}"
                )
                return []

            if not users:
                logger.warning("Список пользователей пуст")
                return []

            logger.debug(f"Обрабатываю {len(users)} пользователей")

            admins = []
            for user in users:
                try:
                    # Проверяем структуру пользователя
                    if not isinstance(user, dict):
                        continue

                    # Получаем ID пользователя
                    user_id = user.get("user_id") or user.get("id")
                    if not user_id:
                        continue

                    # Получаем информацию о статусе
                    status_info = user.get("status_info", {})
                    if not isinstance(status_info, dict):
                        continue

                    # Проверяем админские права
                    is_admin = status_info.get("enable_admin", False)
                    if not is_admin:
                        continue

                    # Проверяем сектор пользователя
                    user_sector = status_info.get("sector_id")

                    # Если sector_id передан, проверяем совпадение
                    # Если sector_id не передан (None), берем всех админов
                    if sector_id is None or user_sector == sector_id:
                        admins.append(user_id)
                        logger.debug(
                            f"  Найден админ: {user_id} (сектор: {user_sector})"
                        )

                except Exception as e:
                    logger.debug(f"Ошибка обработки пользователя {user}: {e}")
                    continue

            logger.info(f"Найдено админов для сектора {sector_id}: {len(admins)}")
            return admins

        except Exception as e:
            logger.error(f"Ошибка получения админов: {e}", exc_info=True)
            return []

    def schedule_daily_report(self, time_str: str = "07:30"):
        """
        Запланировать ежедневную рассылку

        Args:
            time_str: Время в формате "ЧЧ:ММ"
        """
        try:
            hour, minute = map(int, time_str.split(":"))

            self.scheduler.add_job(
                self.send_all_sectors_reports,
                CronTrigger(hour=hour, minute=minute, timezone="Europe/Moscow"),
                id="daily_sector_report",
                name="Ежедневный отчет по секторам",
                replace_existing=True,
            )

            logger.info(f"⏰ Ежедневная рассылка запланирована на {time_str}")

        except ValueError:
            logger.error(f"❌ Неверный формат времени: {time_str}. Используйте ЧЧ:ММ")
        except Exception as e:
            logger.error(f"❌ Ошибка планирования: {e}")

    def schedule_test_report(self, seconds: int = 60):
        """
        Запланировать тестовую рассылку (для отладки)

        Args:
            seconds: Интервал в секундах
        """
        try:
            self.scheduler.add_job(
                self.send_test_report,
                IntervalTrigger(seconds=seconds),
                id="test_report",
                name="Тестовая рассылка",
                replace_existing=True,
            )

            logger.info(f"🧪 Тестовая рассылка запланирована каждые {seconds} секунд")

        except Exception as e:
            logger.error(f"❌ Ошибка планирования теста: {e}")

    async def send_test_report(self):
        """Выполнить тестовую рассылку"""
        logger.info("🧪 Выполняю тестовую рассылку...")

        try:
            # Отправляем сообщение в лог
            logger.info("🧪 Тестовая рассылка выполнена")

            # Можно отправить тестовое сообщение разработчику
            # test_chat_id = 205864200  # Ваш chat_id
            # await self.bot.send_message(
            #     test_chat_id,
            #     "🧪 **ТЕСТОВАЯ РАССЫЛКА**\n"
            #     f"Время: {datetime.now().strftime('%H:%M:%S')}\n"
            #     "Это тестовое сообщение по расписанию.",
            #     parse_mode="Markdown"
            # )

        except Exception as e:
            logger.error(f"❌ Ошибка тестовой рассылки: {e}")

    def start(self):
        """Запустить планировщик"""
        try:
            self.scheduler.start()
            logger.info("🚀 Планировщик запущен")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска планировщика: {e}")

    def stop(self):
        """Остановить планировщик"""
        try:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logger.info("🛑 Планировщик остановлен")
            else:
                logger.info("⏸️ Планировщик уже остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка остановки планировщика: {e}")

    def get_jobs_info(self) -> str:
        """Получить информацию о запланированных задачах"""
        jobs = self.scheduler.get_jobs()

        if not jobs:
            return "📭 Нет запланированных задач"

        info = "📅 **Запланированные задачи:**\n\n"
        for job in jobs:
            info += f"• **{job.name}**\n"
            info += f"  ID: `{job.id}`\n"
            info += f"  Следующий запуск: {job.next_run_time}\n"
            info += f"  Триггер: {job.trigger}\n\n"

        return info
