#!/bin/bash

# Скрипт для создания архива проекта

echo "🚀 Создание архива проекта..."

# Создаем временную директорию
temp_dir="repair-management-system-$(date +%Y%m%d)"
mkdir -p $temp_dir

# Копируем файлы проекта
echo "📁 Копирование файлов..."
cp -r backend $temp_dir/
cp -r frontend $temp_dir/
cp docker-compose.yml $temp_dir/
cp .env.example $temp_dir/
cp README.md $temp_dir/
cp README_LOCAL_SETUP.md $temp_dir/

# Очищаем ненужные файлы
echo "🧹 Очистка ненужных файлов..."
rm -rf $temp_dir/backend/venv
rm -rf $temp_dir/backend/__pycache__
rm -rf $temp_dir/backend/*/__pycache__
rm -rf $temp_dir/backend/.env
rm -rf $temp_dir/backend/*.db
rm -rf $temp_dir/backend/media/*
rm -rf $temp_dir/frontend/node_modules
rm -rf $temp_dir/frontend/dist

# Создаем архив
echo "📦 Создание архива..."
tar -czf ${temp_dir}.tar.gz $temp_dir

# Удаляем временную директорию
rm -rf $temp_dir

echo "✅ Архив создан: ${temp_dir}.tar.gz"
echo "📄 Размер архива: $(du -h ${temp_dir}.tar.gz | cut -f1)"
echo ""
echo "🎯 Для использования:"
echo "1. Скачайте архив ${temp_dir}.tar.gz"
echo "2. Распакуйте: tar -xzf ${temp_dir}.tar.gz"
echo "3. Следуйте инструкциям в README_LOCAL_SETUP.md"