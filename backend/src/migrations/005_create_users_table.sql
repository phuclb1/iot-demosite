-- Migration: Create users table
-- Description: Creates the users table for authentication and authorization
-- Created: 2025-09-17

BEGIN;

-- Create user role enum
CREATE TYPE user_role AS ENUM ('admin', 'operator', 'viewer');

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'viewer',
    organization_permissions UUID[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_organization_permissions ON users USING GIN(organization_permissions);

-- Add constraints
ALTER TABLE users ADD CONSTRAINT chk_users_email_format
    CHECK (email ~ '^[^@]+@[^@]+\.[^@]+$');

ALTER TABLE users ADD CONSTRAINT chk_users_name_not_empty
    CHECK (LENGTH(TRIM(name)) > 0);

ALTER TABLE users ADD CONSTRAINT chk_users_password_hash_not_empty
    CHECK (LENGTH(TRIM(password_hash)) > 0);

-- Ensure organization_permissions contains valid UUIDs
CREATE OR REPLACE FUNCTION validate_uuid_array(uuids UUID[])
RETURNS BOOLEAN AS $$
DECLARE
    uuid_val UUID;
BEGIN
    IF uuids IS NULL THEN
        RETURN TRUE;
    END IF;

    FOREACH uuid_val IN ARRAY uuids
    LOOP
        -- This will raise an exception if uuid_val is not a valid UUID
        -- The UUID type in PostgreSQL automatically validates format
        CONTINUE;
    END LOOP;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

ALTER TABLE users ADD CONSTRAINT chk_users_organization_permissions_valid
    CHECK (validate_uuid_array(organization_permissions));

-- Create trigger for updated_at
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to validate organization permissions reference existing organizations
CREATE OR REPLACE FUNCTION validate_organization_permissions()
RETURNS TRIGGER AS $$
DECLARE
    org_id UUID;
BEGIN
    -- Check that all organization IDs in permissions array exist
    IF NEW.organization_permissions IS NOT NULL THEN
        FOREACH org_id IN ARRAY NEW.organization_permissions
        LOOP
            IF NOT EXISTS (SELECT 1 FROM organizations WHERE id = org_id) THEN
                RAISE EXCEPTION 'Organization with ID % does not exist', org_id;
            END IF;
        END LOOP;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_users_validate_org_permissions
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION validate_organization_permissions();

-- Create function to remove organization from users when organization is deleted
CREATE OR REPLACE FUNCTION cleanup_user_organization_permissions()
RETURNS TRIGGER AS $$
BEGIN
    -- Remove the deleted organization ID from all users' permissions
    UPDATE users
    SET organization_permissions = array_remove(organization_permissions, OLD.id)
    WHERE OLD.id = ANY(organization_permissions);

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_cleanup_org_permissions_on_org_delete
    AFTER DELETE ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_user_organization_permissions();

-- Add comments
COMMENT ON TABLE users IS 'Application users with authentication and authorization data';
COMMENT ON COLUMN users.id IS 'Unique identifier for the user';
COMMENT ON COLUMN users.email IS 'User email address (used for login)';
COMMENT ON COLUMN users.name IS 'User full name';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hash of the user password';
COMMENT ON COLUMN users.role IS 'User role determining system-wide permissions';
COMMENT ON COLUMN users.organization_permissions IS 'Array of organization IDs the user has access to';
COMMENT ON COLUMN users.created_at IS 'Timestamp when the user was created';
COMMENT ON COLUMN users.updated_at IS 'Timestamp when the user was last updated';

COMMIT;