"""
Роутер для управления заявками.
Обрабатывает создание, просмотр, обновление заявок, загрузку фото.
"""

import os
import uuid
from datetime import datetime
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import aiofiles
import json

from database import get_session, get_ticket_by_id, get_tickets_for_user, get_executors, get_ticket_stats
from models import (
    Ticket, TicketCreate, TicketUpdate, TicketPublic, TicketStatus, 
    User, UserRole, DashboardData, TicketStats, WSMessage
)
from routers.auth import get_current_active_user, check_admin_role

# ===== КОНФИГУРАЦИЯ =====

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

# Настройки загрузки файлов
MEDIA_DIR = "media"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Создаем директорию для медиа файлов
os.makedirs(MEDIA_DIR, exist_ok=True)

# ===== WEBSOCKET МЕНЕДЖЕР =====

class ConnectionManager:
    """Менеджер WebSocket соединений для realtime уведомлений"""
    
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}  # user_id -> websocket
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Подключает пользователя к WebSocket"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"📡 Пользователь {user_id} подключился к WebSocket")
    
    def disconnect(self, user_id: int):
        """Отключает пользователя от WebSocket"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"📡 Пользователь {user_id} отключился от WebSocket")
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Отправляет персональное сообщение пользователю"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message, default=str))
            except Exception as e:
                print(f"❌ Ошибка отправки сообщения пользователю {user_id}: {e}")
                self.disconnect(user_id)
    
    async def broadcast(self, message: dict, exclude_user_id: Optional[int] = None):
        """Рассылает сообщение всем подключенным пользователям"""
        for user_id, connection in list(self.active_connections.items()):
            if exclude_user_id and user_id == exclude_user_id:
                continue
            try:
                await connection.send_text(json.dumps(message, default=str))
            except Exception as e:
                print(f"❌ Ошибка рассылки пользователю {user_id}: {e}")
                self.disconnect(user_id)

# Глобальный экземпляр менеджера соединений
manager = ConnectionManager()


# ===== УТИЛИТЫ =====

def validate_file(file: UploadFile) -> bool:
    """Проверяет валидность загружаемого файла"""
    if not file.filename:
        return False
    
    # Проверяем расширение
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False
    
    return True


async def save_uploaded_file(file: UploadFile, prefix: str = "") -> str:
    """Сохраняет загруженный файл и возвращает путь"""
    if not validate_file(file):
        raise HTTPException(status_code=400, detail="Недопустимый тип файла")
    
    # Генерируем уникальное имя файла
    file_ext = os.path.splitext(file.filename)[1].lower()
    unique_filename = f"{prefix}{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(MEDIA_DIR, unique_filename)
    
    # Сохраняем файл
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Файл слишком большой")
        await f.write(content)
    
    return file_path


async def notify_ticket_update(ticket: Ticket, action: str, session: AsyncSession):
    """Отправляет уведомления об изменении заявки"""
    # Получаем полную информацию о заявке
    full_ticket = await get_ticket_by_id(session, ticket.id)
    if not full_ticket:
        return
    
    # Формируем сообщение
    message = {
        "type": "ticket_updated",
        "action": action,  # "created", "assigned", "status_changed", etc.
        "ticket": {
            "id": full_ticket.id,
            "title": full_ticket.title,
            "status": full_ticket.status,
            "customer_name": full_ticket.customer.full_name if full_ticket.customer else None,
            "executor_name": full_ticket.executor.full_name if full_ticket.executor else None
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Отправляем уведомления заинтересованным сторонам
    recipients = []
    
    if full_ticket.customer_id:
        recipients.append(full_ticket.customer_id)
    if full_ticket.executor_id:
        recipients.append(full_ticket.executor_id)
    
    # Уведомляем конкретных пользователей
    for user_id in recipients:
        await manager.send_personal_message(message, user_id)
    
    # Рассылаем всем админам
    # TODO: Можно оптимизировать, получив список админов из БД
    await manager.broadcast(message)


# ===== WEBSOCKET ЭНДПОИНТЫ =====

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket эндпоинт для realtime уведомлений"""
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Слушаем сообщения от клиента (пинг/понг)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(user_id)


# ===== ОСНОВНЫЕ ЭНДПОИНТЫ =====

