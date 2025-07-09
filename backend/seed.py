"""
Скрипт для заполнения базы данных тестовыми данными.
Создает 3 админа, 5 исполнителей, 10 клиентов и 20 заявок.
"""

import asyncio
from datetime import datetime, timedelta
import random

from database import init_db, async_session_maker
from models import User, Ticket, UserRole, TicketStatus
from routers.auth import get_password_hash


# ===== ТЕСТОВЫЕ ДАННЫЕ =====

ADMIN_DATA = [
    {
        "email": "admin1@company.com",
        "full_name": "Главный Администратор",
        "password": "admin123",
        "role": UserRole.ADMIN
    },
    {
        "email": "admin2@company.com", 
        "full_name": "Системный Администратор",
        "password": "admin123",
        "role": UserRole.ADMIN
    },
    {
        "email": "admin3@company.com",
        "full_name": "Технический Администратор", 
        "password": "admin123",
        "role": UserRole.ADMIN
    }
]

EXECUTOR_DATA = [
    {
        "email": "executor1@company.com",
        "full_name": "Иван Петров",
        "password": "exec123",
        "role": UserRole.EXECUTOR
    },
    {
        "email": "executor2@company.com",
        "full_name": "Анна Сидорова",
        "password": "exec123", 
        "role": UserRole.EXECUTOR
    },
    {
        "email": "executor3@company.com",
        "full_name": "Михаил Козлов",
        "password": "exec123",
        "role": UserRole.EXECUTOR
    },
    {
        "email": "executor4@company.com",
        "full_name": "Елена Морозова",
        "password": "exec123",
        "role": UserRole.EXECUTOR
    },
    {
        "email": "executor5@company.com",
        "full_name": "Дмитрий Волков",
        "password": "exec123",
        "role": UserRole.EXECUTOR
    }
]

CUSTOMER_DATA = [
    {
        "email": "customer1@gmail.com",
        "full_name": "Олег Смирнов",
        "password": "customer123",
        "role": UserRole.CUSTOMER
    },
    {
        "email": "customer2@gmail.com",
        "full_name": "Мария Васильева",
        "password": "customer123",
        "role": UserRole.CUSTOMER
    },
    {
        "email": "customer3@gmail.com", 
        "full_name": "Александр Новikov",
        "password": "customer123",
        "role": UserRole.CUSTOMER
    },
    {
        "email": "customer4@gmail.com",
        "full_name": "Татьяна Лебедева",
        "password": "customer123",
        "role": UserRole.CUSTOMER
    },
    {
        "email": "customer5@gmail.com",
        "full_name": "Сергей Кузнецов",
        "password": "customer123",
        "role": UserRole.CUSTOMER
    },
    {
        "email": "customer6@gmail.com",
        "full_name": "Наталья Федорова",
        "password": "customer123",
        "role": UserRole.CUSTOMER
    },
    {
        "email": "customer7@gmail.com",
        "full_name": "Владимир Медведев",
        "password": "customer123",
        "role": UserRole.CUSTOMER
    },
    {
        "email": "customer8@gmail.com",
        "full_name": "Ольга Романова",
        "password": "customer123",
        "role": UserRole.CUSTOMER
    },
    {
        "email": "customer9@gmail.com",
        "full_name": "Андрей Соколов",
        "password": "customer123",
        "role": UserRole.CUSTOMER
    },
    {
        "email": "customer10@gmail.com",
        "full_name": "Светлана Попова",
        "password": "customer123",
        "role": UserRole.CUSTOMER
    }
]

# Шаблоны заявок
TICKET_TEMPLATES = [
    {
        "title": "Ремонт водопровода",
        "description": "Течь в трубе на кухне, необходимо срочное устранение",
        "addresses": ["ул. Ленина, д. 15, кв. 42", "пр. Мира, д. 8, кв. 156", "ул. Пушкина, д. 23, кв. 78"]
    },
    {
        "title": "Замена электропроводки",
        "description": "Требуется замена старой проводки в квартире",
        "addresses": ["ул. Гагарина, д. 7, кв. 29", "ул. Советская, д. 45, кв. 12", "пр. Строителей, д. 33, кв. 91"]
    },
    {
        "title": "Установка кондиционера",
        "description": "Монтаж кондиционера в спальне с подключением", 
        "addresses": ["ул. Садовая, д. 19, кв. 67", "ул. Новая, д. 11, кв. 34", "пр. Победы, д. 2, кв. 145"]
    },
    {
        "title": "Ремонт отопления",
        "description": "Не работает радиатор отопления в комнате",
        "addresses": ["ул. Молодежная, д. 6, кв. 23", "ул. Центральная, д. 14, кв. 87", "пр. Космонавтов, д. 28, кв. 56"]
    },
    {
        "title": "Замена замков",
        "description": "Установка нового замка на входную дверь",
        "addresses": ["ул. Рабочая, д. 31, кв. 18", "ул. Школьная, д. 9, кв. 72", "пр. Ленинский, д. 16, кв. 103"]
    },
    {
        "title": "Ремонт сантехники", 
        "description": "Замена смесителя и ремонт душевой кабины",
        "addresses": ["ул. Парковая, д. 22, кв. 45", "ул. Речная, д. 5, кв. 134", "пр. Дружбы, д. 12, кв. 67"]
    },
    {
        "title": "Монтаж освещения",
        "description": "Установка люстры и дополнительных светильников",
        "addresses": ["ул. Зеленая, д. 8, кв. 26", "ул. Мирная, д. 18, кв. 89", "пр. Юбилейный, д. 4, кв. 112"]
    }
]


