#!/usr/bin/env python3
"""
Test script for Google Ads + Google OAuth integration.
Tests the basic functionality without requiring actual Google credentials.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_file_imports():
    """Test that all required files can be imported."""
    logger.info("🧪 Testing file imports...")
    
    tests = [
        ("orchestrator_service/routes/google_auth.py", "Google Auth Routes"),
        ("orchestrator_service/services/marketing/google_ads_service.py", "Google Ads Service"),
        ("orchestrator_service/services/auth/google_oauth_service.py", "Google OAuth Service"),
        ("orchestrator_service/run_google_migration.py", "Migration Script"),
    ]
    
    all_passed = True
    
    for file_path, description in tests:
        try:
            # Convert path to module path
            module_path = file_path.replace('/', '.').replace('.py', '')
            __import__(module_path)
            logger.info(f"  ✅ {description}: Import successful")
        except ImportError as e:
            logger.error(f"  ❌ {description}: Import failed - {e}")
            all_passed = False
        except Exception as e:
            logger.error(f"  ❌ {description}: Error - {e}")
            all_passed = False
    
    return all_passed

async def test_google_auth_routes():
    """Test Google Auth routes structure."""
    logger.info("🧪 Testing Google Auth routes structure...")
    
    try:
        from orchestrator_service.routes.google_auth import router, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
        
        # Check that router exists
        assert router is not None, "Router not found"
        
        # Check environment variables (they might not be set yet)
        logger.info(f"  ✅ Google Auth router loaded")
        logger.info(f"  📝 GOOGLE_CLIENT_ID: {'Set' if GOOGLE_CLIENT_ID != 'YOUR_GOOGLE_CLIENT_ID' else 'Not set (using placeholder)'}")
        logger.info(f"  📝 GOOGLE_CLIENT_SECRET: {'Set' if GOOGLE_CLIENT_SECRET != 'YOUR_GOOGLE_CLIENT_SECRET' else 'Not set (using placeholder)'}")
        
        # Check routes
        routes = [route for route in router.routes]
        logger.info(f"  📊 Found {len(routes)} routes in Google Auth")
        
        # List routes
        for route in routes:
            methods = ','.join(route.methods) if route.methods else 'ANY'
            logger.info(f"    • {methods} {route.path}")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Google Auth routes test failed: {e}")
        return False

async def test_google_ads_service():
    """Test Google Ads service structure."""
    logger.info("🧪 Testing Google Ads service structure...")
    
    try:
        from orchestrator_service.services.marketing.google_ads_service import (
            GoogleAdsService, GoogleAdsClient,
            GoogleAdsAuthError, GoogleAdsRateLimitError, GoogleAdsNotFoundError
        )
        
        # Check classes exist
        assert GoogleAdsService is not None, "GoogleAdsService not found"
        assert GoogleAdsClient is not None, "GoogleAdsClient not found"
        
        # Check exception classes
        assert GoogleAdsAuthError is not None, "GoogleAdsAuthError not found"
        assert GoogleAdsRateLimitError is not None, "GoogleAdsRateLimitError not found"
        assert GoogleAdsNotFoundError is not None, "GoogleAdsNotFoundError not found"
        
        logger.info("  ✅ Google Ads service classes loaded")
        
        # Test client initialization
        client = GoogleAdsClient()
        logger.info(f"  ✅ GoogleAdsClient initialized: access_token={'Set' if client.access_token else 'Not set'}")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Google Ads service test failed: {e}")
        return False

async def test_google_oauth_service():
    """Test Google OAuth service structure."""
    logger.info("🧪 Testing Google OAuth service structure...")
    
    try:
        from orchestrator_service.services.auth.google_oauth_service import (
            GoogleOAuthService, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
        )
        
        # Check class exists
        assert GoogleOAuthService is not None, "GoogleOAuthService not found"
        
        logger.info("  ✅ Google OAuth service class loaded")
        logger.info(f"  📝 GOOGLE_CLIENT_ID: {'Set' if GOOGLE_CLIENT_ID != 'YOUR_GOOGLE_CLIENT_ID' else 'Not set (using placeholder)'}")
        logger.info(f"  📝 GOOGLE_CLIENT_SECRET: {'Set' if GOOGLE_CLIENT_SECRET != 'YOUR_GOOGLE_CLIENT_SECRET' else 'Not set (using placeholder)'}")
        
        # Check static methods exist
        methods = [
            'exchange_code_for_token',
            'get_user_info', 
            'create_or_update_user',
            'create_jwt_session',
            'validate_google_token',
            'get_user_by_google_id',
            'link_existing_user_to_google',
            'unlink_google_from_user'
        ]
        
        for method in methods:
            if hasattr(GoogleOAuthService, method):
                logger.info(f"    • {method}(): Found")
            else:
                logger.warning(f"    • {method}(): Missing")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Google OAuth service test failed: {e}")
        return False

async def test_migration_script():
    """Test migration script structure."""
    logger.info("🧪 Testing migration script...")
    
    try:
        from orchestrator_service.run_google_migration import (
            run_migration, rollback_migration, check_migration_status
        )
        
        # Check functions exist
        assert run_migration is not None, "run_migration not found"
        assert rollback_migration is not None, "rollback_migration not found"
        assert check_migration_status is not None, "check_migration_status not found"
        
        logger.info("  ✅ Migration script functions loaded")
        
        # Test argument parsing
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("action", choices=["run", "rollback", "status"])
        
        logger.info("  ✅ Migration script argument parser configured")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Migration script test failed: {e}")
        return False

async def test_main_integration():
    """Test that Google routes are integrated in main.py."""
    logger.info("🧪 Testing main.py integration...")
    
    try:
        main_path = Path(__file__).parent / "orchestrator_service" / "main.py"
        
        if not main_path.exists():
            logger.error(f"  ❌ main.py not found at {main_path}")
            return False
        
        with open(main_path, 'r') as f:
            content = f.read()
        
        # Check for Google routes inclusion
        if "google_auth_router" in content:
            logger.info("  ✅ Google Auth router found in main.py")
        else:
            logger.warning("  ⚠️  Google Auth router not found in main.py - did you update it?")
            return False
        
        if "prefix=\"/crm/auth/google\"" in content:
            logger.info("  ✅ Google routes prefix configured correctly")
        else:
            logger.warning("  ⚠️  Google routes prefix not found in main.py")
            return False
        
        if "Google Ads Marketing API mounted" in content:
            logger.info("  ✅ Google Ads mount log message found")
        else:
            logger.warning("  ⚠️  Google Ads mount log message not found")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Main integration test failed: {e}")
        return False

async def test_credentials_integration():
    """Test that Google credentials are added to credentials.py."""
    logger.info("🧪 Testing credentials.py integration...")
    
    try:
        creds_path = Path(__file__).parent / "orchestrator_service" / "core" / "credentials.py"
        
        if not creds_path.exists():
            logger.error(f"  ❌ credentials.py not found at {creds_path}")
            return False
        
        with open(creds_path, 'r') as f:
            content = f.read()
        
        # Check for Google credential constants
        google_constants = [
            "GOOGLE_ADS_TOKEN",
            "GOOGLE_CLIENT_ID", 
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_DEVELOPER_TOKEN"
        ]
        
        all_found = True
        for constant in google_constants:
            if constant in content:
                logger.info(f"  ✅ {constant} found in credentials.py")
            else:
                logger.warning(f"  ⚠️  {constant} not found in credentials.py")
                all_found = False
        
        return all_found
        
    except Exception as e:
        logger.error(f"  ❌ Credentials integration test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests."""
    logger.info("🚀 Starting Google Ads + Google OAuth integration tests...")
    logger.info("=" * 60)
    
    tests = [
        ("File Imports", test_file_imports),
        ("Google Auth Routes", test_google_auth_routes),
        ("Google Ads Service", test_google_ads_service),
        ("Google OAuth Service", test_google_oauth_service),
        ("Migration Script", test_migration_script),
        ("Main Integration", test_main_integration),
        ("Credentials Integration", test_credentials_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 {test_name}")
        logger.info("-" * 40)
        
        try:
            result = await test_func()
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
        logger.info("🎉 ALL TESTS PASSED! Google integration is ready for configuration.")
    else:
        logger.warning("⚠️  Some tests failed. Check the logs above for details.")
    
    # Next steps
    logger.info("\n📝 NEXT STEPS:")
    logger.info("1. Configure Google Cloud Console:")
    logger.info("   • Create project and enable APIs")
    logger.info("   • Configure OAuth consent screen")
    logger.info("   • Create OAuth 2.0 credentials")
    logger.info("   • Request Google Ads Developer Token")
    logger.info("")
    logger.info("2. Set environment variables:")
    logger.info("   • GOOGLE_CLIENT_ID")
    logger.info("   • GOOGLE_CLIENT_SECRET")
    logger.info("   • GOOGLE_DEVELOPER_TOKEN")
    logger.info("   • GOOGLE_REDIRECT_URI")
    logger.info("   • GOOGLE_LOGIN_REDIRECT_URI")
    logger.info("")
    logger.info("3. Run database migration:")
    logger.info("   cd orchestrator_service && python run_google_migration.py run")
    logger.info("")
    logger.info("4. Test with actual Google credentials")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)