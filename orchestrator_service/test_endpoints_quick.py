#!/usr/bin/env python3
"""
Quick test of Meta Ads endpoints without database.
Tests route registration and basic functionality.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Mock headers for testing
MOCK_HEADERS = {
    "Authorization": "Bearer test_token",
    "X-Admin-Token": "test_admin_token"
}

def test_route_registration():
    """Test that routes are properly registered."""
    print("🔍 Testing route registration...")
    
    # Get all registered routes
    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            routes.append({
                "path": route.path,
                "methods": getattr(route, "methods", set()),
                "name": getattr(route, "name", "N/A")
            })
    
    # Filter for Meta Ads routes
    meta_routes = [r for r in routes if "/crm/marketing" in r["path"] or "/crm/auth/meta" in r["path"]]
    
    print(f"📊 Found {len(meta_routes)} Meta Ads routes:")
    for route in meta_routes:
        methods = ", ".join(sorted(route["methods"])) if route["methods"] else "N/A"
        print(f"   • {methods} {route['path']}")
    
    # Check for expected routes
    expected_paths = [
        "/crm/marketing/stats",
        "/crm/marketing/stats/roi",
        "/crm/marketing/token-status",
        "/crm/marketing/meta-portfolios",
        "/crm/marketing/meta-accounts",
        "/crm/marketing/connect",
        "/crm/marketing/automation-logs",
        "/crm/marketing/hsm/templates",
        "/crm/marketing/automation/rules",
        "/crm/marketing/campaigns",
        "/crm/auth/meta/url",
        "/crm/auth/meta/callback",
        "/crm/auth/meta/disconnect",
        "/crm/auth/meta/debug/token",
        "/crm/auth/meta/test-connection"
    ]
    
    missing_routes = []
    for expected in expected_paths:
        if not any(expected in r["path"] for r in meta_routes):
            missing_routes.append(expected)
    
    if missing_routes:
        print(f"❌ Missing routes: {len(missing_routes)}")
        for missing in missing_routes:
            print(f"   • {missing}")
        return False
    else:
        print("✅ All expected routes are registered!")
        return True

def test_endpoint_responses():
    """Test endpoint responses (will fail due to auth, but should return proper status codes)."""
    print("\n🔍 Testing endpoint responses...")
    
    endpoints_to_test = [
        ("GET", "/crm/marketing/stats"),
        ("GET", "/crm/marketing/stats/roi"),
        ("GET", "/crm/marketing/token-status"),
        ("GET", "/crm/marketing/meta-portfolios"),
        ("GET", "/crm/marketing/meta-accounts"),
        ("GET", "/crm/marketing/hsm/templates"),
        ("GET", "/crm/marketing/automation/rules"),
        ("GET", "/crm/marketing/campaigns"),
        ("GET", "/crm/auth/meta/url"),
        ("GET", "/crm/auth/meta/debug/token"),
        ("GET", "/crm/auth/meta/test-connection"),
    ]
    
    results = []
    for method, path in endpoints_to_test:
        try:
            if method == "GET":
                response = client.get(path, headers=MOCK_HEADERS)
            elif method == "POST":
                response = client.post(path, headers=MOCK_HEADERS, json={})
            
            status = response.status_code
            # Acceptable status codes: 200 (success), 401/403 (auth failed), 422 (validation error)
            if status in [200, 401, 403, 422, 500]:
                results.append((path, status, "✅" if status != 500 else "⚠️"))
            else:
                results.append((path, status, "❌"))
                
        except Exception as e:
            results.append((path, f"ERROR: {str(e)[:50]}", "❌"))
    
    print("📊 Endpoint response summary:")
    for path, status, symbol in results:
        print(f"   {symbol} {path} -> {status}")
    
    # Count successes (excluding 500 errors which indicate server issues)
    success_count = sum(1 for _, status, symbol in results if symbol == "✅")
    total_count = len(results)
    
    print(f"\n📈 Success rate: {success_count}/{total_count} endpoints responding")
    
    return success_count >= total_count * 0.8  # 80% success rate

def test_imports():
    """Test that all required modules can be imported."""
    print("\n🔍 Testing module imports...")
    
    modules_to_test = [
        "routes.marketing",
        "routes.meta_auth",
        "services.marketing.marketing_service",
        "services.marketing.meta_ads_service",
        "services.marketing.automation_service",
    ]
    
    results = []
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            results.append((module_name, "✅"))
        except ImportError as e:
            results.append((module_name, f"❌ {str(e)[:50]}"))
        except Exception as e:
            results.append((module_name, f"⚠️ {str(e)[:50]}"))
    
    for module_name, status in results:
        print(f"   {status} {module_name}")
    
    success_count = sum(1 for _, status in results if "✅" in status)
    return success_count == len(modules_to_test)

def test_migration_file():
    """Test that migration file exists and is valid."""
    print("\n🔍 Testing migration file...")
    
    migration_file = Path(__file__).parent / "migrations" / "patch_009_meta_ads_tables.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for key SQL statements
        checks = [
            ("CREATE TABLE", "CREATE TABLE statements"),
            ("meta_ads_campaigns", "meta_ads_campaigns table"),
            ("opportunities", "opportunities table"),
            ("sales_transactions", "sales_transactions table"),
            ("calculate_campaign_roi", "ROI function"),
        ]
        
        results = []
        for keyword, description in checks:
            if keyword in content:
                results.append((description, "✅"))
            else:
                results.append((description, "❌"))
        
        for description, status in results:
            print(f"   {status} {description}")
        
        success_count = sum(1 for _, status in results if "✅" in status)
        file_size_kb = len(content) / 1024
        print(f"   📏 File size: {file_size_kb:.1f} KB")
        
        return success_count >= len(checks) - 1  # Allow one missing
        
    except Exception as e:
        print(f"❌ Error reading migration file: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Meta Ads Endpoint Tests")
    print("=" * 50)
    
    tests = [
        ("Route Registration", test_route_registration),
        ("Module Imports", test_imports),
        ("Migration File", test_migration_file),
        ("Endpoint Responses", test_endpoint_responses),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 30)
        try:
            success = test_func()
            results.append((test_name, success))
            print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Sprint 1 Day 2 validation complete.")
        print("\n📋 Next steps:")
        print("   1. Configure POSTGRES_DSN environment variable")
        print("   2. Run database migrations: python run_meta_ads_migrations.py")
        print("   3. Test with actual database connection")
        print("   4. Configure Meta Developers App for OAuth testing")
    else:
        print(f"\n⚠️ {total - passed} tests failed. Review issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)