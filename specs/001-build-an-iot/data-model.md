# Data Model: IoT Telemetry Dashboard

**Date**: 2025-09-12  
**Project**: IoT Telemetry Dashboard  
**Spec Reference**: [spec.md](./spec.md)

## Entity Definitions

### PostgreSQL Entities (Metadata & Hierarchy)

#### Organization
```typescript
interface Organization {
  id: string;           // Primary key, UUID
  name: string;         // Business name, max 255 chars
  slug: string;         // URL-friendly identifier, unique
  description?: string; // Optional description
  created_at: Date;     // Timestamp of creation
  updated_at: Date;     // Last modification timestamp
}
```

**Validation Rules:**
- `name`: Required, 1-255 characters, unique within system
- `slug`: Required, alphanumeric + hyphens only, globally unique
- Must have at least one Site to be considered active

#### Site
```typescript
interface Site {
  id: string;           // Primary key, UUID
  organization_id: string; // Foreign key to Organization
  name: string;         // Site name, max 255 chars
  slug: string;         // URL-friendly identifier
  location?: string;    // Physical address/location
  timezone: string;     // IANA timezone identifier
  created_at: Date;
  updated_at: Date;
}
```

**Validation Rules:**
- `name`: Required, 1-255 characters, unique within organization
- `slug`: Required, unique within organization
- `timezone`: Must be valid IANA timezone (e.g., 'America/New_York')
- Must belong to an active Organization

#### Area
```typescript
interface Area {
  id: string;           // Primary key, UUID
  site_id: string;      // Foreign key to Site
  name: string;         // Area name, max 255 chars
  slug: string;         // URL-friendly identifier
  description?: string; // Optional area description
  created_at: Date;
  updated_at: Date;
}
```

**Validation Rules:**
- `name`: Required, 1-255 characters, unique within site
- `slug`: Required, unique within site
- Must belong to an active Site

#### Device
```typescript
interface Device {
  id: string;           // Primary key, UUID (matches MQTT device_id)
  area_id: string;      // Foreign key to Area
  name: string;         // Human-readable device name
  model: string;        // Device model/type
  firmware_version?: string; // Optional firmware version
  mac_address?: string; // Optional MAC address for identification
  last_seen?: Date;     // Last time device sent telemetry
  status: 'online' | 'offline' | 'maintenance'; // Device status
  created_at: Date;
  updated_at: Date;
}
```

**Validation Rules:**
- `id`: Must be valid UUID matching MQTT topic device_id
- `name`: Required, 1-255 characters, unique within area
- `model`: Required, represents device type/capabilities
- `status`: Derived from recent telemetry activity (online if data within 5 seconds)

#### User
```typescript
interface User {
  id: string;           // Primary key, UUID
  email: string;        // Email address, unique
  name: string;         // Full name
  role: 'admin' | 'operator' | 'viewer'; // Permission level
  organization_permissions: string[]; // Array of organization IDs user can access
  created_at: Date;
  updated_at: Date;
}
```

**Validation Rules:**
- `email`: Required, valid email format, globally unique
- `name`: Required, 1-255 characters
- `role`: Determines base permissions across system
- User must have at least one organization permission

### InfluxDB Entities (Time-Series Data)

#### TelemetryReading
```typescript
interface TelemetryReading {
  // InfluxDB fields
  vibration: number;    // Vibration measurement (units: Hz or g-force)
  temperature: number;  // Temperature in Celsius
  power: number;        // Power consumption in Watts
  electricity: number;  // Electrical measurement (Amps, Voltage, etc.)
  
  // InfluxDB tags (indexed for fast queries)
  device_id: string;    // Matches Device.id from PostgreSQL
  org: string;          // Organization slug
  site: string;         // Site slug  
  area: string;         // Area slug
  
  // InfluxDB timestamp
  time: Date;           // Precision: nanoseconds
}
```

**Measurement Name**: `telemetry`

**Validation Rules:**
- All numeric fields must be finite numbers (not NaN, Infinity)
- `device_id`: Must correspond to existing Device in PostgreSQL
- `time`: Must be within reasonable range (not future dates beyond 5 minutes)
- Tag values must match existing hierarchy slugs

#### DeviceStatusSnapshot
```typescript
interface DeviceStatusSnapshot {
  // InfluxDB fields
  online: boolean;      // Device online status
  last_message_delay: number; // Seconds since last message
  message_count: number; // Total messages received this hour
  
  // InfluxDB tags
  device_id: string;
  org: string;
  site: string;
  area: string;
  
  time: Date;
}
```

**Measurement Name**: `device_status`

## Entity Relationships

### PostgreSQL Relationships
```
Organization (1) ─── (N) Site
Site (1) ─── (N) Area  
Area (1) ─── (N) Device
User (N) ─── (N) Organization [permissions]
```

### Cross-Database Relationships
- `Device.id` (PostgreSQL) ↔ `TelemetryReading.device_id` (InfluxDB)
- Hierarchy slugs in PostgreSQL match InfluxDB tags for fast filtering

## Data Validation Rules

### Business Rules
1. **Hierarchical Integrity**: Device must belong to Area → Site → Organization chain
2. **Telemetry Timestamps**: Must be within 5 minutes of current time (prevent stale data)
3. **Device Status**: Automatically set to 'offline' if no telemetry received for >30 seconds
4. **User Access**: Users can only view telemetry from organizations in their permissions array
5. **Data Retention**: Telemetry data older than 1 year automatically purged

### Performance Rules
1. **InfluxDB Tags**: Organization/site/area/device stored as tags for fast queries
2. **Index Strategy**: PostgreSQL indexes on foreign keys and slug fields
3. **Batch Inserts**: Telemetry writes batched for optimal InfluxDB performance
4. **Connection Pooling**: Database connections pooled to handle high-frequency writes

## State Transitions

### Device Status States
```
online ←→ offline ←→ maintenance
```

**Triggers:**
- `online`: Telemetry received within last 30 seconds
- `offline`: No telemetry for >30 seconds, no manual maintenance flag
- `maintenance`: Manual flag set by admin user

### Data Lifecycle
1. **Ingestion**: MQTT → API → Validation → InfluxDB batch write
2. **Real-time Access**: Dashboard queries last values via InfluxDB LVC
3. **Historical Analysis**: Time-range queries for trending charts
4. **Archival**: Data >1 year moved to cold storage or purged

## Schema Evolution Strategy

### Versioning Approach
- PostgreSQL: Standard migration files with rollback support
- InfluxDB: Additive schema changes only (new fields/measurements)
- API: Versioned endpoints to handle schema changes gracefully

### Breaking Change Handling
1. Run parallel schemas during transition period
2. Implement data migration scripts for existing telemetry
3. Version API responses to maintain backward compatibility