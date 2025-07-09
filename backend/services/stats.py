"""
Сервис для расчета статистики и аналитики по заявкам.
Включает детальную статистику, тренды, производительность исполнителей.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import Ticket, TicketStatus, User, UserRole
from database import async_session_maker


# ===== ОБЩАЯ СТАТИСТИКА =====

async def get_basic_stats(session: AsyncSession) -> Dict:
    """Получает базовую статистику по заявкам"""
    # Подсчет по статусам
    stats = {}
    
    for status in TicketStatus:
        count_query = select(func.count(Ticket.id)).where(Ticket.status == status)
        result = await session.exec(count_query)
        stats[f"{status.value}_count"] = result.first() or 0
    
    # Общее количество
    total_query = select(func.count(Ticket.id))
    result = await session.exec(total_query)
    stats["total_count"] = result.first() or 0
    
    return stats


async def get_completion_stats(session: AsyncSession) -> Dict:
    """Получает статистику по времени выполнения"""
    # Среднее время выполнения
    avg_query = select(
        func.avg(
            func.julianday(Ticket.completed_at) - func.julianday(Ticket.started_at)
        ) * 24  # В часах
    ).where(
        Ticket.status == TicketStatus.DONE,
        Ticket.started_at.isnot(None),
        Ticket.completed_at.isnot(None)
    )
    result = await session.exec(avg_query)
    avg_completion_time = result.first()
    
    # Минимальное и максимальное время
    min_query = select(
        func.min(
            func.julianday(Ticket.completed_at) - func.julianday(Ticket.started_at)
        ) * 24
    ).where(
        Ticket.status == TicketStatus.DONE,
        Ticket.started_at.isnot(None),
        Ticket.completed_at.isnot(None)
    )
    result = await session.exec(min_query)
    min_completion_time = result.first()
    
    max_query = select(
        func.max(
            func.julianday(Ticket.completed_at) - func.julianday(Ticket.started_at)
        ) * 24
    ).where(
        Ticket.status == TicketStatus.DONE,
        Ticket.started_at.isnot(None),
        Ticket.completed_at.isnot(None)
    )
    result = await session.exec(max_query)
    max_completion_time = result.first()
    
    return {
        "avg_completion_time_hours": round(avg_completion_time, 2) if avg_completion_time else None,
        "min_completion_time_hours": round(min_completion_time, 2) if min_completion_time else None,
        "max_completion_time_hours": round(max_completion_time, 2) if max_completion_time else None
    }


# ===== СТАТИСТИКА ПО ИСПОЛНИТЕЛЯМ =====

async def get_executor_performance(session: AsyncSession, days: int = 30) -> List[Dict]:
    """Получает статистику производительности исполнителей"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Получаем всех исполнителей
    executors_query = select(User).where(User.role == UserRole.EXECUTOR)
    result = await session.exec(executors_query)
    executors = result.all()
    
    performance_data = []
    
    for executor in executors:
        # Общее количество заявок
        total_query = select(func.count(Ticket.id)).where(
            Ticket.executor_id == executor.id,
            Ticket.created_at >= cutoff_date
        )
        result = await session.exec(total_query)
        total_tickets = result.first() or 0
        
        # Выполненные заявки
        completed_query = select(func.count(Ticket.id)).where(
            Ticket.executor_id == executor.id,
            Ticket.status == TicketStatus.DONE,
            Ticket.created_at >= cutoff_date
        )
        result = await session.exec(completed_query)
        completed_tickets = result.first() or 0
        
        # Среднее время выполнения
        avg_time_query = select(
            func.avg(
                func.julianday(Ticket.completed_at) - func.julianday(Ticket.started_at)
            ) * 24
        ).where(
            Ticket.executor_id == executor.id,
            Ticket.status == TicketStatus.DONE,
            Ticket.started_at.isnot(None),
            Ticket.completed_at.isnot(None),
            Ticket.created_at >= cutoff_date
        )
        result = await session.exec(avg_time_query)
        avg_time = result.first()
        
        # Заявки в работе
        in_progress_query = select(func.count(Ticket.id)).where(
            Ticket.executor_id == executor.id,
            Ticket.status == TicketStatus.IN_PROGRESS,
            Ticket.created_at >= cutoff_date
        )
        result = await session.exec(in_progress_query)
        in_progress_tickets = result.first() or 0
        
        # Процент завершения
        completion_rate = (completed_tickets / total_tickets * 100) if total_tickets > 0 else 0
        
        performance_data.append({
            "executor_id": executor.id,
            "executor_name": executor.full_name,
            "total_tickets": total_tickets,
            "completed_tickets": completed_tickets,
            "in_progress_tickets": in_progress_tickets,
            "completion_rate": round(completion_rate, 1),
            "avg_completion_time_hours": round(avg_time, 2) if avg_time else None
        })
    
    # Сортируем по количеству выполненных заявок
    performance_data.sort(key=lambda x: x["completed_tickets"], reverse=True)
    return performance_data


