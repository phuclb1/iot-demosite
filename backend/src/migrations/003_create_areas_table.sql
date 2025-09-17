-- Migration: Create areas table
-- Description: Creates the areas table for the third level of hierarchy
-- Created: 2025-09-17

BEGIN;

-- Create areas table
CREATE TABLE IF NOT EXISTS areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_areas_site_id ON areas(site_id);
CREATE INDEX IF NOT EXISTS idx_areas_site_slug ON areas(site_id, slug);
CREATE INDEX IF NOT EXISTS idx_areas_name ON areas(name);
CREATE INDEX IF NOT EXISTS idx_areas_created_at ON areas(created_at);

-- Add unique constraint for slug within site
ALTER TABLE areas ADD CONSTRAINT uk_areas_site_slug
    UNIQUE (site_id, slug);

-- Add constraints
ALTER TABLE areas ADD CONSTRAINT chk_areas_slug_format
    CHECK (slug ~ '^[a-z0-9-]+$');

ALTER TABLE areas ADD CONSTRAINT chk_areas_name_not_empty
    CHECK (LENGTH(TRIM(name)) > 0);

-- Create trigger for updated_at
CREATE TRIGGER trigger_areas_updated_at
    BEFORE UPDATE ON areas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments
COMMENT ON TABLE areas IS 'Functional areas within sites';
COMMENT ON COLUMN areas.id IS 'Unique identifier for the area';
COMMENT ON COLUMN areas.site_id IS 'Reference to the parent site';
COMMENT ON COLUMN areas.name IS 'Human-readable area name';
COMMENT ON COLUMN areas.slug IS 'URL-safe identifier for the area within the site';
COMMENT ON COLUMN areas.description IS 'Optional description of the area';
COMMENT ON COLUMN areas.created_at IS 'Timestamp when the area was created';
COMMENT ON COLUMN areas.updated_at IS 'Timestamp when the area was last updated';

COMMIT;