@router.post("/", response_model=TicketPublic)
async def create_ticket(
    title: str = Form(...),
    address: str = Form(...),
    description: str = Form(...),
    deadline: str = Form(...),  # ISO datetime string
    priority: int = Form(1),
    executor_id: Optional[int] = Form(None),
    current_user: Annotated[User, Depends(get_current_active_user)] = Depends(),
    session: AsyncSession = Depends(get_session)
):
    """
    Создание новой заявки.
    Клиенты могут создавать заявки, админы могут сразу назначать исполнителя.
    """
    # Проверяем права на создание заявок
    if current_user.role not in [UserRole.CUSTOMER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для создания заявок"
        )
    
    # Парсим дату
    try:
        deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты")
    
    # Проверяем исполнителя (если указан)
    if executor_id:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только администраторы могут назначать исполнителей"
            )
        
        executor = await session.get(User, executor_id)
        if not executor or executor.role != UserRole.EXECUTOR:
            raise HTTPException(status_code=400, detail="Указанный исполнитель не найден")
    
    # Создаем заявку
    ticket = Ticket(
        title=title,
        address=address,
        description=description,
        deadline=deadline_dt,
        priority=priority,
        customer_id=current_user.id,
        executor_id=executor_id,
        status=TicketStatus.IN_PROGRESS if executor_id else TicketStatus.PENDING,
        started_at=datetime.utcnow() if executor_id else None
    )
    
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    
    # Получаем полную информацию о заявке
    full_ticket = await get_ticket_by_id(session, ticket.id)
    
    # Отправляем уведомления
    await notify_ticket_update(ticket, "created", session)
    
    return full_ticket


@router.get("/", response_model=List[TicketPublic])
async def get_tickets(
    status: Optional[TicketStatus] = None,
    executor_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: Annotated[User, Depends(get_current_active_user)] = Depends(),
    session: AsyncSession = Depends(get_session)
):
    """
    Получение списка заявок с фильтрацией.
    Права доступа зависят от роли пользователя.
    """
    # Получаем заявки в зависимости от роли
    tickets = await get_tickets_for_user(session, current_user.id, current_user.role)
    
    # Применяем фильтры
    if status:
        tickets = [t for t in tickets if t.status == status]
    
    if executor_id:
        tickets = [t for t in tickets if t.executor_id == executor_id]
    
    # Применяем пагинацию
    tickets = tickets[offset:offset + limit]
    
    return tickets


