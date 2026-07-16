# Payment Processing Service
## Запуск
Укажите переменные окружения из `.env.example`

Запустите проект командой:
```bash
docker compose up --build
```
## API
### POST /api/v1/payments

Заголовки:
- `X-API-Key: <api_key>` (обязательный)
- `Idempotency-Key: <unique_uuid>` (обязательный)

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: supersecretkey" \
  -H "Idempotency-Key: order-123" \
  -d '{"amount": "100.50", "currency": "RUB", "webhook_url": "https://webhook.site/xxx"}'
```

Ответ `202 Accepted`:
```json
{"payment_id": "...", "status": "pending", "created_at": "..."}
```

### GET /api/v1/payments/{payment_id}

```bash
curl http://localhost:8000/api/v1/payments/<id> -H "X-API-Key: supersecretkey"
```
