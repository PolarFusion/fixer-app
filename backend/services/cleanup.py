"""
Сервис автоматической очистки данных.
Использует APScheduler для периодической очистки старых заявок и файлов.
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import select

from database import async_session_maker, cleanup_old_tickets
from models import Ticket


# ===== КОНФИГУРАЦИЯ =====

# Глобальный планировщик
scheduler: AsyncIOScheduler = None

# Настройки очистки
DEFAULT_RETENTION_DAYS = 90  # Дни хранения
CLEANUP_TIME = "02:00"       # Время запуска очистки (2:00 ночи)
MEDIA_DIR = "media"          # Директория медиа файлов


# ===== ОСНОВНЫЕ ФУНКЦИИ ОЧИСТКИ =====

async def cleanup_old_data(retention_days: int = DEFAULT_RETENTION_DAYS) -> Dict:
    """
    Основная функция очистки старых данных.
    Удаляет заявки и связанные файлы старше указанного количества дней.
    """
    print(f"🧹 Запуск очистки данных старше {retention_days} дней...")
    
    cleanup_stats = {
        "started_at": datetime.utcnow().isoformat(),
        "tickets_deleted": 0,
        "files_deleted": 0,
        "errors": [],
        "status": "running"
    }
    
    try:
        # Очищаем заявки (функция из database.py)
        deleted_tickets = await cleanup_old_tickets(retention_days)
        cleanup_stats["tickets_deleted"] = deleted_tickets
        
        # Дополнительно очищаем файлы-сироты
        orphaned_files = await cleanup_orphaned_files()
        cleanup_stats["files_deleted"] = orphaned_files
        
        cleanup_stats["status"] = "completed"
        print(f"✅ Очистка завершена: удалено {deleted_tickets} заявок и {orphaned_files} файлов")
        
    except Exception as e:
        cleanup_stats["status"] = "failed"
        cleanup_stats["errors"].append(str(e))
        print(f"❌ Ошибка при очистке: {e}")
    
    cleanup_stats["completed_at"] = datetime.utcnow().isoformat()
    return cleanup_stats


async def cleanup_orphaned_files() -> int:
    """
    Удаляет файлы-сироты в медиа директории.
    Файлы, которые не связаны ни с одной заявкой.
    """
    if not os.path.exists(MEDIA_DIR):
        return 0
    
    deleted_count = 0
    
    # Получаем все файлы в медиа директории
    media_files = []
    for filename in os.listdir(MEDIA_DIR):
        file_path = os.path.join(MEDIA_DIR, filename)
        if os.path.isfile(file_path):
            media_files.append(file_path)
    
    if not media_files:
        return 0
    
    # Получаем все пути файлов из активных заявок
    async with async_session_maker() as session:
        tickets_query = select(Ticket.before_photo_path, Ticket.after_photo_path)
        result = await session.exec(tickets_query)
        ticket_files = result.all()
    
    # Собираем список всех файлов, используемых в заявках
    active_files = set()
    for before_path, after_path in ticket_files:
        if before_path:
            active_files.add(before_path)
        if after_path:
            active_files.add(after_path)
    
    # Удаляем файлы-сироты
    for file_path in media_files:
        if file_path not in active_files:
            try:
                # Проверяем, что файл старше 1 дня (на всякий случай)
                file_age = datetime.utcnow() - datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_age > timedelta(days=1):
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"🗑️ Удален файл-сирота: {file_path}")
            except Exception as e:
                print(f"❌ Ошибка удаления файла {file_path}: {e}")
    
    return deleted_count


async def cleanup_old_sessions() -> int:
    """
    Очистка старых сессий и временных данных.
    В данном проекте используется JWT, поэтому эта функция может быть расширена
    для очистки других временных данных.
    """
    # В будущем здесь может быть логика очистки логов, кеша и т.д.
    print("🧹 Очистка временных данных...")
    return 0


# ===== АНАЛИЗ ДИСКОВОГО ПРОСТРАНСТВА =====

async def analyze_disk_usage() -> Dict:
    """Анализирует использование дискового пространства"""
    analysis = {
        "media_dir_size_mb": 0,
        "media_files_count": 0,
        "database_size_mb": 0,
        "total_size_mb": 0,
        "analysis_date": datetime.utcnow().isoformat()
    }
    
    try:
        # Размер медиа директории
        if os.path.exists(MEDIA_DIR):
            media_size = 0
            media_count = 0
            for root, dirs, files in os.walk(MEDIA_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        media_size += os.path.getsize(file_path)
                        media_count += 1
            
            analysis["media_dir_size_mb"] = round(media_size / (1024 * 1024), 2)
            analysis["media_files_count"] = media_count
        
        # Размер базы данных
        db_files = ["tickets.db", "tickets.db-shm", "tickets.db-wal"]
        db_size = 0
        for db_file in db_files:
            if os.path.exists(db_file):
                db_size += os.path.getsize(db_file)
        
        analysis["database_size_mb"] = round(db_size / (1024 * 1024), 2)
        analysis["total_size_mb"] = analysis["media_dir_size_mb"] + analysis["database_size_mb"]
        
    except Exception as e:
        print(f"❌ Ошибка анализа дискового пространства: {e}")
    
    return analysis


# ===== СТАТИСТИКА ОЧИСТКИ =====

async def get_cleanup_candidates(days: int = DEFAULT_RETENTION_DAYS) -> Dict:
    """
    Получает информацию о данных-кандидатах на удаление
    без их фактического удаления.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    candidates_info = {
        "cutoff_date": cutoff_date.isoformat(),
        "tickets_to_delete": 0,
        "files_to_delete": 0,
        "estimated_space_freed_mb": 0
    }
    
    try:
        async with async_session_maker() as session:
            # Подсчитываем заявки для удаления
            old_tickets_query = select(Ticket).where(Ticket.created_at < cutoff_date)
            result = await session.exec(old_tickets_query)
            old_tickets = result.all()
            
            candidates_info["tickets_to_delete"] = len(old_tickets)
            
            # Подсчитываем файлы и их размер
            files_size = 0
            files_count = 0
            for ticket in old_tickets:
                for photo_path in [ticket.before_photo_path, ticket.after_photo_path]:
                    if photo_path and os.path.exists(photo_path):
                        try:
                            files_size += os.path.getsize(photo_path)
                            files_count += 1
                        except:
                            pass
            
            candidates_info["files_to_delete"] = files_count
            candidates_info["estimated_space_freed_mb"] = round(files_size / (1024 * 1024), 2)
    
    except Exception as e:
        print(f"❌ Ошибка получения кандидатов на удаление: {e}")
    
    return candidates_info


