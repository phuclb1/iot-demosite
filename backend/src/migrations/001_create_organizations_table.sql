-- Migration: Create organizations table
-- Description: Creates the organizations table for the top-level hierarchy
-- Created: 2025-09-17

BEGIN;

-- Create organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_organizations_created_at ON organizations(created_at);
CREATE INDEX IF NOT EXISTS idx_organizations_name ON organizations(name);

-- Add constraints
ALTER TABLE organizations ADD CONSTRAINT chk_organizations_slug_format
    CHECK (slug ~ '^[a-z0-9-]+$');

ALTER TABLE organizations ADD CONSTRAINT chk_organizations_name_not_empty
    CHECK (LENGTH(TRIM(name)) > 0);

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments
COMMENT ON TABLE organizations IS 'Top-level organizational entities in the IoT hierarchy';
COMMENT ON COLUMN organizations.id IS 'Unique identifier for the organization';
COMMENT ON COLUMN organizations.name IS 'Human-readable organization name';
COMMENT ON COLUMN organizations.slug IS 'URL-safe identifier for the organization';
COMMENT ON COLUMN organizations.description IS 'Optional description of the organization';
COMMENT ON COLUMN organizations.created_at IS 'Timestamp when the organization was created';
COMMENT ON COLUMN organizations.updated_at IS 'Timestamp when the organization was last updated';

COMMIT;