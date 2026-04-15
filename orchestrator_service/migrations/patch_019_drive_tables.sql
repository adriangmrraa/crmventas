-- Migration Patch 019: Drive / File Storage System (SPEC-01)
-- Creates tables for drive_folders and drive_files
-- All tables include tenant_id for multi-tenancy sovereignty
-- Idempotent: safe to run multiple times

-- ============================================
-- 1. DRIVE_FOLDERS (hierarchical folder tree)
-- ============================================
CREATE TABLE IF NOT EXISTS drive_folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    nombre VARCHAR(255) NOT NULL,
    parent_id UUID REFERENCES drive_folders(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_drive_folders_tenant ON drive_folders(tenant_id);
CREATE INDEX IF NOT EXISTS idx_drive_folders_client ON drive_folders(client_id);
CREATE INDEX IF NOT EXISTS idx_drive_folders_parent ON drive_folders(parent_id);

-- ============================================
-- 2. DRIVE_FILES (files linked to folders)
-- ============================================
CREATE TABLE IF NOT EXISTS drive_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    folder_id UUID NOT NULL REFERENCES drive_folders(id) ON DELETE CASCADE,
    nombre VARCHAR(255) NOT NULL,
    storage_path VARCHAR(1024) NOT NULL,
    mime_type VARCHAR(127) NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes > 0),
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_drive_files_tenant ON drive_files(tenant_id);
CREATE INDEX IF NOT EXISTS idx_drive_files_client ON drive_files(client_id);
CREATE INDEX IF NOT EXISTS idx_drive_files_folder ON drive_files(folder_id);