# ===== ФУНКЦИИ СОЗДАНИЯ ДАННЫХ =====

async def create_users(session):
    """Создает пользователей всех ролей"""
    users = []
    
    print("👥 Создание пользователей...")
    
    # Создаем админов
    for admin_data in ADMIN_DATA:
        user = User(
            email=admin_data["email"],
            full_name=admin_data["full_name"],
            role=admin_data["role"],
            hashed_password=get_password_hash(admin_data["password"]),
            is_active=True
        )
        session.add(user)
        users.append(user)
    
    # Создаем исполнителей
    for executor_data in EXECUTOR_DATA:
        user = User(
            email=executor_data["email"],
            full_name=executor_data["full_name"],
            role=executor_data["role"],
            hashed_password=get_password_hash(executor_data["password"]),
            is_active=True
        )
        session.add(user)
        users.append(user)
    
    # Создаем клиентов
    for customer_data in CUSTOMER_DATA:
        user = User(
            email=customer_data["email"],
            full_name=customer_data["full_name"],
            role=customer_data["role"],
            hashed_password=get_password_hash(customer_data["password"]),
            is_active=True
        )
        session.add(user)
        users.append(user)
    
    await session.commit()
    
    # Обновляем объекты для получения ID
    for user in users:
        await session.refresh(user)
    
    print(f"✅ Создано {len(users)} пользователей:")
    print(f"   • {len(ADMIN_DATA)} администраторов")
    print(f"   • {len(EXECUTOR_DATA)} исполнителей")
    print(f"   • {len(CUSTOMER_DATA)} клиентов")
    
    return users


