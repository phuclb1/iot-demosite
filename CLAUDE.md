# iot-demosite Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-09-12

## Active Technologies
- TypeScript with Next.js (React framework)
- VisActor (visualization), Tailwind CSS, Shadcn UI components, Jotai (state management)
- Vitest (unit tests), Playwright (E2E tests)
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
# Testing commands
npm run test           # Run Vitest unit tests
npm run test:e2e       # Run Playwright E2E tests
npm run test:watch     # Vitest watch mode

# Development commands  
npm run dev           # Start development server
npm run build         # Build for production
npm run start         # Start production server

## Code Style
- TypeScript: Follow strict mode conventions
- React: Functional components with hooks
- Testing: TDD approach - tests before implementation
- Database: PostgreSQL for metadata, InfluxDB for time-series data
- Real-time: Server-sent events for dashboard updates

## Recent Changes
- 001-build-an-iot: Added TypeScript + Next.js + VisActor + InfluxDB stack for IoT telemetry dashboard

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->