# Gatum AI Support Agent (тестове завдання)

Прототип мультиканального AI-агента підтримки для [Gatum.io](https://gatum.io): обробка 7 обов'язкових сценаріїв, тікети в SQLite, аналітика, два канали (Telegram + HTTP webhook для Zendesk/Teams/WhatsApp).

## Швидкий старт

```bash
cd gatum-ai-agent
make install
cp .env.example .env   # додайте TELEGRAM_BOT_TOKEN та OPENAI_API_KEY за бажанням
make run
```

### Docker (рекомендовано для Telegram-бота)

Бот використовує **long polling** — з контейнера працює так само, як з локальної машини (потрібен лише інтернет і токен).

```bash
cp .env.example .env
# Вставте TELEGRAM_BOT_TOKEN у .env (див. розділ «Telegram-бот» нижче)
make docker-up          # збірка + запуск у фоні
make docker-logs        # перегляд логів (має бути "Telegram bot polling started")
make docker-down        # зупинка
```

Перевірка API з хоста: http://localhost:8000/health

```bash
curl http://localhost:8000/health
```

## Telegram-бот — створення токена

1. Відкрийте [@BotFather](https://t.me/BotFather) у Telegram.
2. Команда `/newbot`
3. **Ім'я (display name):** `Gatum Support Demo`
4. **Username (обов'язково закінчується на `bot`):** `gatum_support_demo_bot`  
   → повний адрес: `@gatum_support_demo_bot`  
   (якщо зайнято — спробуйте `gatum_ai_test_bot`, `yourname_gatum_bot`)
5. Скопіюйте токен у `.env`:
   ```
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...
   ```
6. Запустіть контейнер: `make docker-up`
7. Знайдіть бота в Telegram → `/start` → напишіть «як зробити розсилку?»

> Для демо всіх сценаріїв у робочий час: `AFTER_HOURS_CHECK_ENABLED=false` у `.env`, потім `docker compose up --build -d`.

Демо webhook-каналів (сервер має працювати):

```bash
chmod +x scripts/demo.sh
./scripts/demo.sh
```

Аналітика (CLI):

```bash
make analytics
# або
PYTHONPATH=src python -m gatum_agent.main analytics --format markdown
```

## Канали

| Канал | Як підключено |
|-------|----------------|
| **Telegram** | Long polling (`TELEGRAM_BOT_TOKEN`) |
| **Zendesk / Teams / WhatsApp** | `POST /channels/{channel}/messages` — реальний HTTP API, емуляція вхідних повідомлень (типовий webhook-патерн інтеграцій) |

Приклад:

```bash
curl -X POST http://localhost:8000/channels/zendesk/messages \
  -H "Content-Type: application/json" \
  -d '{"client_id":"user-42","message":"Як зробити розсилку?"}'
```

## API

| Endpoint | Опис |
|----------|------|
| `GET /health` | Статус |
| `POST /channels/{channel}/messages` | Вхідне повідомлення |
| `GET /tickets` | Список тікетів |
| `GET /tickets/{id}` | Один тікет |
| `GET /analytics?format=json\|text\|markdown` | Звіт |

## Сценарії (C-1 … C-7)

| ID | Тригер (приклад) | Поведінка | Ескалація |
|----|------------------|-----------|-----------|
| C-1 | «як зробити розсилку?» | FAQ з `knowledge/faq/` | — |
| C-2 | «поповнити баланс» | Інструкція + гаманець з `.env` | `finance` |
| C-3 | «SMS не доставлено +380…» | Збір phone/time/sender | `l2_support` |
| C-4 | Поза 09:00–18:00 (TZ з `.env`) | Автовідповідь + тікет | `morning_queue` |
| C-5 | «ціна», «знижка» | Без цін | `sales` |
| C-6 | «SMPP», «API error» | Збір деталей | `l2_support` (urgent) |
| C-7 | Невідомий intent | Без вигаданої відповіді | `support_queue` |
| C-8 (бонус) | Скарга / негатив | `sentiment=negative`, HIGH | `support_lead` + webhook |

Для демо всіх сценаріів у робочий час: `AFTER_HOURS_CHECK_ENABLED=false` у `.env`.

## ADR — архітектурні рішення

### 1. Гібридна класифікація намірів

**Рішення:** regex/keywords спочатку, опційно LLM (OpenAI) для невизначених випадків.

**Чому:** прототип має працювати без API-ключа на review; LLM покращує C-7 без жорсткого списку фраз.

### 2. SQLite для тікетів

**Рішення:** один файл `data/tickets.db`, без зовнішніх сервісів.

**Чому:** мінімальний setup для перевіряючого, достатньо для демо та аналітики.

### 3. Markdown FAQ замість векторної БД

**Рішення:** keyword search по файлах у `knowledge/faq/`.

**Чому:** RAG можна додати пізніше; для C-1 достатньо передбачуваних відповідей без embeddings.

### 4. Другий канал через REST webhook

**Рішення:** уніфікований endpoint замість окремих SDK Zendesk/Teams.

**Чому:** реальний патерн інтеграції; не потребує sandbox Microsoft/Zendesk для демо. Telegram — повноцінний другий канал з Bot API.

### 5. After-hours як middleware

**Рішення:** перевірка часу в `SupportAgent` до обробки сценарію.

**Чому:** прямо відповідає C-4; вимкнення через env для запису відео.

## Структура проєкту

```
gatum-ai-agent/
├── knowledge/faq/          # База знань (C-1)
├── src/gatum_agent/
│   ├── agent/              # Класифікатор, handlers, orchestrator
│   ├── channels/           # Telegram
│   ├── storage/            # SQLite
│   ├── analytics/          # Звіти
│   ├── api.py              # FastAPI
│   └── main.py             # Entrypoint
├── scripts/demo.sh
├── docker-compose.yml
└── Makefile
```

## Змінні середовища

Див. `.env.example`. Усі секрети — лише через environment variables.

## Демо-відео (чеклист)

1. `make run` або `docker compose up`
2. Telegram: 2–3 сценарії в чаті
3. `scripts/demo.sh` — zendesk/whatsapp/teams
4. `GET /tickets` — показати поля тікету
5. `make analytics` або `/analytics`

## Ліцензія

Код для тестового завдання Gatum — не публікуйте завдання відкрито.
