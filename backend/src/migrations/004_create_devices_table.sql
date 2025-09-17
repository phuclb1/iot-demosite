-- Migration: Create devices table
-- Description: Creates the devices table for the fourth level of hierarchy
-- Created: 2025-09-17

BEGIN;

-- Create device status enum
CREATE TYPE device_status AS ENUM ('online', 'offline', 'maintenance');

-- Create devices table
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    area_id UUID NOT NULL REFERENCES areas(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    firmware_version VARCHAR(100),
    mac_address VARCHAR(17),
    last_seen TIMESTAMP WITH TIME ZONE,
    status device_status NOT NULL DEFAULT 'offline',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_devices_area_id ON devices(area_id);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);
CREATE INDEX IF NOT EXISTS idx_devices_mac_address ON devices(mac_address);
CREATE INDEX IF NOT EXISTS idx_devices_name ON devices(name);
CREATE INDEX IF NOT EXISTS idx_devices_model ON devices(model);
CREATE INDEX IF NOT EXISTS idx_devices_created_at ON devices(created_at);

-- Add constraints
ALTER TABLE devices ADD CONSTRAINT chk_devices_name_not_empty
    CHECK (LENGTH(TRIM(name)) > 0);

ALTER TABLE devices ADD CONSTRAINT chk_devices_model_not_empty
    CHECK (LENGTH(TRIM(model)) > 0);

-- MAC address format validation (XX:XX:XX:XX:XX:XX)
ALTER TABLE devices ADD CONSTRAINT chk_devices_mac_address_format
    CHECK (mac_address IS NULL OR mac_address ~ '^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$');

-- Ensure last_seen is not in the future (allow 1 hour tolerance for clock skew)
ALTER TABLE devices ADD CONSTRAINT chk_devices_last_seen_not_future
    CHECK (last_seen IS NULL OR last_seen <= NOW() + INTERVAL '1 hour');

-- Create unique constraint for MAC address (if provided)
CREATE UNIQUE INDEX IF NOT EXISTS uk_devices_mac_address
    ON devices(mac_address) WHERE mac_address IS NOT NULL;

-- Create trigger for updated_at
CREATE TRIGGER trigger_devices_updated_at
    BEFORE UPDATE ON devices
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to automatically update last_seen when status changes to online
CREATE OR REPLACE FUNCTION update_device_last_seen()
RETURNS TRIGGER AS $$
BEGIN
    -- If status is changing to online and last_seen is not explicitly set, update it
    IF NEW.status = 'online' AND (OLD.status != 'online' OR OLD.last_seen IS NULL) THEN
        IF NEW.last_seen = OLD.last_seen OR NEW.last_seen IS NULL THEN
            NEW.last_seen = NOW();
        END IF;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_devices_last_seen
    BEFORE UPDATE ON devices
    FOR EACH ROW
    EXECUTE FUNCTION update_device_last_seen();

-- Add comments
COMMENT ON TABLE devices IS 'IoT devices that collect telemetry data';
COMMENT ON COLUMN devices.id IS 'Unique identifier for the device';
COMMENT ON COLUMN devices.area_id IS 'Reference to the parent area';
COMMENT ON COLUMN devices.name IS 'Human-readable device name or identifier';
COMMENT ON COLUMN devices.model IS 'Device model or type';
COMMENT ON COLUMN devices.firmware_version IS 'Current firmware version installed on the device';
COMMENT ON COLUMN devices.mac_address IS 'Device MAC address in XX:XX:XX:XX:XX:XX format';
COMMENT ON COLUMN devices.last_seen IS 'Timestamp when the device was last seen online';
COMMENT ON COLUMN devices.status IS 'Current operational status of the device';
COMMENT ON COLUMN devices.created_at IS 'Timestamp when the device was created';
COMMENT ON COLUMN devices.updated_at IS 'Timestamp when the device was last updated';

COMMIT;