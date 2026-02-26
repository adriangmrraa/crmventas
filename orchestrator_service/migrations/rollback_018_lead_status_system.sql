BEGIN;

-- 1. Eliminar foreign key constraint opcional (por si se agregó posteriormente)
ALTER TABLE leads DROP CONSTRAINT IF EXISTS fk_leads_status;

-- 2. Eliminar columnas agregadas
ALTER TABLE leads DROP COLUMN IF EXISTS status_changed_at;
ALTER TABLE leads DROP COLUMN IF EXISTS status_changed_by;
ALTER TABLE leads DROP COLUMN IF EXISTS days_in_current_status;
ALTER TABLE leads DROP COLUMN IF EXISTS status_metadata;

-- 3. Eliminar tablas nuevas
DROP TABLE IF EXISTS lead_status_trigger_logs CASCADE;
DROP TABLE IF EXISTS lead_status_triggers CASCADE;
DROP TABLE IF EXISTS lead_status_history CASCADE;
DROP TABLE IF EXISTS lead_status_transitions CASCADE;
DROP TABLE IF EXISTS lead_statuses CASCADE;

COMMIT;
