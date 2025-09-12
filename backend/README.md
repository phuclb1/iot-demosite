# IoT Telemetry Dashboard Backend

Python 3.12+ FastAPI backend for IoT device telemetry data ingestion and API services.

## Features

- **FastAPI**: Modern, fast web framework for building APIs with Python
- **Async/Await**: Full async support for high-performance I/O operations
- **PostgreSQL**: Metadata storage for organizations, sites, areas, and devices
- **InfluxDB**: Time-series database for telemetry data storage
- **MQTT**: Async MQTT client for real-time telemetry data ingestion
- **Real-time Streaming**: Server-Sent Events (SSE) for live dashboard updates
- **Authentication**: JWT-based authentication and authorization

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 15+
- InfluxDB 2.7+
- MQTT Broker (e.g., Mosquitto)

### Installation

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (copy `.env.example` to `.env` and configure):
```bash
cp .env.example .env
# Edit .env with your database and MQTT settings
```

4. Run database migrations:
```bash
# TODO: Add migration commands
```

5. Start the development server:
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

- **OpenAPI/Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Testing

Run tests with pytest:
```bash
pytest                     # Run all tests
pytest -v                  # Verbose output
pytest --cov=src          # With coverage report
pytest tests/unit/        # Run only unit tests
pytest tests/integration/ # Run only integration tests
```

## Development

### Code Quality

Format code with black and ruff:
```bash
black src/ tests/
ruff check src/ tests/
mypy src/
```

### Project Structure

```
backend/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── api/v1/              # API route handlers
│   ├── models/              # Pydantic models and database schemas
│   ├── services/            # Business logic services
│   ├── middleware/          # Custom middleware
│   ├── cli/                 # Command-line interfaces
│   ├── lib/                 # Reusable libraries
│   ├── migrations/          # Database migrations
│   └── scripts/             # Utility scripts
├── tests/
│   ├── contract/            # API contract tests
│   ├── integration/         # Integration tests
│   └── unit/                # Unit tests
├── requirements.txt         # Dependencies
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## Configuration

Environment variables (`.env` file):

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=iot_dashboard

# InfluxDB
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-token
INFLUXDB_ORG=iot-dashboard
INFLUXDB_BUCKET=telemetry

# MQTT
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=username
MQTT_PASSWORD=password

# Authentication
SECRET_KEY=your-secret-key-change-in-production
```

## MQTT Topic Structure

Telemetry data is expected on MQTT topics following this pattern:
```
iot/{org}/{site}/{area}/{device_id}/telemetry/v1
```

Payload format:
```json
{
  "timestamp": "2025-09-12T10:00:00Z",
  "vibration": 0.5,
  "temperature": 25.3,
  "power": 150.7,
  "electricity": 12.4
}
```