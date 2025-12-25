# WhatsApp Food Ordering Backend

A production-ready conversational commerce backend for WhatsApp-based food ordering using Django, Meta WhatsApp Business API, and Paystack.

## Features

- **Conversational Ordering**: Full menu browsing, cart management, and checkout via WhatsApp text messages
- **Finite State Machine**: Predictable, debuggable conversation flow
- **Payment Integration**: Paystack payment links with webhook confirmation
- **Production-Ready**: Proper security, logging, and async-ready architecture

## Tech Stack

- Python 3.11+
- Django 4.2+ with Django REST Framework
- PostgreSQL (SQLite for development)
- Meta WhatsApp Business Cloud API
- Paystack Payment Gateway
- Celery + Redis (optional, for async processing)

## Quick Start

### 1. Clone and Setup Environment

```bash
cd whatsapp_orders
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
copy .env.example .env
# Edit .env with your actual credentials
```

### 3. Initialize Database

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_menu  # Load sample menu data
```

### 4. Run Development Server

```bash
python manage.py runserver
```

### 5. Expose Webhooks (for testing with WhatsApp)

```bash
ngrok http 8000
# Configure the ngrok URL in Meta Developer Console
```

## Project Structure

```
whatsapp_orders/
├── config/                 # Django project settings
│   ├── settings/          # Environment-specific settings
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── users/             # WhatsApp user profiles
│   ├── catalog/           # Menu categories and items
│   ├── orders/            # Orders and cart logic
│   ├── conversations/     # FSM conversation engine
│   ├── webhooks/          # WhatsApp & Paystack webhooks
│   └── messaging/         # WhatsApp API client
└── utils/                 # Shared utilities
```

## Webhook Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /webhooks/whatsapp/` | Meta webhook verification |
| `POST /webhooks/whatsapp/` | Incoming WhatsApp messages |
| `POST /webhooks/paystack/` | Payment confirmations |

## Environment Variables

See `.env.example` for all required configuration.

## Conversation Flow

1. User sends message → Bot shows menu categories
2. User selects category → Bot shows items
3. User selects item → Item added to cart
4. User types "cart" → Bot shows cart summary
5. User proceeds to checkout → Bot collects address
6. User confirms → Bot sends Paystack payment link
7. Payment confirmed → Bot sends order confirmation

## License

MIT
