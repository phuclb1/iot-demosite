# iot-demosite Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-09-12

## Active Technologies
- Backend: Python 3.12, FastAPI, asyncpg, asyncio-mqtt, pytest
- Frontend: TypeScript with Next.js (React framework)
- VisActor (visualization), Tailwind CSS, Shadcn UI components, Jotai (state management)
- Frontend Testing: Vitest (unit tests), Playwright (E2E tests)
- Backend Testing: pytest, pytest-asyncio
- PostgreSQL (device metadata/organization hierarchy), InfluxDB (telemetry time-series data)
- Web application (browser-based dashboard) (001-build-an-iot)

## Project Structure
```
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/
```

## Commands
# Backend Testing commands (Python)
pytest                 # Run Python backend tests
pytest --watch         # Run tests in watch mode
pytest -v              # Run tests with verbose output

# Frontend Testing commands (Node.js)
npm run test           # Run Vitest unit tests
npm run test:e2e       # Run Playwright E2E tests
npm run test:watch     # Vitest watch mode

# Development commands  
# Backend (Python)
uvicorn src.main:app --reload  # Start FastAPI development server
python -m src.main             # Alternative startup

# Frontend (Node.js)
npm run dev           # Start Next.js development server
npm run build         # Build for production
npm run start         # Start production server

## Code Style
- Python: Follow PEP 8, use type hints, async/await for I/O
- FastAPI: Use pydantic models, dependency injection
- TypeScript: Follow strict mode conventions
- React: Functional components with hooks
- Testing: TDD approach - tests before implementation
- Database: PostgreSQL for metadata, InfluxDB for time-series data
- Real-time: FastAPI SSE for dashboard updates

## Recent Changes
- 001-build-an-iot: Updated to Python 3.12 + FastAPI backend, TypeScript + Next.js frontend, VisActor + InfluxDB stack for IoT telemetry dashboard

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->