# ===== ПЛАНИРОВЩИК ЗАДАЧ =====

async def scheduled_cleanup():
    """Функция для планировщика - ежедневная очистка"""
    print("📅 Запуск планового задания очистки...")
    try:
        stats = await cleanup_old_data()
        print(f"✅ Плановая очистка завершена: {stats}")
    except Exception as e:
        print(f"❌ Ошибка планового задания: {e}")


async def weekly_analysis():
    """Еженедельный анализ использования дискового пространства"""
    print("📊 Запуск еженедельного анализа...")
    try:
        analysis = await analyze_disk_usage()
        candidates = await get_cleanup_candidates()
        
        print(f"📊 Анализ дискового пространства:")
        print(f"   Медиа файлы: {analysis['media_files_count']} файлов, {analysis['media_dir_size_mb']} МБ")
        print(f"   База данных: {analysis['database_size_mb']} МБ")
        print(f"   Кандидатов на удаление: {candidates['tickets_to_delete']} заявок")
        
    except Exception as e:
        print(f"❌ Ошибка еженедельного анализа: {e}")


def init_scheduler():
    """Инициализация планировщика задач"""
    global scheduler
    
    if scheduler is not None:
        return scheduler
    
    scheduler = AsyncIOScheduler()
    
    # Ежедневная очистка в 2:00 ночи
    scheduler.add_job(
        scheduled_cleanup,
        CronTrigger(hour=2, minute=0),
        id="daily_cleanup",
        name="Ежедневная очистка данных",
        replace_existing=True
    )
    
    # Еженедельный анализ по воскресеньям в 3:00
    scheduler.add_job(
        weekly_analysis,
        CronTrigger(day_of_week=6, hour=3, minute=0),  # 6 = Sunday
        id="weekly_analysis",
        name="Еженедельный анализ дискового пространства",
        replace_existing=True
    )
    
    print("⏰ Планировщик задач инициализирован")
    return scheduler


def start_scheduler():
    """Запуск планировщика задач"""
    global scheduler
    
    if scheduler is None:
        scheduler = init_scheduler()
    
    if not scheduler.running:
        scheduler.start()
        print("🚀 Планировщик задач запущен")
        
        # Показываем запланированные задания
        for job in scheduler.get_jobs():
            print(f"   📅 {job.name}: {job.next_run_time}")
    else:
        print("⚠️ Планировщик уже запущен")


def stop_scheduler():
    """Остановка планировщика задач"""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown()
        print("🛑 Планировщик задач остановлен")
    else:
        print("⚠️ Планировщик не запущен")


# ===== УПРАВЛЯЮЩИЕ ФУНКЦИИ =====

async def force_cleanup(retention_days: int = DEFAULT_RETENTION_DAYS) -> Dict:
    """Принудительная очистка (вызывается вручную)"""
    print(f"🔧 Принудительная очистка (retention: {retention_days} дней)")
    return await cleanup_old_data(retention_days)


async def get_scheduler_status() -> Dict:
    """Получает статус планировщика"""
    global scheduler
    
    status = {
        "running": False,
        "jobs": [],
        "next_cleanup": None,
        "last_run": None
    }
    
    if scheduler:
        status["running"] = scheduler.running
        
        for job in scheduler.get_jobs():
            job_info = {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            }
            status["jobs"].append(job_info)
            
            if job.id == "daily_cleanup":
                status["next_cleanup"] = job.next_run_time.isoformat() if job.next_run_time else None
    
    return status


# ===== ЭКСПОРТ ФУНКЦИЙ =====

__all__ = [
    "cleanup_old_data",
    "cleanup_orphaned_files", 
    "analyze_disk_usage",
    "get_cleanup_candidates",
    "init_scheduler",
    "start_scheduler", 
    "stop_scheduler",
    "force_cleanup",
    "get_scheduler_status"
]