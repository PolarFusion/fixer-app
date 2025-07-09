"""
Модели данных для системы ремонтно-монтажных заявок.
Использует SQLModel для совместимости с FastAPI и SQLAlchemy.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
import uuid


class UserRole(str, Enum):
    """Роли пользователей в системе"""
    ADMIN = "admin"
    EXECUTOR = "executor" 
    CUSTOMER = "customer"


class TicketStatus(str, Enum):
    """Статусы заявок"""
    PENDING = "pending"        # Ожидает назначения
    IN_PROGRESS = "in_progress"  # В работе
    DONE = "done"             # Выполнено
    REJECTED = "rejected"     # Отклонено


# ===== ПОЛЬЗОВАТЕЛИ =====

class UserBase(SQLModel):
    """Базовая модель пользователя"""
    email: str = Field(unique=True, index=True)
    full_name: str
    role: UserRole
    is_active: bool = True


class User(UserBase, table=True):
    """Модель пользователя в БД"""
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Связи
    created_tickets: List["Ticket"] = Relationship(
        back_populates="customer",
        sa_relationship_kwargs={"foreign_keys": "Ticket.customer_id"}
    )
    assigned_tickets: List["Ticket"] = Relationship(
        back_populates="executor", 
        sa_relationship_kwargs={"foreign_keys": "Ticket.executor_id"}
    )


class UserCreate(UserBase):
    """Схема создания пользователя"""
    password: str


class UserPublic(UserBase):
    """Публичная схема пользователя"""
    id: int
    created_at: datetime


# ===== ЗАЯВКИ =====

class TicketBase(SQLModel):
    """Базовая модель заявки"""
    title: str
    address: str
    description: str
    deadline: datetime
    priority: int = Field(default=1, ge=1, le=5)  # 1-низкий, 5-критический


class Ticket(TicketBase, table=True):
    """Модель заявки в БД"""
    id: Optional[int] = Field(default=None, primary_key=True)
    status: TicketStatus = Field(default=TicketStatus.PENDING)
    
    # Внешние ключи
    customer_id: int = Field(foreign_key="user.id")
    executor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    # Временные метки
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Результат работы
    completion_comment: Optional[str] = None
    rejection_reason: Optional[str] = None
    before_photo_path: Optional[str] = None
    after_photo_path: Optional[str] = None
    
    # Связи
    customer: User = Relationship(
        back_populates="created_tickets",
        sa_relationship_kwargs={"foreign_keys": "Ticket.customer_id"}
    )
    executor: Optional[User] = Relationship(
        back_populates="assigned_tickets",
        sa_relationship_kwargs={"foreign_keys": "Ticket.executor_id"}
    )


class TicketCreate(TicketBase):
    """Схема создания заявки"""
    executor_id: Optional[int] = None


class TicketUpdate(SQLModel):
    """Схема обновления заявки"""
    status: Optional[TicketStatus] = None
    executor_id: Optional[int] = None
    completion_comment: Optional[str] = None
    rejection_reason: Optional[str] = None


class TicketPublic(TicketBase):
    """Публичная схема заявки"""
    id: int
    status: TicketStatus
    customer_id: int
    executor_id: Optional[int]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    completion_comment: Optional[str]
    rejection_reason: Optional[str]
    before_photo_path: Optional[str]
    after_photo_path: Optional[str]
    
    # Вложенные объекты
    customer: Optional[UserPublic] = None
    executor: Optional[UserPublic] = None


# ===== АУТЕНТИФИКАЦИЯ =====

class Token(SQLModel):
    """Модель JWT токена"""
    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    """Данные из JWT токена"""
    user_id: Optional[int] = None


# ===== СТАТИСТИКА =====

class TicketStats(SQLModel):
    """Статистика по заявкам"""
    total_tickets: int
    pending_tickets: int
    in_progress_tickets: int
    done_tickets: int
    rejected_tickets: int
    avg_completion_time_hours: Optional[float] = None


class DashboardData(SQLModel):
    """Данные для дашборда"""
    stats: TicketStats
    recent_tickets: List[TicketPublic]
    my_tickets: Optional[List[TicketPublic]] = None


# ===== ОТЧЕТЫ =====

class ReportType(str, Enum):
    """Типы отчетов"""
    PDF = "pdf"
    XLSX = "xlsx"


class DigestRange(str, Enum):
    """Период для сводных отчетов"""
    DAILY = "daily"
    WEEKLY = "weekly"


# ===== WEBSOCKET =====

class WSMessage(SQLModel):
    """Сообщение WebSocket"""
    type: str  # "ticket_created", "ticket_updated", "notification"
    data: dict
    recipient_user_id: Optional[int] = None  # None = broadcast
    timestamp: datetime = Field(default_factory=datetime.utcnow)