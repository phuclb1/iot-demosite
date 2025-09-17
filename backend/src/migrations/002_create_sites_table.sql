-- Migration: Create sites table
-- Description: Creates the sites table for the second level of hierarchy
-- Created: 2025-09-17

BEGIN;

-- Create sites table
CREATE TABLE IF NOT EXISTS sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_sites_organization_id ON sites(organization_id);
CREATE INDEX IF NOT EXISTS idx_sites_org_slug ON sites(organization_id, slug);
CREATE INDEX IF NOT EXISTS idx_sites_name ON sites(name);
CREATE INDEX IF NOT EXISTS idx_sites_created_at ON sites(created_at);

-- Add unique constraint for slug within organization
ALTER TABLE sites ADD CONSTRAINT uk_sites_organization_slug
    UNIQUE (organization_id, slug);

-- Add constraints
ALTER TABLE sites ADD CONSTRAINT chk_sites_slug_format
    CHECK (slug ~ '^[a-z0-9-]+$');

ALTER TABLE sites ADD CONSTRAINT chk_sites_name_not_empty
    CHECK (LENGTH(TRIM(name)) > 0);

ALTER TABLE sites ADD CONSTRAINT chk_sites_timezone_not_empty
    CHECK (LENGTH(TRIM(timezone)) > 0);

-- Create trigger for updated_at
CREATE TRIGGER trigger_sites_updated_at
    BEFORE UPDATE ON sites
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments
COMMENT ON TABLE sites IS 'Physical sites within organizations';
COMMENT ON COLUMN sites.id IS 'Unique identifier for the site';
COMMENT ON COLUMN sites.organization_id IS 'Reference to the parent organization';
COMMENT ON COLUMN sites.name IS 'Human-readable site name';
COMMENT ON COLUMN sites.slug IS 'URL-safe identifier for the site within the organization';
COMMENT ON COLUMN sites.location IS 'Physical location or address of the site';
COMMENT ON COLUMN sites.timezone IS 'IANA timezone name for the site';
COMMENT ON COLUMN sites.created_at IS 'Timestamp when the site was created';
COMMENT ON COLUMN sites.updated_at IS 'Timestamp when the site was last updated';

COMMIT;