# ===== ВРЕМЕННЫЕ ТРЕНДЫ =====

async def get_daily_trends(session: AsyncSession, days: int = 30) -> List[Dict]:
    """Получает ежедневные тренды создания и завершения заявок"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    trends = []
    
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        next_date = current_date + timedelta(days=1)
        
        # Созданные заявки
        created_query = select(func.count(Ticket.id)).where(
            Ticket.created_at >= current_date,
            Ticket.created_at < next_date
        )
        result = await session.exec(created_query)
        created_count = result.first() or 0
        
        # Завершенные заявки
        completed_query = select(func.count(Ticket.id)).where(
            Ticket.completed_at >= current_date,
            Ticket.completed_at < next_date,
            Ticket.status == TicketStatus.DONE
        )
        result = await session.exec(completed_query)
        completed_count = result.first() or 0
        
        trends.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "created_tickets": created_count,
            "completed_tickets": completed_count
        })
    
    return trends


async def get_weekly_trends(session: AsyncSession, weeks: int = 12) -> List[Dict]:
    """Получает недельные тренды"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(weeks=weeks)
    
    trends = []
    
    for i in range(weeks):
        week_start = start_date + timedelta(weeks=i)
        week_end = week_start + timedelta(weeks=1)
        
        # Созданные заявки
        created_query = select(func.count(Ticket.id)).where(
            Ticket.created_at >= week_start,
            Ticket.created_at < week_end
        )
        result = await session.exec(created_query)
        created_count = result.first() or 0
        
        # Завершенные заявки
        completed_query = select(func.count(Ticket.id)).where(
            Ticket.completed_at >= week_start,
            Ticket.completed_at < week_end,
            Ticket.status == TicketStatus.DONE
        )
        result = await session.exec(completed_query)
        completed_count = result.first() or 0
        
        trends.append({
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "created_tickets": created_count,
            "completed_tickets": completed_count
        })
    
    return trends


# ===== СТАТИСТИКА ПО ПРИОРИТЕТАМ =====

async def get_priority_stats(session: AsyncSession) -> List[Dict]:
    """Получает статистику по приоритетам заявок"""
    priority_stats = []
    
    for priority in range(1, 6):  # Приоритеты 1-5
        # Общее количество
        total_query = select(func.count(Ticket.id)).where(Ticket.priority == priority)
        result = await session.exec(total_query)
        total_count = result.first() or 0
        
        # Завершенные
        completed_query = select(func.count(Ticket.id)).where(
            Ticket.priority == priority,
            Ticket.status == TicketStatus.DONE
        )
        result = await session.exec(completed_query)
        completed_count = result.first() or 0
        
        # Среднее время выполнения
        avg_time_query = select(
            func.avg(
                func.julianday(Ticket.completed_at) - func.julianday(Ticket.started_at)
            ) * 24
        ).where(
            Ticket.priority == priority,
            Ticket.status == TicketStatus.DONE,
            Ticket.started_at.isnot(None),
            Ticket.completed_at.isnot(None)
        )
        result = await session.exec(avg_time_query)
        avg_time = result.first()
        
        completion_rate = (completed_count / total_count * 100) if total_count > 0 else 0
        
        priority_stats.append({
            "priority": priority,
            "total_tickets": total_count,
            "completed_tickets": completed_count,
            "completion_rate": round(completion_rate, 1),
            "avg_completion_time_hours": round(avg_time, 2) if avg_time else None
        })
    
    return priority_stats


