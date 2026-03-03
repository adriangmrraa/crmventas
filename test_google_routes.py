#!/usr/bin/env python3
"""
Test script for Google Ads routes integration.
Tests that all routes are properly registered and accessible.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_routes_registration():
    """Test that Google routes are properly registered in main.py."""
    logger.info("🧪 Testing Google routes registration...")
    
    main_path = Path(__file__).parent / "orchestrator_service" / "main.py"
    
    if not main_path.exists():
        logger.error(f"❌ main.py not found at {main_path}")
        return False
    
    with open(main_path, 'r') as f:
        content = f.read()
    
    tests = [
        ("Google Auth router import", "from routes.google_auth import router as google_auth_router"),
        ("Google Ads routes import", "from routes.google_ads_routes import router as google_ads_routes_router"),
        ("Google Auth router registration", 'app.include_router(google_auth_router, prefix="/crm/auth/google"'),
        ("Google Ads routes registration", 'app.include_router(google_ads_routes_router, prefix="/crm/marketing"'),
        ("Google OAuth tags", 'tags=["Google OAuth"]'),
        ("Google Ads tags", 'tags=["Google Ads"]'),
        ("Mount success log", 'logger.info("✅ Google Ads Marketing API mounted")')
    ]
    
    all_passed = True
    for test_name, search_string in tests:
        if search_string in content:
            logger.info(f"  ✅ {test_name}")
        else:
            logger.error(f"  ❌ {test_name}: '{search_string}' not found")
            all_passed = False
    
    return all_passed

def test_google_ads_routes_file():
    """Test that google_ads_routes.py exists and has correct structure."""
    logger.info("🧪 Testing google_ads_routes.py structure...")
    
    routes_path = Path(__file__).parent / "orchestrator_service" / "routes" / "google_ads_routes.py"
    
    if not routes_path.exists():
        logger.error(f"❌ google_ads_routes.py not found at {routes_path}")
        return False
    
    with open(routes_path, 'r') as f:
        content = f.read()
    
    tests = [
        ("File exists", True),
        ("Router definition", "router = APIRouter()"),
        ("Import GoogleAdsService", "from services.marketing.google_ads_service import GoogleAdsService"),
        ("Campaigns endpoint", "@router.get(\"/google/campaigns\")"),
        ("Metrics endpoint", "@router.get(\"/google/metrics\")"),
        ("Customers endpoint", "@router.get(\"/google/customers\")"),
        ("Sync endpoint", "@router.post(\"/google/sync\")"),
        ("Stats endpoint", "@router.get(\"/google/stats\")"),
        ("Combined stats endpoint", "@router.get(\"/combined-stats\")"),
        ("Connection status endpoint", "@router.get(\"/google/connection-status\")"),
        ("Debug endpoint", "@router.get(\"/google/debug\")"),
        ("Audit access decorator", "@audit_access"),
        ("Rate limiting", "@limiter.limit"),
        ("Error handling", "except Exception as e:"),
        ("JSON response", "timestamp")
    ]
    
    all_passed = True
    for test_name, condition in tests:
        if isinstance(condition, bool):
            # Simple existence test
            if condition:
                logger.info(f"  ✅ {test_name}")
            else:
                logger.error(f"  ❌ {test_name}")
                all_passed = False
        elif isinstance(condition, str):
            # String search test
            if condition in content:
                logger.info(f"  ✅ {test_name}")
            else:
                logger.error(f"  ❌ {test_name}: '{condition}' not found")
                all_passed = False
    
    # Count endpoints
    endpoint_count = content.count("@router.")
    logger.info(f"  📊 Found {endpoint_count} endpoints in google_ads_routes.py")
    
    return all_passed

def test_frontend_api_integration():
    """Test that frontend API client matches backend routes."""
    logger.info("🧪 Testing frontend-backend API integration...")
    
    # Check frontend API client
    api_path = Path(__file__).parent / "frontend_react" / "src" / "api" / "google_ads.ts"
    
    if not api_path.exists():
        logger.error(f"❌ google_ads.ts not found at {api_path}")
        return False
    
    with open(api_path, 'r') as f:
        api_content = f.read()
    
    # Check backend routes
    routes_path = Path(__file__).parent / "orchestrator_service" / "routes" / "google_ads_routes.py"
    with open(routes_path, 'r') as f:
        routes_content = f.read()
    
    # Map frontend functions to backend endpoints
    api_functions = [
        ("getGoogleAdsCampaigns", "/google/campaigns"),
        ("getGoogleAdsMetrics", "/google/metrics"),
        ("getAccessibleGoogleAdsCustomers", "/google/customers"),
        ("syncGoogleAdsData", "/google/sync"),
        ("testGoogleAdsConnection", "/google/connection-status"),
        ("getGoogleAdsStats", "/google/stats")
    ]
    
    all_passed = True
    for func_name, endpoint in api_functions:
        # Check frontend has function
        if f"async function {func_name}" in api_content or f"export async function {func_name}" in api_content:
            logger.info(f"  ✅ Frontend: {func_name}() exists")
        else:
            logger.error(f"  ❌ Frontend: {func_name}() not found")
            all_passed = False
        
        # Check backend has endpoint
        if f'@router.get("{endpoint}")' in routes_content or f'@router.post("{endpoint}")' in routes_content:
            logger.info(f"  ✅ Backend: {endpoint} endpoint exists")
        else:
            logger.error(f"  ❌ Backend: {endpoint} endpoint not found")
            all_passed = False
    
    return all_passed

def test_combined_endpoint():
    """Test the combined stats endpoint specifically."""
    logger.info("🧪 Testing combined stats endpoint...")
    
    routes_path = Path(__file__).parent / "orchestrator_service" / "routes" / "google_ads_routes.py"
    
    with open(routes_path, 'r') as f:
        content = f.read()
    
    # Check combined endpoint exists
    if '@router.get("/combined-stats")' in content:
        logger.info("  ✅ Combined stats endpoint exists")
        
        # Check it imports necessary services
        if "from services.marketing.marketing_service import MarketingService" in content:
            logger.info("  ✅ Imports MarketingService")
        else:
            logger.error("  ❌ Does not import MarketingService")
            return False
        
        # Check it calls both services
        if "MarketingService.get_roi_stats" in content and "GoogleAdsService.test_connection" in content:
            logger.info("  ✅ Calls both Meta and Google services")
        else:
            logger.error("  ❌ Does not call both services")
            return False
        
        return True
    else:
        logger.error("  ❌ Combined stats endpoint not found")
        return False

def test_marketing_hub_integration():
    """Test that MarketingHubView uses the combined endpoint."""
    logger.info("🧪 Testing MarketingHubView integration...")
    
    view_path = Path(__file__).parent / "frontend_react" / "src" / "views" / "marketing" / "MarketingHubView.tsx"
    
    if not view_path.exists():
        logger.error(f"❌ MarketingHubView.tsx not found at {view_path}")
        return False
    
    with open(view_path, 'r') as f:
        content = f.read()
    
    tests = [
        ("Uses combined endpoint", 'await api.get(`/crm/marketing/combined-stats'),
        ("Sets Meta connection", 'setIsMetaConnected'),
        ("Sets Google connection", 'setIsGoogleConnected'),
        ("Platform tabs", 'activePlatform'),
        ("Google connection handler", 'handleConnectGoogle'),
        ("Google wizard", 'GoogleConnectionWizard'),
        ("Platform data helper", 'getPlatformData()'),
        ("Currency helper", 'getCurrency()'),
        ("Empty state helper", 'getEmptyStateMessage()')
    ]
    
    all_passed = True
    for test_name, search_string in tests:
        if search_string in content:
            logger.info(f"  ✅ {test_name}")
        else:
            logger.error(f"  ❌ {test_name}: '{search_string}' not found")
            all_passed = False
    
    return all_passed

def run_all_tests():
    """Run all tests."""
    logger.info("🚀 Starting Google Ads routes integration tests...")
    logger.info("=" * 60)
    
    tests = [
        ("Routes Registration", test_routes_registration),
        ("Google Ads Routes File", test_google_ads_routes_file),
        ("Frontend-Backend API Integration", test_frontend_api_integration),
        ("Combined Endpoint", test_combined_endpoint),
        ("Marketing Hub Integration", test_marketing_hub_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 {test_name}")
        logger.info("-" * 40)
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    logger.info(f"✅ Passed: {passed}/{total}")
    logger.info(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! Google Ads routes are properly integrated.")
    else:
        logger.warning("⚠️  Some tests failed. Check the logs above for details.")
    
    # Next steps
    logger.info("\n📝 NEXT STEPS:")
    logger.info("1. Configure Google Cloud Console with credentials")
    logger.info("2. Set environment variables:")
    logger.info("   • GOOGLE_CLIENT_ID")
    logger.info("   • GOOGLE_CLIENT_SECRET")
    logger.info("   • GOOGLE_DEVELOPER_TOKEN")
    logger.info("3. Run database migration:")
    logger.info("   cd orchestrator_service && python run_google_migration.py run")
    logger.info("4. Test with actual API calls")
    logger.info("5. Deploy to staging environment")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)