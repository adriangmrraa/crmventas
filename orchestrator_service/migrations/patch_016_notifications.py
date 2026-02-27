"""
Patch 016: Sistema de Notificaciones
Tabla para almacenar notificaciones de vendedores y CEO
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def apply(db):
    """Aplicar migración"""
    logger.info("Applying Patch 016: Notifications system")
    
    # Crear tabla de notificaciones
    await db.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id VARCHAR(255) PRIMARY KEY,
            type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            priority VARCHAR(20) NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'critical')),
            recipient_id VARCHAR(255) NOT NULL,
            sender_id VARCHAR(255),
            related_entity_type VARCHAR(50),
            related_entity_id VARCHAR(255),
            metadata JSONB,
            read BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE,
            
            -- Índices para búsquedas frecuentes
            INDEX idx_notifications_recipient (recipient_id),
            INDEX idx_notifications_recipient_read (recipient_id, read),
            INDEX idx_notifications_created (created_at DESC),
            INDEX idx_notifications_expires (expires_at),
            INDEX idx_notifications_type (type),
            INDEX idx_notifications_priority (priority)
        )
    """)
    
    logger.info("✅ Created notifications table")
    
    # Agregar trigger para limpieza automática
    await db.execute("""
        CREATE OR REPLACE FUNCTION cleanup_expired_notifications()
        RETURNS TRIGGER AS $$
        BEGIN
            DELETE FROM notifications 
            WHERE expires_at IS NOT NULL 
                AND expires_at < NOW();
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    await db.execute("""
        DROP TRIGGER IF EXISTS trigger_cleanup_notifications ON notifications;
        CREATE TRIGGER trigger_cleanup_notifications
        AFTER INSERT ON notifications
        EXECUTE FUNCTION cleanup_expired_notifications();
    """)
    
    logger.info("✅ Created cleanup trigger for expired notifications")
    
    # Crear tabla para configuración de notificaciones por usuario
    await db.execute("""
        CREATE TABLE IF NOT EXISTS notification_settings (
            user_id VARCHAR(255) PRIMARY KEY,
            email_notifications BOOLEAN DEFAULT true,
            push_notifications BOOLEAN DEFAULT true,
            desktop_notifications BOOLEAN DEFAULT true,
            mute_until TIMESTAMP WITH TIME ZONE,
            muted_types JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            
            INDEX idx_notification_settings_user (user_id)
        )
    """)
    
    logger.info("✅ Created notification_settings table")
    
    # Crear función para actualizar timestamp
    await db.execute("""
        CREATE OR REPLACE FUNCTION update_notification_settings_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    await db.execute("""
        DROP TRIGGER IF EXISTS trigger_update_notification_settings_timestamp ON notification_settings;
        CREATE TRIGGER trigger_update_notification_settings_timestamp
        BEFORE UPDATE ON notification_settings
        FOR EACH ROW
        EXECUTE FUNCTION update_notification_settings_timestamp();
    """)
    
    logger.info("✅ Created timestamp update trigger for notification_settings")
    
    # Insertar configuraciones por defecto para usuarios existentes
    await db.execute("""
        INSERT INTO notification_settings (user_id)
        SELECT id FROM users
        WHERE id NOT IN (SELECT user_id FROM notification_settings)
        ON CONFLICT (user_id) DO NOTHING
    """)
    
    logger.info("✅ Created default notification settings for existing users")
    
    # Crear vista para notificaciones no leídas
    await db.execute("""
        CREATE OR REPLACE VIEW unread_notifications_count AS
        SELECT 
            recipient_id as user_id,
            COUNT(*) as count,
            COUNT(CASE WHEN priority = 'critical' THEN 1 END) as critical_count,
            COUNT(CASE WHEN priority = 'high' THEN 1 END) as high_count,
            COUNT(CASE WHEN priority = 'medium' THEN 1 END) as medium_count,
            COUNT(CASE WHEN priority = 'low' THEN 1 END) as low_count
        FROM notifications
        WHERE read = false
            AND (expires_at IS NULL OR expires_at > NOW())
        GROUP BY recipient_id
    """)
    
    logger.info("✅ Created unread_notifications_count view")
    
    # Crear función para obtener notificaciones recientes
    await db.execute("""
        CREATE OR REPLACE FUNCTION get_recent_notifications(
            p_user_id VARCHAR(255),
            p_limit INTEGER DEFAULT 20,
            p_unread_only BOOLEAN DEFAULT false
        )
        RETURNS TABLE (
            id VARCHAR(255),
            type VARCHAR(50),
            title VARCHAR(255),
            message TEXT,
            priority VARCHAR(20),
            sender_id VARCHAR(255),
            related_entity_type VARCHAR(50),
            related_entity_id VARCHAR(255),
            metadata JSONB,
            read BOOLEAN,
            created_at TIMESTAMP WITH TIME ZONE,
            expires_at TIMESTAMP WITH TIME ZONE,
            sender_name VARCHAR(255),
            sender_email VARCHAR(255)
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT 
                n.id,
                n.type,
                n.title,
                n.message,
                n.priority,
                n.sender_id,
                n.related_entity_type,
                n.related_entity_id,
                n.metadata,
                n.read,
                n.created_at,
                n.expires_at,
                u.first_name || ' ' || u.last_name as sender_name,
                u.email as sender_email
            FROM notifications n
            LEFT JOIN users u ON n.sender_id = u.id
            WHERE n.recipient_id = p_user_id
                AND (NOT p_unread_only OR n.read = false)
                AND (n.expires_at IS NULL OR n.expires_at > NOW())
            ORDER BY 
                CASE n.priority
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                END,
                n.created_at DESC
            LIMIT p_limit;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    logger.info("✅ Created get_recent_notifications function")
    
    # Crear índices adicionales para performance
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_notifications_recipient_type 
        ON notifications(recipient_id, type, created_at DESC)
    """)
    
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_notifications_entity 
        ON notifications(related_entity_type, related_entity_id, created_at DESC)
    """)
    
    logger.info("✅ Created additional indexes for performance")
    
    # Registrar la migración
    await db.execute("""
        INSERT INTO migrations (patch_number, description, applied_at)
        VALUES (16, 'Sistema de notificaciones para vendedores y CEO', NOW())
        ON CONFLICT (patch_number) DO UPDATE SET
            description = EXCLUDED.description,
            applied_at = NOW()
    """)
    
    logger.info("🎉 Patch 016 applied successfully: Notifications system")

async def rollback(db):
    """Revertir migración"""
    logger.info("Rolling back Patch 016: Notifications system")
    
    # Eliminar vistas y funciones primero
    await db.execute("DROP VIEW IF EXISTS unread_notifications_count")
    await db.execute("DROP FUNCTION IF EXISTS get_recent_notifications")
    await db.execute("DROP FUNCTION IF EXISTS cleanup_expired_notifications")
    await db.execute("DROP FUNCTION IF EXISTS update_notification_settings_timestamp")
    
    # Eliminar triggers
    await db.execute("DROP TRIGGER IF EXISTS trigger_cleanup_notifications ON notifications")
    await db.execute("DROP TRIGGER IF EXISTS trigger_update_notification_settings_timestamp ON notification_settings")
    
    # Eliminar tablas
    await db.execute("DROP TABLE IF EXISTS notification_settings")
    await db.execute("DROP TABLE IF EXISTS notifications")
    
    # Eliminar registro de migración
    await db.execute("DELETE FROM migrations WHERE patch_number = 16")
    
    logger.info("✅ Patch 016 rolled back successfully")