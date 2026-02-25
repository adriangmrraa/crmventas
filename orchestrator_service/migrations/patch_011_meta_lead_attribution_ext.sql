-- Migration Patch 011: Add extra Meta attribution columns to leads
-- This allows storing full attribution data from Lead Forms and Click-to-WhatsApp.

BEGIN;

DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='meta_adset_id') THEN
        ALTER TABLE leads ADD COLUMN meta_adset_id VARCHAR(255);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='meta_campaign_name') THEN
        ALTER TABLE leads ADD COLUMN meta_campaign_name TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='meta_adset_name') THEN
        ALTER TABLE leads ADD COLUMN meta_adset_name TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='meta_ad_name') THEN
        ALTER TABLE leads ADD COLUMN meta_ad_name TEXT;
    END IF;
END $$;

COMMIT;
