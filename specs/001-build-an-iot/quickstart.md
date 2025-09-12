# Quickstart: IoT Telemetry Dashboard

**Purpose**: Validate core user scenarios from the feature specification  
**Duration**: 5-10 minutes  
**Prerequisites**: Development environment running with test data

## Test Scenario: Operations Manager Dashboard Workflow

This quickstart validates the primary user story:
> "As an operations manager, I need to monitor real-time telemetry data from IoT devices across multiple organizational sites so that I can track device health, identify anomalies, and ensure optimal performance of our industrial equipment."

### Setup: Test Data Requirements

Before starting, ensure the following test data exists:

#### Organizations & Hierarchy
```
TestCorp (Organization)
  ├── Factory-North (Site)
  │   ├── Production-Floor (Area)
  │   │   ├── Device-001 (Temperature Sensor)
  │   │   └── Device-002 (Vibration Monitor)
  │   └── Maintenance-Bay (Area)
  │       └── Device-003 (Power Monitor)
  └── Warehouse-South (Site)
      └── Storage-Area (Area)
          └── Device-004 (Multi-sensor)
```

#### Active Telemetry Stream
- All devices sending data every 1 second
- Realistic sensor values within normal ranges
- At least 1 hour of historical data per device

### Step 1: Authentication & Access Control (2 minutes)

1. **Login as Operations Manager**
   ```
   Navigate to: http://localhost:3000/login
   Email: ops-manager@testcorp.com
   Password: [test-password]
   ```

2. **Verify Organization Access**
   - Dashboard should display "TestCorp" organization
   - User should see permission to access both Factory-North and Warehouse-South
   - Verify no access to other organizations (if test data includes them)

**Expected Result**: Successful login with appropriate organization scope

### Step 2: Real-time Dashboard Validation (3 minutes)

3. **View Real-time Charts**
   - Navigate to main dashboard
   - Verify 4 chart types displayed: Vibration, Temperature, Power, Electricity
   - Confirm charts update automatically (within 1-2 seconds)
   - Check that device status indicators show "online" for active devices

4. **Multi-device Data Streaming**
   - Verify data from all 4 test devices appearing in charts
   - Confirm each device's data stream is visually distinct
   - Check timestamps match current time (±5 seconds tolerance)

**Expected Result**: Live charts updating with current data from all devices

### Step 3: Hierarchical Filtering (2 minutes)

5. **Organization Filter**
   - Select "TestCorp" organization (should be default)
   - Verify all sites and devices visible

6. **Site Filter**
   - Filter to "Factory-North" site only
   - Confirm only devices 001, 002, 003 visible
   - Charts should update to show only selected site data

7. **Area Filter**
   - Within Factory-North, select "Production-Floor" area
   - Verify only devices 001 and 002 visible
   - Charts should show filtered data set

**Expected Result**: Filtering works at each level, data updates accordingly

### Step 4: Historical Data Analysis (3 minutes)

8. **Time Range Selection**
   - Switch from real-time view to historical view
   - Select time range: "Last 1 hour"
   - Verify charts display historical trend data

9. **Historical Data Validation**
   - Confirm data points span the full hour
   - Check that trend lines are reasonable (no major gaps)
   - Verify time axis labels are correct

10. **Different Time Ranges**
    - Test "Last 15 minutes" range
    - Test "Last 4 hours" range (if data available)
    - Confirm chart granularity adjusts appropriately

**Expected Result**: Historical charts display accurate time-series data

### Step 5: Device Status Monitoring (2 minutes)

11. **Online Device Status**
    - Verify all test devices show "online" status
    - Check last-seen timestamps are current

12. **Offline Device Simulation**
    - Stop telemetry for one device (Device-002)
    - Wait 35 seconds (offline threshold: 30 seconds)
    - Verify device status changes to "offline"
    - Confirm chart stops receiving new data for that device

**Expected Result**: Device status accurately reflects connectivity

### Acceptance Criteria Validation

After completing all steps, verify these acceptance scenarios from the spec:

✅ **Scenario 1**: Dashboard displays real-time charts for authorized devices  
✅ **Scenario 2**: Charts update in real-time as MQTT data arrives  
✅ **Scenario 3**: Hierarchical filtering works correctly  
✅ **Scenario 4**: Historical data displays for selected time ranges  
✅ **Scenario 5**: Device offline detection works within timeout threshold  

### Performance Validation

During testing, monitor these performance targets:

- **Chart Update Latency**: <200ms from data arrival to chart update
- **Filter Response Time**: <100ms for hierarchy filter changes
- **Historical Query Time**: <500ms for 1-hour data retrieval
- **Concurrent User Support**: Multiple browser tabs should work simultaneously

### Troubleshooting Common Issues

#### Charts Not Updating
- Check browser developer console for WebSocket/SSE errors
- Verify MQTT broker connection in server logs
- Confirm test devices are actually sending data

#### Missing Historical Data
- Verify InfluxDB contains test data for selected time range
- Check timezone settings match server configuration
- Confirm date/time picker values are valid

#### Permission Errors
- Verify user has correct organization_permissions in database
- Check API authentication tokens are not expired
- Confirm organization/site/area hierarchy is correctly configured

### Next Steps After Quickstart

Once quickstart validation passes:

1. **Load Testing**: Simulate hundreds of concurrent devices
2. **Stress Testing**: Test system with thousands of data points per second
3. **Integration Testing**: Full end-to-end MQTT → Database → Dashboard flow
4. **Browser Compatibility**: Test across Chrome, Firefox, Safari, Edge

### Success Criteria

This quickstart is **PASSED** when:
- All 12 test steps complete successfully
- All 5 acceptance scenarios validated
- Performance targets met during testing
- No errors in browser console or server logs

This quickstart is **FAILED** when:
- Any test step fails to produce expected result
- Performance targets exceeded by >50%
- Critical errors prevent core functionality

---

**Last Updated**: 2025-09-12  
**Test Environment**: Development with Docker Compose  
**Estimated Runtime**: 8 minutes average