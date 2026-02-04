1. Перенос файлов
Перенесите файлы проекта на сервер в удобную директорию.

2. Установка ПО
curl -fsSL https://get.docker.com | sudo sh

3. Настройка
Переместите файл .env.example в -> .env рядом с docker-compose.yml и заполните его:

4. Запуск
docker compose up -d --build