# ===== ПРОСРОЧЕННЫЕ ЗАЯВКИ =====

async def get_overdue_tickets(session: AsyncSession) -> List[Dict]:
    """Получает список просроченных заявок"""
    now = datetime.utcnow()
    
    # Заявки с просроченным дедлайном и статусом не "выполнено"
    overdue_query = select(Ticket).where(
        Ticket.deadline < now,
        Ticket.status.in_([TicketStatus.PENDING, TicketStatus.IN_PROGRESS])
    )
    result = await session.exec(overdue_query)
    overdue_tickets = result.all()
    
    overdue_data = []
    for ticket in overdue_tickets:
        overdue_hours = (now - ticket.deadline).total_seconds() / 3600
        
        overdue_data.append({
            "ticket_id": ticket.id,
            "title": ticket.title,
            "status": ticket.status.value,
            "deadline": ticket.deadline.isoformat(),
            "overdue_hours": round(overdue_hours, 1),
            "priority": ticket.priority,
            "executor_id": ticket.executor_id
        })
    
    # Сортируем по количеству просроченных часов
    overdue_data.sort(key=lambda x: x["overdue_hours"], reverse=True)
    return overdue_data


# ===== СВОДНАЯ АНАЛИТИКА =====

async def get_comprehensive_analytics(session: AsyncSession) -> Dict:
    """Получает комплексную аналитику для дашборда администратора"""
    
    # Собираем все виды статистики
    basic_stats = await get_basic_stats(session)
    completion_stats = await get_completion_stats(session)
    executor_performance = await get_executor_performance(session, days=30)
    daily_trends = await get_daily_trends(session, days=7)  # Последние 7 дней
    priority_stats = await get_priority_stats(session)
    overdue_tickets = await get_overdue_tickets(session)
    
    return {
        "basic_stats": basic_stats,
        "completion_stats": completion_stats,
        "executor_performance": executor_performance[:10],  # Топ 10 исполнителей
        "daily_trends": daily_trends,
        "priority_stats": priority_stats,
        "overdue_tickets": overdue_tickets[:20],  # Топ 20 просроченных
        "analytics_generated_at": datetime.utcnow().isoformat()
    }


# ===== ПОЛЬЗОВАТЕЛЬСКАЯ СТАТИСТИКА =====

