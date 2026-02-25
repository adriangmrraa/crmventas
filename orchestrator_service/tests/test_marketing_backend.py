"""
Test Suite for Meta Ads Marketing Backend
Sprint 1 - Day 3: Backend Testing
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

# Import the main app
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from services.marketing.marketing_service import MarketingService
from services.marketing.meta_ads_service import MetaAdsService
from services.marketing.automation_service import AutomationService

client = TestClient(app)

# Mock authentication headers
MOCK_HEADERS = {
    "Authorization": "Bearer test_token",
    "X-Admin-Token": "test_admin_token"
}

class TestMarketingBackend:
    """Test suite for marketing backend endpoints."""
    
    def setup_method(self):
        """Setup before each test."""
        self.tenant_id = 1
        self.user_id = 100
        
    # ==================== DASHBOARD ENDPOINTS ====================
    
    def test_marketing_stats_endpoint(self):
        """Test /crm/marketing/stats endpoint."""
        with patch('routes.marketing.MarketingService.get_roi_stats') as mock_get_stats:
            mock_get_stats.return_value = asyncio.Future()
            mock_get_stats.return_value.set_result({
                "leads": 150,
                "leads_change": 15.5,
                "opportunities": 45,
                "opportunities_change": 22.2,
                "sales_revenue": 25000,
                "revenue_change": 18.7,
                "marketing_spend": 5000,
                "spend_change": -5.3,
                "roi_percentage": 400,
                "roi_change": 25.0,
                "cpa": 33.33
            })
            
            response = client.get(
                "/crm/marketing/stats?time_range=last_30d",
                headers=MOCK_HEADERS
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert "data" in data
            assert data["data"]["leads"] == 150
            assert data["data"]["roi_percentage"] == 400
    
    def test_roi_details_endpoint(self):
        """Test /crm/marketing/stats/roi endpoint."""
        with patch('routes.marketing.MarketingService.get_roi_breakdown') as mock_get_details:
            mock_get_details.return_value = asyncio.Future()
            mock_get_details.return_value.set_result({
                "campaigns": [
                    {
                        "id": "campaign_123",
                        "name": "Test Campaign",
                        "spend": 1000,
                        "revenue": 5000,
                        "roi": 400,
                        "leads": 50,
                        "opportunities": 15
                    }
                ],
                "time_period": "last_30d",
                "total_spend": 5000,
                "total_revenue": 25000,
                "average_roi": 400
            })
            
            response = client.get(
                "/crm/marketing/stats/roi?time_range=last_30d",
                headers=MOCK_HEADERS
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert len(data["data"]["campaigns"]) == 1
            assert data["data"]["campaigns"][0]["name"] == "Test Campaign"
    
    def test_token_status_endpoint(self):
        """Test /crm/marketing/token-status endpoint."""
        with patch('routes.marketing.MetaAdsService.check_token_status') as mock_check_status:
            mock_check_status.return_value = asyncio.Future()
            mock_check_status.return_value.set_result({
                "connected": True,
                "expires_at": "2024-12-31T23:59:59Z",
                "scopes": ["ads_management", "business_management"],
                "business_managers": 2,
                "ad_accounts": 5
            })
            
            response = client.get(
                "/crm/marketing/token-status",
                headers=MOCK_HEADERS
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["data"]["connected"] == True
            assert "business_managers" in data["data"]
    
    # ==================== META ACCOUNT MANAGEMENT ====================
    
    def test_get_meta_portfolios(self):
        """Test /crm/marketing/meta-portfolios endpoint."""
        with patch('routes.marketing.MetaAdsService.get_business_managers') as mock_get_bms:
            mock_get_bms.return_value = asyncio.Future()
            mock_get_bms.return_value.set_result([
                {
                    "id": "bm_123",
                    "name": "Business Manager 1",
                    "ad_accounts_count": 3
                },
                {
                    "id": "bm_456",
                    "name": "Business Manager 2",
                    "ad_accounts_count": 2
                }
            ])
            
            response = client.get(
                "/crm/marketing/meta-portfolios",
                headers=MOCK_HEADERS
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert len(data["data"]) == 2
            assert data["data"][0]["name"] == "Business Manager 1"
    
    def test_get_meta_accounts(self):
        """Test /crm/marketing/meta-accounts endpoint."""
        with patch('routes.marketing.MetaAdsService.get_ad_accounts') as mock_get_accounts:
            mock_get_accounts.return_value = asyncio.Future()
            mock_get_accounts.return_value.set_result([
                {
                    "id": "act_123",
                    "name": "Ad Account 1",
                    "currency": "USD",
                    "timezone": "America/New_York",
                    "status": "ACTIVE"
                }
            ])
            
            response = client.get(
                "/crm/marketing/meta-accounts?portfolio_id=bm_123",
                headers=MOCK_HEADERS
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert len(data["data"]) == 1
            assert data["data"][0]["name"] == "Ad Account 1"
    
    def test_connect_meta_account(self):
        """Test /crm/marketing/connect endpoint."""
        with patch('routes.marketing.MetaAdsService.connect_ad_account') as mock_connect:
            mock_connect.return_value = asyncio.Future()
            mock_connect.return_value.set_result({
                "connected": True,
                "account_id": "act_123",
                "account_name": "Test Account",
                "message": "Account connected successfully"
            })
            
            response = client.post(
                "/crm/marketing/connect",
                headers=MOCK_HEADERS,
                json={
                    "account_id": "act_123",
                    "account_name": "Test Account"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["data"]["connected"] == True
            assert data["data"]["account_id"] == "act_123"
    
    # ==================== HSM AUTOMATION ENDPOINTS ====================
    
    def test_get_hsm_templates(self):
        """Test /crm/marketing/hsm/templates endpoint."""
        with patch('routes.marketing.AutomationService.get_hsm_templates') as mock_get_templates:
            mock_get_templates.return_value = asyncio.Future()
            mock_get_templates.return_value.set_result([
                {
                    "id": "template_123",
                    "name": "Welcome Template",
                    "category": "MARKETING",
                    "language": "es",
                    "status": "APPROVED",
                    "components": {
                        "header": {"type": "text", "text": "Welcome!"},
                        "body": {"text": "Thank you for your interest."}
                    }
                }
            ])
            
            response = client.get(
                "/crm/marketing/hsm/templates",
                headers=MOCK_HEADERS
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert len(data["data"]) == 1
            assert data["data"][0]["name"] == "Welcome Template"
    
    def test_get_automation_rules(self):
        """Test /crm/marketing/automation/rules endpoint."""
        with patch('routes.marketing.AutomationService.get_automation_rules') as mock_get_rules:
            mock_get_rules.return_value = asyncio.Future()
            mock_get_rules.return_value.set_result([
                {
                    "id": "rule_123",
                    "name": "New Lead Follow-up",
                    "trigger_type": "lead_created",
                    "is_active": True,
                    "trigger_count": 150
                }
            ])
            
            response = client.get(
                "/crm/marketing/automation/rules",
                headers=MOCK_HEADERS
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert len(data["data"]) == 1
            assert data["data"][0]["name"] == "New Lead Follow-up"
    
    def test_update_automation_rules(self):
        """Test POST /crm/marketing/automation/rules endpoint."""
        with patch('routes.marketing.AutomationService.update_automation_rules') as mock_update_rules:
            mock_update_rules.return_value = asyncio.Future()
            mock_update_rules.return_value.set_result({
                "updated": True,
                "rules_count": 1,
                "message": "Rules updated successfully"
            })
            
            response = client.post(
                "/crm/marketing/automation/rules",
                headers=MOCK_HEADERS,
                json={
                    "rules": [
                        {
                            "name": "New Rule",
                            "trigger_type": "lead_status_changed",
                            "action_type": "send_hsm"
                        }
                    ]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["data"]["updated"] == True
    
    # ==================== CAMPAIGN MANAGEMENT ====================
    
    def test_get_campaigns(self):
        """Test /crm/marketing/campaigns endpoint."""
        with patch('routes.marketing.MetaAdsService.get_campaigns_with_performance') as mock_get_campaigns:
            mock_get_campaigns.return_value = asyncio.Future()
            mock_get_campaigns.return_value.set_result([
                {
                    "id": "campaign_123",
                    "name": "Q1 Sales Campaign",
                    "status": "ACTIVE",
                    "spend": 2500,
                    "leads": 125,
                    "opportunities": 38,
                    "revenue": 12500,
                    "roi": 400
                }
            ])
            
            response = client.get(
                "/crm/marketing/campaigns?status=ACTIVE&limit=10",
                headers=MOCK_HEADERS
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert len(data["data"]) == 1
            assert data["data"][0]["name"] == "Q1 Sales Campaign"
    
    def test_get_campaign_details(self):
        """Test /crm/marketing/campaigns/{campaign_id} endpoint."""
        with patch('routes.marketing.MetaAdsService.get_campaign_details') as mock_get_details:
            mock_get_details.return_value = asyncio.Future()
            mock_get_details.return_value.set_result({
                "id": "campaign_123",
                "name": "Detailed Campaign",
                "objective": "LEADS",
                "daily_budget": 100,
                "targeting": {"age_min": 25, "age_max": 55},
                "performance": {
                    "spend": 2500,
                    "leads": 125,
                    "cpa": 20
                }
            })
            
            response = client.get(
                "/crm/marketing/campaigns/campaign_123",
                headers=MOCK_HEADERS
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["data"]["name"] == "Detailed Campaign"
            assert "performance" in data["data"]
    
    # ==================== ERROR HANDLING ====================
    
    def test_missing_authentication(self):
        """Test endpoints without authentication headers."""
        response = client.get("/crm/marketing/stats")
        # Should return 401 or 403 (depending on implementation)
        assert response.status_code in [401, 403, 422]
    
    def test_invalid_time_range(self):
        """Test with invalid time range parameter."""
        response = client.get(
            "/crm/marketing/stats?time_range=invalid_range",
            headers=MOCK_HEADERS
        )
        # Should handle gracefully - either 400 or use default
        assert response.status_code in [200, 400, 422]
    
    def test_rate_limiting(self):
        """Test rate limiting (simulated)."""
        # Note: Actual rate limiting would need more sophisticated testing
        # This just verifies the endpoint exists
        response = client.get(
            "/crm/marketing/stats",
            headers=MOCK_HEADERS
        )
        assert response.status_code in [200, 429]

# ==================== SERVICE UNIT TESTS ====================

class TestMarketingService:
    """Unit tests for MarketingService."""
    
    @pytest.mark.asyncio
    async def test_get_roi_stats(self):
        """Test ROI stats calculation."""
        with patch('services.marketing.marketing_service.db.pool.fetchval') as mock_fetchval:
            mock_fetchval.side_effect = [
                150,  # meta_leads
                45,   # converted_leads
                25000, # revenue
                5000   # spend
            ]
            
            with patch('services.marketing.marketing_service.get_tenant_credential') as mock_get_cred:
                mock_get_cred.return_value = "mock_token"
                
                stats = await MarketingService.get_roi_stats(1, "last_30d")
                
                assert "leads" in stats
                assert "opportunities" in stats
                assert "sales_revenue" in stats
                assert "marketing_spend" in stats
                assert "roi_percentage" in stats
                
                # Verify calculations
                assert stats["leads"] == 150
                assert stats["opportunities"] == 45
                assert stats["sales_revenue"] == 25000
                assert stats["marketing_spend"] == 5000
                # ROI = ((25000 - 5000) / 5000) * 100 = 400
                assert stats["roi_percentage"] == 400
    
    @pytest.mark.asyncio
    async def test_get_roi_stats_no_token(self):
        """Test ROI stats when no Meta token is connected."""
        with patch('services.marketing.marketing_service.get_tenant_credential') as mock_get_cred:
            mock_get_cred.return_value = None
            
            stats = await MarketingService.get_roi_stats(1, "last_30d")
            
            assert "leads" in stats
            assert stats["meta_connected"] == False
            assert "connect_url" in stats

class TestMetaAdsService:
    """Unit tests for MetaAdsService."""
    
    @pytest.mark.asyncio
    async def test_check_token_status_connected(self):
        """Test token status check when connected."""
        with patch('services.marketing.meta_ads_service.get_tenant_credential') as mock_get_cred:
            mock_get_cred.return_value = "valid_token"
            
            with patch('services.marketing.meta_ads_service.MetaAdsService.validate_token') as mock_validate:
                mock_validate.return_value = {
                    "valid": True,
                    "expires_at": "2024-12-31T23:59:59Z",
                    "scopes": ["ads_management"]
                }
                
                status = await MetaAdsService.check_token_status(1)
                
                assert status["connected"] == True
                assert "expires_at" in status
                assert "scopes" in status
    
    @pytest.mark.asyncio
    async def test_check_token_status_not_connected(self):
        """Test token status check when not connected."""
        with patch('services.marketing.meta_ads_service.get_tenant_credential') as mock_get_cred:
            mock_get_cred.return_value = None
            
            status = await MetaAdsService.check_token_status(1)
            
            assert status["connected"] == False
            assert "connect_url" in status

# ==================== RUN TESTS ====================

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))