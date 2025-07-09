"""
Роутер аутентификации и авторизации.
Обрабатывает регистрацию, логин, управление JWT токенами.
"""

from datetime import datetime, timedelta
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session, get_user_by_email, get_user_by_id
from models import User, UserCreate, UserPublic, Token, TokenData, UserRole

# ===== КОНФИГУРАЦИЯ =====

router = APIRouter(prefix="/api/auth", tags=["auth"])

# JWT настройки
SECRET_KEY = "your-secret-key-change-in-production"  # В продакшене использовать переменную окружения
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 часа

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 схема для получения токена из заголовков
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ===== УТИЛИТЫ АУТЕНТИФИКАЦИИ =====

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет соответствие пароля хешу"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Создает хеш пароля"""
    return pwd_context.hash(password)


async def authenticate_user(session: AsyncSession, email: str, password: str) -> Optional[User]:
    """Аутентифицирует пользователя по email и паролю"""
    user = await get_user_by_email(session, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создает JWT токен доступа"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Получает текущего пользователя из JWT токена.
    Используется как dependency в защищенных эндпоинтах.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверные учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_id(session, user_id=token_data.user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Проверяет, что пользователь активен"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Неактивный пользователь")
    return current_user


def check_admin_role(current_user: Annotated[User, Depends(get_current_active_user)]):
    """Проверяет права администратора"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    return current_user


# ===== ЭНДПОИНТЫ =====

@router.post("/register", response_model=UserPublic)
async def register_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Регистрация нового пользователя.
    Проверяет уникальность email и создает пользователя с хешированным паролем.
    """
    # Проверяем, не существует ли пользователь с таким email
    existing_user = await get_user_by_email(session, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    # Создаем пользователя с хешированным паролем
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=user_data.is_active,
        hashed_password=hashed_password
    )
    
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: AsyncSession = Depends(get_session)
):
    """
    Аутентификация пользователя и выдача JWT токена.
    Принимает email в поле username (стандарт OAuth2).
    """
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserPublic)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Получение информации о текущем пользователе"""
    return current_user


@router.get("/users", response_model=list[UserPublic])
async def get_all_users(
    current_user: Annotated[User, Depends(check_admin_role)],
    session: AsyncSession = Depends(get_session)
):
    """Получение списка всех пользователей (только для админов)"""
    from sqlmodel import select
    
    result = await session.exec(select(User))
    users = result.all()
    return users


@router.put("/users/{user_id}/toggle", response_model=UserPublic)
async def toggle_user_status(
    user_id: int,
    current_user: Annotated[User, Depends(check_admin_role)],
    session: AsyncSession = Depends(get_session)
):
    """Включение/отключение пользователя (только для админов)"""
    user = await get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    user.is_active = not user.is_active
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    return user


@router.post("/change-password")
async def change_password(
    old_password: str = Form(...),
    new_password: str = Form(...),
    current_user: Annotated[User, Depends(get_current_active_user)] = Depends(),
    session: AsyncSession = Depends(get_session)
):
    """Смена пароля пользователя"""
    # Проверяем старый пароль
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль"
        )
    
    # Устанавливаем новый пароль
    current_user.hashed_password = get_password_hash(new_password)
    session.add(current_user)
    await session.commit()
    
    return {"message": "Пароль успешно изменен"}


# ===== ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ =====

def get_user_permissions(user: User) -> dict:
    """Возвращает права доступа пользователя в зависимости от роли"""
    permissions = {
        "can_create_tickets": False,
        "can_edit_own_tickets": False,
        "can_view_all_tickets": False,
        "can_assign_tickets": False,
        "can_manage_users": False,
        "can_generate_reports": False
    }
    
    if user.role == UserRole.CUSTOMER:
        permissions.update({
            "can_create_tickets": True,
            "can_edit_own_tickets": True
        })
    elif user.role == UserRole.EXECUTOR:
        permissions.update({
            "can_view_all_tickets": True  # Только назначенные
        })
    elif user.role == UserRole.ADMIN:
        permissions.update({
            "can_create_tickets": True,
            "can_edit_own_tickets": True,
            "can_view_all_tickets": True,
            "can_assign_tickets": True,
            "can_manage_users": True,
            "can_generate_reports": True
        })
    
    return permissions


@router.get("/permissions")
async def get_my_permissions(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Получение прав доступа текущего пользователя"""
    return get_user_permissions(current_user)