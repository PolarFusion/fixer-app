"""
Основное FastAPI приложение для системы ремонтно-монтажных заявок.
Интегрирует все компоненты: аутентификацию, CRUD операции, WebSocket, планировщик.
"""

import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Импорты модулей приложения
from database import init_db, get_session
from routers import auth, tickets, reports
from services.cleanup import start_scheduler, stop_scheduler, get_scheduler_status
from services.stats import get_comprehensive_analytics


# ===== LIFESPAN МЕНЕДЖЕР =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Менеджер жизненного цикла приложения.
    Инициализирует БД и запускает планировщик при старте,
    останавливает планировщик при завершении.
    """
    print("🚀 Запуск приложения...")
    
    # Инициализация при старте
    await init_db()
    start_scheduler()
    
    print("✅ Приложение готово к работе!")
    
    yield  # Здесь приложение работает
    
    # Очистка при завершении
    print("🛑 Завершение работы приложения...")
    stop_scheduler()
    print("✅ Приложение завершено")


# ===== СОЗДАНИЕ ПРИЛОЖЕНИЯ =====

app = FastAPI(
    title="Система ремонтно-монтажных заявок",
    description="API для управления заявками на ремонтно-монтажные работы с поддержкой ролей, файлов и отчетов",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)


# ===== НАСТРОЙКА CORS =====

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://frontend:3000",   # Docker frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== ПОДКЛЮЧЕНИЕ РОУТЕРОВ =====

# Роутер аутентификации
app.include_router(auth.router)

# Роутер заявок (включает WebSocket)
app.include_router(tickets.router)

# Роутер отчетов
app.include_router(reports.router)


# ===== СТАТИЧЕСКИЕ ФАЙЛЫ =====

# Подключаем медиа директорию для доступа к загруженным файлам
app.mount("/media", StaticFiles(directory="media"), name="media")


# ===== ОСНОВНЫЕ ЭНДПОИНТЫ =====

@app.get("/")
async def root():
    """Корневой эндпоинт - информация о приложении"""
    return {
        "name": "Система ремонтно-монтажных заявок",
        "version": "1.0.0",
        "description": "API для управления заявками с поддержкой ролей и отчетов",
        "docs": "/api/docs",
        "health": "/api/health"
    }


@app.get("/api/health")
async def health_check():
    """Проверка состояния приложения"""
    # Проверяем статус планировщика
    scheduler_status = await get_scheduler_status()
    
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",  # Placeholder
        "services": {
            "database": "connected",
            "scheduler": "running" if scheduler_status["running"] else "stopped",
            "media_dir": "available" if os.path.exists("media") else "missing"
        },
        "scheduler": scheduler_status
    }


@app.get("/api/info")
async def app_info():
    """Подробная информация о приложении"""
    return {
        "application": {
            "name": "Repair Management System",
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development")
        },
        "features": [
            "JWT Authentication",
            "Role-based Access Control",
            "File Upload Support", 
            "Real-time WebSocket Notifications",
            "PDF/XLSX Report Generation",
            "Automated Data Cleanup",
            "Statistics and Analytics"
        ],
        "supported_roles": ["admin", "executor", "customer"],
        "supported_formats": ["PDF", "XLSX"],
        "api_endpoints": {
            "authentication": "/api/auth/*",
            "tickets": "/api/tickets/*", 
            "reports": "/api/reports/*",
            "websocket": "/api/tickets/ws/{user_id}"
        }
    }


# ===== АДМИНИСТРАТИВНЫЕ ЭНДПОИНТЫ =====

@app.get("/api/admin/stats")
async def get_admin_analytics(
    session=Depends(get_session),
    current_user=Depends(auth.check_admin_role)
):
    """
    Получение комплексной аналитики для администраторов.
    Включает статистику, тренды, производительность исполнителей.
    """
    analytics = await get_comprehensive_analytics(session)
    return analytics


@app.get("/api/admin/scheduler")
async def get_scheduler_info(current_user=Depends(auth.check_admin_role)):
    """Информация о планировщике задач"""
    return await get_scheduler_status()


@app.post("/api/admin/cleanup")
async def manual_cleanup(
    retention_days: int = 90,
    current_user=Depends(auth.check_admin_role)
):
    """Ручной запуск очистки данных"""
    from services.cleanup import force_cleanup
    
    result = await force_cleanup(retention_days)
    return result


@app.get("/api/admin/disk-usage")
async def get_disk_usage(current_user=Depends(auth.check_admin_role)):
    """Анализ использования дискового пространства"""
    from services.cleanup import analyze_disk_usage, get_cleanup_candidates
    
    usage = await analyze_disk_usage()
    candidates = await get_cleanup_candidates()
    
    return {
        "current_usage": usage,
        "cleanup_candidates": candidates
    }


# ===== ОБРАБОТЧИКИ ОШИБОК =====

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Кастомный обработчик 404 ошибки"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Не найдено",
            "message": "Запрашиваемый ресурс не найден",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Кастомный обработчик 500 ошибки"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Внутренняя ошибка сервера",
            "message": "Произошла неожиданная ошибка. Попробуйте позже."
        }
    )


# ===== MIDDLEWARE =====

@app.middleware("http")
async def add_security_headers(request, call_next):
    """Добавляет заголовки безопасности"""
    response = await call_next(request)
    
    # Основные заголовки безопасности
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response


@app.middleware("http") 
async def log_requests(request, call_next):
    """Логирование запросов (упрощенное)"""
    import time
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    print(f"📝 {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    return response


# ===== ЗАПУСК ПРИЛОЖЕНИЯ =====

if __name__ == "__main__":
    # Конфигурация для разработки
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Автоперезагрузка при изменениях
        log_level="info"
    )