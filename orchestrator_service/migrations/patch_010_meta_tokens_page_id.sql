-- Migration Patch 010: Add page_id to meta_tokens
-- This enables mapping Lead Form webhooks (which contain page_id) to tenants.

BEGIN;

ALTER TABLE meta_tokens ADD COLUMN IF NOT EXISTS page_id VARCHAR(255);
CREATE INDEX IF NOT EXISTS idx_meta_tokens_page_id ON meta_tokens(page_id);

COMMIT;
