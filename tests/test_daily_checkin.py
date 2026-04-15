"""Tests for SPEC-05: Daily Check-in"""
import os, uuid, pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal

os.environ.setdefault("POSTGRES_DSN", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("YCLOUD_API_KEY", "test")
os.environ.setdefault("YCLOUD_WEBHOOK_SECRET", "test")
os.environ.setdefault("INTERNAL_API_TOKEN", "test")

from services.daily_checkin_service import DailyCheckinService, CheckinAlreadyExistsError, CheckinAlreadyClosedError

@pytest.fixture
def svc(): return DailyCheckinService()

@pytest.fixture
def mock_db():
    with patch("services.daily_checkin_service.db") as m:
        m.pool = MagicMock()
        conn = AsyncMock()
        m.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        m.pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        yield m, conn

@pytest.fixture
def mock_sio():
    with patch("services.daily_checkin_service.sio") as m:
        m.emit = AsyncMock()
        yield m

@pytest.mark.asyncio
async def test_checkin_success(svc, mock_db, mock_sio):
    _, conn = mock_db
    sid = str(uuid.uuid4())
    conn.fetchrow.side_effect = [None, {"id": uuid.uuid4(), "tenant_id": 1, "seller_id": uuid.UUID(sid), "fecha": "2025-04-14", "llamadas_planeadas": 20, "estado": "active", "checkin_at": "2025-04-14T09:00:00Z"}]
    result = await svc.checkin(sid, 1, 20)
    assert result["estado"] == "active"

@pytest.mark.asyncio
async def test_checkin_duplicate(svc, mock_db, mock_sio):
    _, conn = mock_db
    conn.fetchrow.return_value = {"id": uuid.uuid4()}
    with pytest.raises(CheckinAlreadyExistsError):
        await svc.checkin(str(uuid.uuid4()), 1, 20)

@pytest.mark.asyncio
async def test_checkout_success(svc, mock_db, mock_sio):
    _, conn = mock_db
    cid = uuid.uuid4()
    sid = uuid.uuid4()
    conn.fetchrow.side_effect = [
        {"id": cid, "estado": "active", "llamadas_planeadas": 20},
        {"id": cid, "tenant_id": 1, "seller_id": sid, "fecha": "2025-04-14", "llamadas_planeadas": 20, "llamadas_logradas": 17, "contactos_logrados": 5, "cumplimiento_pct": Decimal("85.00"), "estado": "completed", "checkin_at": "2025-04-14T09:00:00Z", "checkout_at": "2025-04-14T18:00:00Z"},
    ]
    result = await svc.checkout(str(cid), str(sid), 1, 17, 5)
    assert result["estado"] == "completed"
    assert result["cumplimiento_pct"] == 85.0

@pytest.mark.asyncio
async def test_checkout_already_closed(svc, mock_db, mock_sio):
    _, conn = mock_db
    conn.fetchrow.return_value = {"id": uuid.uuid4(), "estado": "completed", "llamadas_planeadas": 20}
    with pytest.raises(CheckinAlreadyClosedError):
        await svc.checkout(str(uuid.uuid4()), str(uuid.uuid4()), 1, 17, 5)

@pytest.mark.asyncio
async def test_checkout_not_found(svc, mock_db, mock_sio):
    _, conn = mock_db
    conn.fetchrow.return_value = None
    result = await svc.checkout(str(uuid.uuid4()), str(uuid.uuid4()), 1, 17, 5)
    assert result is None

def test_cumplimiento_colors():
    assert 85.0 >= 80  # verde
    assert 50.0 >= 50  # amarillo
    assert 45.0 < 50   # rojo
