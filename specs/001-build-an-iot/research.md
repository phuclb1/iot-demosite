# IoT Telemetry Dashboard Technology Research

**Date**: 2025-09-12  
**Project**: IoT Telemetry Dashboard  
**Requirements**: Handle thousands of devices, 1-second frequency updates, <200ms latency

## 1. Testing Framework Decision

### Decision: Vitest + Playwright

**Unit Testing**: Vitest  
**E2E Testing**: Playwright

### Rationale

**Vitest for Unit Testing:**
- **Performance**: 3-5x faster than Jest, with 10-20x improvement in watch mode
- **Modern JavaScript Support**: Native TypeScript, JSX, and ESM support out of the box
- **Zero Configuration**: Inherits settings from Vite, minimal setup required
- **Smart Watch Mode**: Only reruns affected tests using ES module graph analysis
- **Industry Momentum**: Became the preferred choice in 2025 for new Next.js TypeScript projects

**Playwright for E2E Testing:**
- **Cross-Browser Support**: Native support for Chromium, Firefox, and WebKit
- **Parallel Execution**: Built-in parallel test execution without paid plans
- **Real-time Dashboard Testing**: Advanced scenarios including multi-tab, network interception, and concurrent user simulation
- **Performance**: Overtook Cypress in npm downloads and GitHub stars by 2024-2025
- **Complex Workflows**: Better handling of role-based session isolation and cross-origin testing

### Alternatives Considered

- **Jest**: Rejected due to slower performance (15.5s vs 3.8s in benchmarks), complex TypeScript setup requirements, and less optimized watch mode
- **Cypress**: Rejected due to limited cross-browser support, same-origin policy limitations, and requirement for paid plans for parallel execution

---

## 2. MQTT Integration Decision

### Decision: MQTT.js with Next.js API Routes

**Library**: MQTT.js v5.0.0+  
**Architecture**: Server-side MQTT client in Next.js API routes with WebSocket forwarding to frontend

### Rationale

- **Mature Library**: MQTT.js is the most robust and popular MQTT client for JavaScript with TypeScript rewrite in v5.0.0
- **Server-Side Reliability**: Single persistent connection on server prevents client-side connection issues
- **Scalability**: One server connection efficiently shares data with multiple client sessions
- **Quality of Service**: Full QoS support with persistent sessions and message queuing
- **Performance**: Minimal bandwidth requirements with pub/sub architecture eliminating polling

### Implementation Pattern
```typescript
// API route: /api/mqtt-bridge
const client = mqtt.connect(brokerUrl, {
  clientId: 'iot-dashboard-server',
  keepalive: 60,
  reconnectPeriod: 1000
});

client.subscribe('iot/+/+/+/+/telemetry/v1');
// Forward to WebSocket connections
```

### Alternatives Considered

- **Paho JavaScript Client**: Rejected due to less active maintenance and fewer features
- **Direct Client-Side MQTT**: Rejected due to connection reliability issues and scalability concerns

---

## 3. VisActor Integration Decision

### Decision: VisActor VChart with React Integration

**Library**: @visactor/react-vchart  
**Update Strategy**: Throttled data updates with 200ms intervals

### Rationale

- **React Integration**: Official React wrapper with consistent API
- **Real-time Capability**: Supports dynamic data updates with configurable refresh rates
- **Performance**: Canvas-based rendering for high-frequency updates
- **Flexibility**: Complete spec-based configuration allows for complex telemetry visualizations

### Implementation Pattern
```typescript
const [chartData, setChartData] = useState();

useEffect(() => {
  const interval = setInterval(() => {
    // Throttle updates to meet 200ms requirement
    updateChartData();
  }, 200);
  return () => clearInterval(interval);
}, []);
```

### Performance Optimizations
- Implement windowing for large datasets
- Use throttling/debouncing for update frequency control
- Canvas rendering over SVG for better performance

### Alternatives Considered

- **Chart.js**: Rejected due to less optimized real-time performance
- **D3.js**: Rejected due to complexity and development time requirements
- **Recharts**: Rejected due to SVG-based rendering limiting high-frequency updates

---

## 4. InfluxDB Integration Decision

### Decision: InfluxDB 3.0 with Official Node.js Client

**Version**: InfluxDB 3.0 (Rust-based)  
**Client**: @influxdata/influxdb3-client  
**Architecture**: API routes for database queries with connection pooling

### Rationale

