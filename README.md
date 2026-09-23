# Task Manager — Лабораторна робота №1 (Технології DevOps)

Проєкт для лабораторної роботи "Віртуалізація та контейнеризація". Реалізований
на Python (Flask + PyMongo), складається з **двох мікросервісів**, що
працюють з однією базою даних **MongoDB**:

- **`api`** (порт `5000`) — REST API для управління задачами (tasks):
  створення, перегляд, оновлення, видалення.
- **`stats`** (порт `5001`) — окремий сервіс, який читає ту саму базу і
  віддає агреговану статистику по задачах (кількість за статусами).

Такий поділ на дві незалежні частини зроблений навмисно — щоб задовольнити
вимогу "складається з декількох частин" і щоб було зручно продовжити роботу
над мікросервісною архітектурою у наступних лабораторних.

## Структура проєкту

```
taskmanager-devops/
├── docker-compose.yml
├── services/
│   ├── api/
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   ├── requirements-dev.txt
│   │   ├── Dockerfile
│   │   └── tests/
│   │       ├── test_unit.py         # юніт-тести (mongomock, без реальної БД)
│   │       └── test_integration.py  # інтеграційні тести (реальний MongoDB)
│   └── stats/
│       ├── app.py
│       ├── requirements.txt
│       ├── requirements-dev.txt
│       ├── Dockerfile
│       └── tests/
│           └── test_stats.py
└── README.md
```

## API `api` (порт 5000)

Повна інтерактивна документація Swagger UI доступна за адресою:
**http://localhost:5000/apidocs/**

Там можна розгорнути кожен ендпоінт, натиснути "Try it out", підставити
дані і одразу побачити реальну відповідь сервера — зручно для демонстрації
на захисті лабораторної.

| Метод  | Шлях              | Опис                                   |
|--------|-------------------|-----------------------------------------|
| GET    | `/health`         | Перевірка стану сервісу                 |
| POST   | `/tasks`          | Створити задачу (`title` обов'язковий)  |
| GET    | `/tasks`          | Список задач (опційно `?status=done`)   |
| GET    | `/tasks/<id>`     | Отримати одну задачу                    |
| PUT    | `/tasks/<id>`     | Оновити задачу (`title`/`description`/`status`) |
| DELETE | `/tasks/<id>`     | Видалити задачу                         |

Приклад:

```bash
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Зробити лабу 1", "status": "pending"}'
```

## API `stats` (порт 5001)

| Метод | Шлях      | Опис                                             |
|-------|-----------|---------------------------------------------------|
| GET   | `/health` | Перевірка стану сервісу                            |
| GET   | `/stats`  | Загальна кількість задач + розбивка за статусами   |

```bash
curl http://localhost:5001/stats
```

## Запуск через Docker Compose

Достатньо мати встановлений Docker і Docker Compose:

```bash
docker compose up --build
```

Це підніме чотири контейнери: `mongo`, `api`, `stats`, `mongo-express`,
об'єднані в одну мережу `taskmanager-net`. Дані MongoDB зберігаються у named
volume `mongo_data`, тож переживають перезапуск контейнерів.

### Перегляд даних у MongoDB (mongo-express)

Відкрий у браузері **http://localhost:8081** — це веб-адмінка для MongoDB.
Там зліва обираєш базу `taskmanager` → колекцію `tasks` і бачиш усі
документи (задачі), які реально лежать у базі. Можна дивитись, редагувати,
видаляти записи прямо в інтерфейсі — зручно показати на захисті.

Альтернатива без браузера — консоль mongosh прямо в контейнері:

```bash
docker compose exec mongo mongosh
```

а всередині:

```javascript
use taskmanager
db.tasks.find().pretty()
```

Зупинити все:

```bash
docker compose down
```

Зупинити і видалити дані бази:

```bash
docker compose down -v
```

## Тестування

### Юніт-тести (без бази даних, з `mongomock`)

Кожен сервіс тестується локально без піднятого MongoDB:

```bash
cd services/api
pip install -r requirements-dev.txt
pytest tests/test_unit.py -v

cd ../stats
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Інтеграційні тести (з реальним MongoDB)

Інтеграційні тести `services/api/tests/test_integration.py` автоматично
пропускаються (`skip`), якщо MongoDB недоступний за адресою `MONGO_URI`.
Щоб їх запустити:

```bash
docker run -d --rm -p 27017:27017 --name test-mongo mongo:7
cd services/api
MONGO_URI=mongodb://localhost:27017 pytest tests/test_integration.py -v
docker stop test-mongo
```

## Публікація в GitHub

```bash
git init
git add .
git commit -m "Lab 1: Dockerfile + docker-compose for taskmanager (api + stats + mongo)"
git branch -M main
git remote add origin <ваше-посилання-на-репозиторій>
git push -u origin main
```

## Відповідність вимогам лабораторної

1. **Проєкт** — веб-додаток (Flask + PyMongo), що взаємодіє з базою даних
   MongoDB.
2. **Dockerfile** — окремо для `services/api` та `services/stats`.
3. **docker-compose.yml** — піднімає обидва сервіси разом з MongoDB.
4. **Юніт та інтеграційні тести** — присутні в обох сервісах (`tests/`).
5. **Декілька частин (мікросервіси)** — `api` і `stats` — незалежні
   Flask-додатки, що діляться однією базою даних.
