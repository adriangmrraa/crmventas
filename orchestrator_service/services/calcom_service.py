import logging
from typing import Optional, Dict
from db import db
import datetime

logger = logging.getLogger(__name__)

class CalcomService:
    async def handle_webhook(self, tenant_id: int, payload: dict):
        """
        Handles Cal.com webhook events.
        Supported events: BOOKING_CREATED, BOOKING_RESCHEDULED, BOOKING_CANCELLED
        """
        event_type = payload.get("triggerEvent")
        content = payload.get("payload", {})
        
        booking_id = str(content.get("id"))
        title = content.get("title", "Cita Cal.com")
        start_str = content.get("startTime")
        end_str = content.get("endTime")
        
        # Parse Dates
        try:
            start_dt = datetime.datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_dt = datetime.datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        except:
            start_dt = datetime.datetime.utcnow()
            end_dt = start_dt + datetime.timedelta(minutes=30)

        # Identify Lead
        attendees = content.get("attendees", [])
        lead_email = attendees[0].get("email") if attendees else None
        lead_phone = attendees[0].get("phoneNumber") if attendees else None

        lead_id = None
        if lead_phone:
            lead_row = await db.fetchrow("SELECT id FROM leads WHERE tenant_id = $1 AND phone_number = $2", tenant_id, lead_phone)
            if lead_row: lead_id = lead_row['id']
        if not lead_id and lead_email:
            lead_row = await db.fetchrow("SELECT id FROM leads WHERE tenant_id = $1 AND email = $2", tenant_id, lead_email)
            if lead_row: lead_id = lead_row['id']

        if event_type in ["BOOKING_CREATED", "BOOKING_RESCHEDULED"]:
            # Sync to seller_agenda_events
            query = """
                INSERT INTO seller_agenda_events (tenant_id, seller_id, title, start_datetime, end_datetime, lead_id, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'scheduled')
                ON CONFLICT (id) DO UPDATE SET
                    start_datetime = EXCLUDED.start_datetime,
                    end_datetime = EXCLUDED.end_datetime,
                    status = 'scheduled'
            """
            # For now, assign to the first active professional/seller if not specified
            # In a real scenario, we'd map Cal.com user ID to our user ID
            seller_row = await db.fetchrow("SELECT id FROM professionals WHERE tenant_id = $1 AND is_active = TRUE LIMIT 1", tenant_id)
            seller_id = seller_row['id'] if seller_row else 1
            
            await db.execute(query, tenant_id, seller_id, title, start_dt, end_dt, lead_id)
            logger.info(f"Cal.com booking synced: {booking_id} for tenant {tenant_id}")

        elif event_type == "BOOKING_CANCELLED":
            await db.execute("UPDATE seller_agenda_events SET status = 'cancelled' WHERE lead_id = $1 AND title = $2", lead_id, title)
            logger.info(f"Cal.com booking cancelled: {booking_id}")

        return {"status": "success"}

calcom_service = CalcomService()