- **Performance**: 3-5x performance improvement with Rust rewrite in v3.0
- **Sub-10ms Queries**: Last Value Cache (LVC) enables <10ms response times for current values
- **Scalability**: Decoupled architecture allows independent scaling of compute and storage
- **SQL Compatibility**: Enhanced SQL support alongside InfluxQL for complex queries
- **Real-time Analytics**: Optimized for high-frequency data ingestion (1Hz per device)

### Implementation Pattern
```typescript
// API route: /api/telemetry/[deviceId]
const client = new InfluxDBClient({
  host: process.env.INFLUXDB_URL,
  database: 'telemetry'
});

// Sub-10ms last value queries
const query = `SELECT last(temperature), last(vibration) 
               FROM measurements 
               WHERE device_id = $1`;
```

### Alternatives Considered

- **TimescaleDB**: Rejected due to PostgreSQL overhead for pure time-series operations
- **InfluxDB 2.x**: Rejected in favor of v3.0's performance improvements

---

## 5. Real-time Updates Decision

### Decision: Server-Sent Events (SSE)

**Technology**: Server-Sent Events with EventSource API  
**Fallback**: WebSocket for bidirectional needs

### Rationale

- **Optimal for Dashboards**: SSE perfect for one-way server-to-client data streams
- **Low Latency**: Meets <200ms requirement with persistent HTTP connection
- **Auto-Reconnection**: Built-in automatic reconnection on connection failure
- **Simplicity**: Less complex than WebSockets for unidirectional updates
- **HTTP/2 Multiplexing**: Efficient connection reuse with modern HTTP protocols
- **Mobile Friendly**: Better handling of network interruptions

### Implementation Pattern
```typescript
// API route: /api/telemetry/stream
export default function handler(req, res) {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
  });
  
  // Stream telemetry data every 200ms
}

// Frontend
const eventSource = new EventSource('/api/telemetry/stream');
eventSource.onmessage = (event) => {
  updateDashboard(JSON.parse(event.data));
};
```

### Alternatives Considered

- **WebSockets**: Rejected due to unnecessary complexity for primarily one-way communication
- **Polling**: Rejected due to higher latency and server resource usage
- **Long Polling**: Rejected due to connection overhead and complexity

---

## 6. PostgreSQL + InfluxDB Dual Architecture Decision

### Decision: Microservices-Style Data Layer

**Pattern**: Domain-driven data separation with unified API layer  
**PostgreSQL**: Metadata, users, organization hierarchy  
**InfluxDB**: Time-series telemetry data

### Rationale

- **Optimal Data Models**: Relational model for hierarchical org data, time-series model for telemetry
- **Performance Isolation**: Heavy telemetry writes don't impact transactional operations
- **Independent Scaling**: Scale time-series storage separately from metadata operations  
- **Query Optimization**: Each database optimized for its specific query patterns
- **Data Integrity**: Referential integrity for metadata, high-throughput ingestion for telemetry

### Architecture Pattern
```typescript
// Data service layer
class TelemetryService {
  async getDeviceMetadata(deviceId: string) {
    // PostgreSQL query for device info
    return await postgresClient.query(
      'SELECT * FROM devices WHERE id = $1', [deviceId]
    );
  }
  
  async getLatestTelemetry(deviceId: string) {
    // InfluxDB query for current readings
    return await influxClient.query(
      `SELECT last(*) FROM telemetry WHERE device_id = '${deviceId}'`
    );
  }
}
```

### Data Distribution
- **PostgreSQL**: Organizations, sites, areas, devices, users, permissions, configuration
- **InfluxDB**: Telemetry readings, timestamps, device metrics, alerts, aggregations

### Alternatives Considered

- **Single PostgreSQL with TimescaleDB**: Rejected due to mixed workload performance impact
- **Single InfluxDB**: Rejected due to lack of strong consistency for metadata operations
- **Document Database + InfluxDB**: Rejected due to unnecessary complexity for structured metadata

---

## Implementation Recommendations

### Development Workflow
1. Start with Vitest unit tests for business logic
2. Use Playwright for E2E testing of real-time dashboard functionality
3. Implement SSE streaming with 200ms intervals
4. Set up dual database architecture with clear data boundaries
5. Use InfluxDB 3.0's LVC for sub-10ms current value queries

### Performance Targets
- Dashboard update latency: <200ms
- Last value queries: <10ms (InfluxDB LVC)
- Data ingestion: Support 1000+ devices at 1Hz
- Test execution: <5 seconds for full unit test suite

### Monitoring & Observability
- Structured JSON logging for both databases
- Real-time performance metrics via InfluxDB
- Error tracking with full context including device IDs and timestamps