async def get_user_stats(session: AsyncSession, user_id: int, role: UserRole) -> Dict:
    """Получает персональную статистику пользователя"""
    stats = {}
    
    if role == UserRole.CUSTOMER:
        # Статистика для клиента
        total_query = select(func.count(Ticket.id)).where(Ticket.customer_id == user_id)
        result = await session.exec(total_query)
        stats["total_created"] = result.first() or 0
        
        for status in TicketStatus:
            status_query = select(func.count(Ticket.id)).where(
                Ticket.customer_id == user_id,
                Ticket.status == status
            )
            result = await session.exec(status_query)
            stats[f"{status.value}_count"] = result.first() or 0
    
    elif role == UserRole.EXECUTOR:
        # Статистика для исполнителя
        total_query = select(func.count(Ticket.id)).where(Ticket.executor_id == user_id)
        result = await session.exec(total_query)
        stats["total_assigned"] = result.first() or 0
        
        for status in TicketStatus:
            status_query = select(func.count(Ticket.id)).where(
                Ticket.executor_id == user_id,
                Ticket.status == status
            )
            result = await session.exec(status_query)
            stats[f"{status.value}_count"] = result.first() or 0
        
        # Среднее время выполнения
        avg_time_query = select(
            func.avg(
                func.julianday(Ticket.completed_at) - func.julianday(Ticket.started_at)
            ) * 24
        ).where(
            Ticket.executor_id == user_id,
            Ticket.status == TicketStatus.DONE,
            Ticket.started_at.isnot(None),
            Ticket.completed_at.isnot(None)
        )
        result = await session.exec(avg_time_query)
        avg_time = result.first()
        stats["avg_completion_time_hours"] = round(avg_time, 2) if avg_time else None
    
    elif role == UserRole.ADMIN:
        # Для админа - общая статистика
        stats = await get_basic_stats(session)
    
    return stats


# ===== УТИЛИТЫ =====

async def calculate_efficiency_score(session: AsyncSession, executor_id: int) -> float:
    """Рассчитывает оценку эффективности исполнителя (0-100)"""
    # Получаем статистику исполнителя за последние 30 дней
    performance = await get_executor_performance(session, days=30)
    executor_data = next((p for p in performance if p["executor_id"] == executor_id), None)
    
    if not executor_data or executor_data["total_tickets"] == 0:
        return 0.0
    
    # Факторы для оценки эффективности
    completion_rate = executor_data["completion_rate"]  # 0-100
    avg_time = executor_data["avg_completion_time_hours"] or 24  # Если None, то 24 часа
    
    # Нормализуем время выполнения (меньше время = выше балл)
    time_score = max(0, 100 - (avg_time / 24 * 100))  # 24 часа = 0 баллов
    
    # Итоговая оценка (50% completion rate + 50% time score)
    efficiency_score = (completion_rate * 0.5) + (time_score * 0.5)
    
    return round(efficiency_score, 1)


async def get_workload_distribution(session: AsyncSession) -> Dict:
    """Получает распределение нагрузки между исполнителями"""
    # Активные заявки по исполнителям
    active_tickets_query = select(
        Ticket.executor_id,
        func.count(Ticket.id).label("active_count")
    ).where(
        Ticket.status.in_([TicketStatus.PENDING, TicketStatus.IN_PROGRESS]),
        Ticket.executor_id.isnot(None)
    ).group_by(Ticket.executor_id)
    
    result = await session.exec(active_tickets_query)
    workload_data = result.all()
    
    # Получаем информацию об исполнителях
    executors_query = select(User).where(User.role == UserRole.EXECUTOR)
    result = await session.exec(executors_query)
    executors = result.all()
    
    # Формируем распределение
    distribution = []
    for executor in executors:
        active_count = next((w.active_count for w in workload_data if w.executor_id == executor.id), 0)
        distribution.append({
            "executor_id": executor.id,
            "executor_name": executor.full_name,
            "active_tickets": active_count
        })
    
    # Сортируем по нагрузке
    distribution.sort(key=lambda x: x["active_tickets"], reverse=True)
    
    total_active = sum(d["active_tickets"] for d in distribution)
    avg_load = total_active / len(distribution) if distribution else 0
    
    return {
        "distribution": distribution,
        "total_active_tickets": total_active,
        "average_load": round(avg_load, 1),
        "executors_count": len(distribution)
    }


# ===== ЭКСПОРТ ФУНКЦИЙ =====

__all__ = [
    "get_basic_stats",
    "get_completion_stats", 
    "get_executor_performance",
    "get_daily_trends",
    "get_weekly_trends",
    "get_priority_stats",
    "get_overdue_tickets",
    "get_comprehensive_analytics",
    "get_user_stats",
    "calculate_efficiency_score",
    "get_workload_distribution"
]