async def create_tickets(session, users):
    """Создает тестовые заявки"""
    print("📋 Создание заявок...")
    
    # Разделяем пользователей по ролям
    admins = [u for u in users if u.role == UserRole.ADMIN]
    executors = [u for u in users if u.role == UserRole.EXECUTOR]
    customers = [u for u in users if u.role == UserRole.CUSTOMER]
    
    tickets = []
    
    # Создаем 20 заявок
    for i in range(20):
        # Выбираем случайный шаблон
        template = random.choice(TICKET_TEMPLATES)
        address = random.choice(template["addresses"])
        
        # Выбираем случайного клиента
        customer = random.choice(customers)
        
        # Случайно назначаем исполнителя (70% вероятность)
        executor = random.choice(executors) if random.random() < 0.7 else None
        
        # Определяем статус в зависимости от наличия исполнителя
        if executor is None:
            status = TicketStatus.PENDING
            started_at = None
            completed_at = None
        else:
            # Случайно выбираем статус для назначенных заявок
            status_options = [TicketStatus.IN_PROGRESS, TicketStatus.DONE, TicketStatus.REJECTED]
            weights = [0.4, 0.5, 0.1]  # 40% в работе, 50% выполнено, 10% отклонено
            status = random.choices(status_options, weights=weights)[0]
            
            # Устанавливаем временные метки
            created_days_ago = random.randint(1, 30)
            created_at = datetime.utcnow() - timedelta(days=created_days_ago)
            started_at = created_at + timedelta(hours=random.randint(1, 24))
            
            if status == TicketStatus.DONE:
                work_duration = random.randint(1, 72)  # 1-72 часа на выполнение
                completed_at = started_at + timedelta(hours=work_duration)
            else:
                completed_at = None
        
        # Генерируем дедлайн
        deadline_days = random.randint(3, 14)
        if status == TicketStatus.DONE and completed_at:
            # Для выполненных заявок дедлайн после создания, но может быть до или после завершения
            deadline = created_at + timedelta(days=deadline_days)
        else:
            deadline = datetime.utcnow() + timedelta(days=deadline_days)
        
        # Приоритет (больше высокоприоритетных заявок)
        priority = random.choices([1, 2, 3, 4, 5], weights=[0.1, 0.2, 0.4, 0.2, 0.1])[0]
        
        # Комментарии для завершенных/отклоненных заявок
        completion_comment = None
        rejection_reason = None
        
        if status == TicketStatus.DONE:
            completion_comments = [
                "Работы выполнены в полном объеме, заказчик доволен",
                "Все работы завершены согласно техническому заданию",
                "Ремонт выполнен качественно, гарантия 6 месяцев",
                "Работы завершены досрочно, заказчик принял работу",
                "Все работы выполнены согласно договору"
            ]
            completion_comment = random.choice(completion_comments)
        elif status == TicketStatus.REJECTED:
            rejection_reasons = [
                "Заказчик отменил заявку",
                "Невозможно выполнить работы по техническим причинам", 
                "Заказчик не предоставил доступ к объекту",
                "Работы отменены по инициативе заказчика"
            ]
            rejection_reason = random.choice(rejection_reasons)
        
        # Создаем заявку
        ticket = Ticket(
            title=template["title"],
            address=address,
            description=template["description"],
            deadline=deadline,
            priority=priority,
            customer_id=customer.id,
            executor_id=executor.id if executor else None,
            status=status,
            created_at=created_at if 'created_at' in locals() else datetime.utcnow(),
            started_at=started_at,
            completed_at=completed_at,
            completion_comment=completion_comment,
            rejection_reason=rejection_reason
        )
        
        session.add(ticket)
        tickets.append(ticket)
    
    await session.commit()
    
    # Обновляем объекты
    for ticket in tickets:
        await session.refresh(ticket)
    
    # Статистика созданных заявок
    status_counts = {}
    for status in TicketStatus:
        count = len([t for t in tickets if t.status == status])
        status_counts[status.value] = count
    
    print(f"✅ Создано {len(tickets)} заявок:")
    for status, count in status_counts.items():
        print(f"   • {status}: {count}")
    
    return tickets


async def create_sample_data():
    """Основная функция создания тестовых данных"""
    print("🌱 Начало заполнения базы данных тестовыми данными...")
    
    # Инициализируем БД
    await init_db()
    
    async with async_session_maker() as session:
        # Проверяем, не заполнена ли уже база
        from sqlmodel import select
        existing_users = await session.exec(select(User))
        if existing_users.first():
            print("⚠️ База данных уже содержит пользователей. Пропускаем заполнение.")
            return
        
        # Создаем пользователей
        users = await create_users(session)
        
        # Создаем заявки
        tickets = await create_tickets(session, users)
        
        print(f"""
🎉 Заполнение базы данных завершено!

📊 Создано:
   • Пользователей: {len(users)}
   • Заявок: {len(tickets)}

🔑 Тестовые учетные данные:
   
   👤 Администраторы:
   • admin1@company.com / admin123
   • admin2@company.com / admin123  
   • admin3@company.com / admin123
   
   🔧 Исполнители:
   • executor1@company.com / exec123
   • executor2@company.com / exec123
   • executor3@company.com / exec123
   • executor4@company.com / exec123
   • executor5@company.com / exec123
   
   👥 Клиенты:
   • customer1@gmail.com / customer123
   • customer2@gmail.com / customer123
   • ... (всего 10 клиентов)

🚀 Приложение готово к тестированию!
        """)


# ===== ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ =====

async def clear_database():
    """Очищает базу данных (для разработки)"""
    print("🗑️ Очистка базы данных...")
    
    async with async_session_maker() as session:
        # Удаляем все заявки
        tickets_result = await session.exec(select(Ticket))
        tickets = tickets_result.all()
        for ticket in tickets:
            await session.delete(ticket)
        
        # Удаляем всех пользователей
        users_result = await session.exec(select(User))
        users = users_result.all()
        for user in users:
            await session.delete(user)
        
        await session.commit()
        print(f"✅ Удалено {len(tickets)} заявок и {len(users)} пользователей")


async def reset_database():
    """Полный сброс и пересоздание данных"""
    await clear_database()
    await create_sample_data()


# ===== ЗАПУСК =====

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "clear":
            asyncio.run(clear_database())
        elif command == "reset":
            asyncio.run(reset_database())
        else:
            print("Доступные команды: clear, reset")
    else:
        asyncio.run(create_sample_data())