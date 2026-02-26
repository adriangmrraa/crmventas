import os

sql_query = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'credentials') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'credentials' AND column_name = 'created_at') THEN
            ALTER TABLE credentials ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'credentials' AND column_name = 'updated_at') THEN
            ALTER TABLE credentials ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
        END IF;
    END IF;
END $$;
"""

print(sql_query)
