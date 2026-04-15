-- Migration Patch 020: Plantillas de Mensajes (SPEC-02)
-- Reusable message templates with dynamic variables
-- Idempotent: safe to run multiple times

CREATE TABLE IF NOT EXISTS plantillas (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre      TEXT NOT NULL,
    categoria   TEXT NOT NULL DEFAULT 'whatsapp'
                    CHECK (categoria IN ('whatsapp', 'email', 'seguimiento', 'prospeccion', 'cierre')),
    contenido   TEXT NOT NULL CHECK (char_length(contenido) <= 4000),
    variables   TEXT[] NOT NULL DEFAULT '{}',
    uso_count   INTEGER NOT NULL DEFAULT 0,
    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plantillas_tenant_id ON plantillas(tenant_id);
CREATE INDEX IF NOT EXISTS idx_plantillas_tenant_categoria ON plantillas(tenant_id, categoria);
CREATE INDEX IF NOT EXISTS idx_plantillas_tenant_uso ON plantillas(tenant_id, uso_count DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_plantillas_tenant_nombre ON plantillas(tenant_id, nombre);