@router.get("/{ticket_id}", response_model=TicketPublic)
async def get_ticket(
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)] = Depends(),
    session: AsyncSession = Depends(get_session)
):
    """Получение информации о конкретной заявке"""
    ticket = await get_ticket_by_id(session, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    # Проверяем права доступа
    if current_user.role == UserRole.CUSTOMER and ticket.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этой заявке")
    elif current_user.role == UserRole.EXECUTOR and ticket.executor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этой заявке")
    
    return ticket


@router.put("/{ticket_id}", response_model=TicketPublic)
async def update_ticket(
    ticket_id: int,
    status: Optional[TicketStatus] = Form(None),
    executor_id: Optional[int] = Form(None),
    completion_comment: Optional[str] = Form(None),
    rejection_reason: Optional[str] = Form(None),
    before_photo: Optional[UploadFile] = File(None),
    after_photo: Optional[UploadFile] = File(None),
    current_user: Annotated[User, Depends(get_current_active_user)] = Depends(),
    session: AsyncSession = Depends(get_session)
):
    """
    Обновление заявки.
    Разные роли имеют разные права на изменение полей.
    """
    ticket = await get_ticket_by_id(session, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    # Проверяем права доступа
    can_edit = False
    if current_user.role == UserRole.ADMIN:
        can_edit = True
    elif current_user.role == UserRole.EXECUTOR and ticket.executor_id == current_user.id:
        can_edit = True
    elif current_user.role == UserRole.CUSTOMER and ticket.customer_id == current_user.id:
        # Клиент может редактировать только свои заявки в статусе PENDING
        can_edit = ticket.status == TicketStatus.PENDING
    
    if not can_edit:
        raise HTTPException(status_code=403, detail="Нет прав на редактирование этой заявки")
    
    # Обновляем поля
    updates_made = []
    
    if status is not None:
        old_status = ticket.status
        ticket.status = status
        
        # Обновляем временные метки
        if status == TicketStatus.IN_PROGRESS and old_status == TicketStatus.PENDING:
            ticket.started_at = datetime.utcnow()
        elif status == TicketStatus.DONE:
            ticket.completed_at = datetime.utcnow()
            # Для завершения требуется комментарий
            if not completion_comment:
                raise HTTPException(
                    status_code=400, 
                    detail="Для завершения заявки необходим комментарий"
                )
        elif status == TicketStatus.REJECTED:
            # Для отклонения требуется причина
            if not rejection_reason:
                raise HTTPException(
                    status_code=400,
                    detail="Для отклонения заявки необходимо указать причину"
                )
        
        updates_made.append(f"статус изменен с {old_status} на {status}")
    
    if executor_id is not None and current_user.role == UserRole.ADMIN:
        ticket.executor_id = executor_id
        if executor_id and ticket.status == TicketStatus.PENDING:
            ticket.status = TicketStatus.IN_PROGRESS
            ticket.started_at = datetime.utcnow()
        updates_made.append("назначен исполнитель")
    
    if completion_comment is not None:
        ticket.completion_comment = completion_comment
        updates_made.append("добавлен комментарий")
    
    if rejection_reason is not None:
        ticket.rejection_reason = rejection_reason
        updates_made.append("указана причина отклонения")
    
    # Обрабатываем загрузку фото
    if before_photo and before_photo.filename:
        file_path = await save_uploaded_file(before_photo, "before_")
        ticket.before_photo_path = file_path
        updates_made.append("загружено фото 'до'")
    
    if after_photo and after_photo.filename:
        file_path = await save_uploaded_file(after_photo, "after_")
        ticket.after_photo_path = file_path
        updates_made.append("загружено фото 'после'")
    
    # Сохраняем изменения
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    
    # Получаем обновленную информацию
    updated_ticket = await get_ticket_by_id(session, ticket_id)
    
    # Отправляем уведомления
    action = "status_changed" if status else "updated"
    await notify_ticket_update(ticket, action, session)
    
    return updated_ticket


@router.delete("/{ticket_id}")
async def delete_ticket(
    ticket_id: int,
    current_user: Annotated[User, Depends(check_admin_role)] = Depends(),
    session: AsyncSession = Depends(get_session)
):
    """Удаление заявки (только для админов)"""
    ticket = await get_ticket_by_id(session, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    # Удаляем связанные файлы
    for photo_path in [ticket.before_photo_path, ticket.after_photo_path]:
        if photo_path and os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except Exception as e:
                print(f"Ошибка удаления файла {photo_path}: {e}")
    
    await session.delete(ticket)
    await session.commit()
    
    return {"message": "Заявка удалена"}


# ===== ДОПОЛНИТЕЛЬНЫЕ ЭНДПОИНТЫ =====

@router.get("/executors/list", response_model=List[dict])
async def get_executors_list(
    current_user: Annotated[User, Depends(get_current_active_user)] = Depends(),
    session: AsyncSession = Depends(get_session)
):
    """Получение списка исполнителей для назначения"""
    executors = await get_executors(session)
    return [
        {"id": executor.id, "full_name": executor.full_name, "email": executor.email}
        for executor in executors
    ]


@router.get("/media/{filename}")
async def get_media_file(filename: str):
    """Получение медиа файла"""
    file_path = os.path.join(MEDIA_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    return FileResponse(file_path)


@router.get("/dashboard/data", response_model=DashboardData)
async def get_dashboard_data(
    current_user: Annotated[User, Depends(get_current_active_user)] = Depends(),
    session: AsyncSession = Depends(get_session)
):
    """Получение данных для дашборда"""
    # Получаем статистику
    stats_data = await get_ticket_stats(session)
    stats = TicketStats(**stats_data)
    
    # Получаем последние заявки
    all_tickets = await get_tickets_for_user(session, current_user.id, current_user.role)
    recent_tickets = all_tickets[:10]  # Последние 10
    
    # Получаем личные заявки (для исполнителей и клиентов)
    my_tickets = None
    if current_user.role in [UserRole.EXECUTOR, UserRole.CUSTOMER]:
        my_tickets = [t for t in all_tickets if 
                     (current_user.role == UserRole.EXECUTOR and t.executor_id == current_user.id) or
                     (current_user.role == UserRole.CUSTOMER and t.customer_id == current_user.id)][:5]
    
    return DashboardData(
        stats=stats,
        recent_tickets=recent_tickets,
        my_tickets=my_tickets
    )