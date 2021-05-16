# Auxy the bot project

Бот-помощник для повышения продуктивности.

## Подготовка окружения для разработки

```
virtualenv -p `which python3` venv
source venv/bin/activate
sudo -u postgres psql
  CREATE ROLE auxy_dev WITH LOGIN PASSWORD 'development';
  CREATE DATABASE auxy_db;
psql -h localhost -p 5432 auxy_db auxy_dev
python3 -m auxy.create_tables  # Потом перейдем на alembic
```


## Запуск для разработки

```
python3 -m auxy.main
```