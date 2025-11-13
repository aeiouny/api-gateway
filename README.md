# Cloud-Native API Gateway

A lightweight, production-ready API Gateway built with FastAPI that demonstrates core API gateway capabilities including authentication, payment processing, rate limiting, and observability.

## Features

- **Authentication** - Auth0 JWT token validation with automatic key rotation
- **Payment Processing** - Stripe payment intent creation with secure API integration
- **Rate Limiting** - Redis-based request throttling to protect your APIs
- **Observability** - OpenTelemetry metrics exported in Prometheus format
- **Fast & Async** - Built on FastAPI for high-performance async operations

## Tech Stack

- **Framework:** FastAPI 0.121.1
- **Authentication:** Auth0 (JWT) + python-jose
- **Payments:** Stripe SDK
- **Rate Limiting:** FastAPI-Limiter + Redis
- **Observability:** OpenTelemetry + Prometheus
- **Runtime:** Uvicorn
- **Containerization:** Docker + Docker Compose

## 📁 Project Structure

```
api-gateway/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application & endpoints
│   ├── auth.py              # Auth0 JWT validation
│   ├── stripe_payments.py    # Stripe payment integration
│   └── telemetry.py          # OpenTelemetry setup & metrics
├── config/
│   └── k8.yaml              # Kubernetes configuration
├── docker-compose.yml        # Docker Compose setup
├── Dockerfile               # Container image definition
├── requirements.txt         # Python dependencies
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.13+ (or 3.9+)
- Docker & Docker Compose (optional, for containerized setup)
- Redis (for rate limiting)
- Auth0 account (for authentication)
- Stripe account (for payments)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/api-gateway.git
   cd api-gateway
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   # Auth0 Configuration
   AUTH0_DOMAIN=your-auth0-domain.auth0.com
   AUTH0_AUDIENCE=your-api-identifier
   
   # Stripe Configuration
   STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
   
   # Redis Configuration
   REDIS_URL=redis://localhost:6379
   
   # Optional
   SERVICE_VERSION=1.0.0
   ENVIRONMENT=development
   ```

5. **Start Redis** (if not using Docker)
   ```bash
   redis-server
   ```

6. **Run the application**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Docker Setup

1. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

   This will start:
   - Redis on port 6379
   - API Gateway on port 8000

2. **View logs**
   ```bash
   docker-compose logs -f api-gateway
   ```

3. **Stop services**
   ```bash
   docker-compose down
   ```

## API Endpoints

### Health & Monitoring

- `GET /` - Root endpoint (rate limited: 5 requests/minute)
- `GET /health` - Health check endpoint
- `GET /metrics` - Prometheus metrics (raw format)

### Authentication

- `GET /api/v1/me` - Get current user info (requires Auth0 JWT token)
  - **Headers:** `Authorization: Bearer <your-jwt-token>`
  - **Response:**
    ```json
    {
      "user_id": "auth0|123456",
      "email": "user@example.com",
      "feature": "authentication"
    }
    ```

### Payments

- `POST /api/payments/create` - Create a Stripe payment intent (requires Auth0 JWT token, rate limited: 20 requests/minute)
  - **Headers:** `Authorization: Bearer <your-jwt-token>`
  - **Body:**
    ```json
    {
      "amount": 2000,
      "currency": "usd",
      "description": "Payment for order #123"
    }
    ```
  - **Response:**
    ```json
    {
      "payment_id": "pi_1234567890",
      "client_secret": "pi_1234567890_secret_abc",
      "amount": 2000,
      "status": "requires_payment_method",
      "feature": "stripe_payments"
    }
    ```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AUTH0_DOMAIN` | Your Auth0 domain (e.g., `your-app.auth0.com`) | Yes |
| `AUTH0_AUDIENCE` | Your Auth0 API identifier | Yes |
| `STRIPE_SECRET_KEY` | Your Stripe secret key (starts with `sk_`) | Yes |
| `REDIS_URL` | Redis connection URL | Yes |
| `SERVICE_VERSION` | Service version for telemetry | No |
| `ENVIRONMENT` | Deployment environment | No |

## Observability

The API Gateway automatically collects metrics using OpenTelemetry:

- **HTTP Request Metrics:** Duration, count, status codes
- **System Metrics:** Memory usage, CPU usage
- **Active Requests:** Current request count

Metrics are exposed at `/metrics` in Prometheus format and can be scraped by Prometheus or other monitoring tools.

## Testing

Example request with curl:

```bash
# Get user info (requires valid Auth0 token)
curl -X GET http://localhost:8000/api/v1/me \
  -H "Authorization: Bearer YOUR_AUTH0_JWT_TOKEN"

# Create payment intent (requires valid Auth0 token)
curl -X POST http://localhost:8000/api/payments/create \
  -H "Authorization: Bearer YOUR_AUTH0_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 2000,
    "currency": "usd",
    "description": "Test payment"
  }'
```

## License

This project is open source and available under the MIT License.
