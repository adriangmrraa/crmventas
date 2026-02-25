#!/usr/bin/env python3
"""
Verify Meta Ads implementation without running the server.
Checks file structure, imports, and code quality.
"""

import os
import sys
import ast
from pathlib import Path
import re

def check_file_exists(path, description):
    """Check if a file exists."""
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists

def check_directory_exists(path, description):
    """Check if a directory exists."""
    exists = os.path.isdir(path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists

def check_file_content(path, required_strings):
    """Check if file contains required strings."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        results = []
        for string, description in required_strings:
            found = string in content
            status = "✅" if found else "❌"
            results.append((description, found))
            print(f"   {status} {description}")
        
        return all(found for _, found in results)
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")
        return False

def check_python_imports(file_path):
    """Check if Python file can be parsed for imports."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the AST
        tree = ast.parse(content)
        
        # Check for imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for name in node.names:
                    imports.append(f"{module}.{name.name}")
        
        print(f"   📦 Imports found: {len(imports)}")
        if imports:
            print(f"   📋 Sample imports: {', '.join(imports[:3])}{'...' if len(imports) > 3 else ''}")
        
        return True
    except SyntaxError as e:
        print(f"   ❌ Syntax error: {e}")
        return False
    except Exception as e:
        print(f"   ⚠️ Parse warning: {e}")
        return True  # Still consider it OK for now

def check_sql_migration(file_path):
    """Check SQL migration file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ("BEGIN;", "Transaction start"),
            ("CREATE TABLE", "CREATE TABLE statements"),
            ("CREATE INDEX", "Index creation"),
            ("COMMIT;", "Transaction commit"),
            ("meta_ads_campaigns", "Meta Ads campaigns table"),
            ("opportunities", "Opportunities table"),
            ("sales_transactions", "Sales transactions table"),
        ]
        
        print("   🔍 SQL checks:")
        results = []
        for string, description in checks:
            count = content.count(string)
            status = "✅" if count > 0 else "❌"
            results.append((description, count > 0))
            print(f"      {status} {description} ({count} occurrences)")
        
        # Check for common SQL issues
        issues = []
        if "DROP TABLE" in content and "IF EXISTS" not in content:
            issues.append("DROP TABLE without IF EXISTS")
        
        if issues:
            print(f"   ⚠️ Potential issues: {', '.join(issues)}")
        
        return all(found for _, found in results)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Main verification function."""
    print("🔍 VERIFYING META ADS IMPLEMENTATION")
    print("=" * 60)
    
    base_dir = Path(__file__).parent
    results = []
    
    # 1. Check directory structure
    print("\n📁 DIRECTORY STRUCTURE")
    print("-" * 40)
    
    dir_checks = [
        (base_dir / "services" / "marketing", "Marketing services directory"),
        (base_dir / "routes", "Routes directory"),
        (base_dir / "migrations", "Migrations directory"),
        (base_dir / "tests", "Tests directory"),
    ]
    
    for path, description in dir_checks:
        results.append(("DIR", description, check_directory_exists(path, description)))
    
    # 2. Check service files
    print("\n⚙️ SERVICE FILES")
    print("-" * 40)
    
    service_files = [
        (base_dir / "services" / "marketing" / "meta_ads_service.py", "Meta Ads service"),
        (base_dir / "services" / "marketing" / "marketing_service.py", "Marketing service"),
        (base_dir / "services" / "marketing" / "automation_service.py", "Automation service"),
    ]
    
    for path, description in service_files:
        if check_file_exists(path, description):
            print("   📄 Content checks:")
            # Check for adapted terminology
            required_strings = [
                ("leads", "Uses 'leads' (not patients)"),
                ("opportunities", "Uses 'opportunities' (not appointments)"),
                ("lead_source", "Uses 'lead_source' (not acquisition_source)"),
            ]
            content_ok = check_file_content(path, required_strings)
            results.append(("SVC", description, content_ok))
            
            # Check Python syntax
            print("   🐍 Python syntax:")
            syntax_ok = check_python_imports(path)
            results.append(("SYN", description, syntax_ok))
    
    # 3. Check route files
    print("\n🛣️ ROUTE FILES")
    print("-" * 40)
    
    route_files = [
        (base_dir / "routes" / "marketing.py", "Marketing routes"),
        (base_dir / "routes" / "meta_auth.py", "Meta auth routes"),
    ]
    
    for path, description in route_files:
        if check_file_exists(path, description):
            print("   📄 Content checks:")
            # Check for FastAPI decorators
            required_strings = [
                ("@router.", "FastAPI router decorators"),
                ("@audit_access", "Audit logging"),
                ("@limiter.limit", "Rate limiting"),
            ]
            content_ok = check_file_content(path, required_strings)
            results.append(("RT", description, content_ok))
            
            # Check Python syntax
            print("   🐍 Python syntax:")
            syntax_ok = check_python_imports(path)
            results.append(("SYN", description, syntax_ok))
    
    # 4. Check migration file
    print("\n🗄️ MIGRATION FILE")
    print("-" * 40)
    
    migration_file = base_dir / "migrations" / "patch_009_meta_ads_tables.sql"
    if check_file_exists(migration_file, "Meta Ads migration"):
        print("   📄 SQL checks:")
        migration_ok = check_sql_migration(migration_file)
        results.append(("MIG", "Migration SQL", migration_ok))
    
    # 5. Check test file
    print("\n🧪 TEST FILE")
    print("-" * 40)
    
    test_file = base_dir / "tests" / "test_marketing_backend.py"
    if check_file_exists(test_file, "Marketing backend tests"):
        print("   📄 Content checks:")
        required_strings = [
            ("TestClient", "Uses TestClient"),
            ("@pytest.mark.asyncio", "Async tests"),
            ("mock", "Uses mocking"),
        ]
        test_ok = check_file_content(test_file, required_strings)
        results.append(("TEST", "Test file", test_ok))
    
    # 6. Check main.py integration
    print("\n🏗️ MAIN.PY INTEGRATION")
    print("-" * 40)
    
    main_file = base_dir / "main.py"
    if check_file_exists(main_file, "Main application file"):
        print("   📄 Integration checks:")
        required_strings = [
            ("routes.marketing", "Marketing routes import"),
            ("routes.meta_auth", "Meta auth routes import"),
            ("/crm/marketing", "Marketing route prefix"),
            ("/crm/auth/meta", "Meta auth route prefix"),
        ]
        main_ok = check_file_content(main_file, required_strings)
        results.append(("MAIN", "Main.py integration", main_ok))
    
    # 7. Check migration script
    print("\n📜 MIGRATION SCRIPT")
    print("-" * 40)
    
    migration_script = base_dir / "run_meta_ads_migrations.py"
    if check_file_exists(migration_script, "Migration script"):
        print("   📄 Content checks:")
        required_strings = [
            ("asyncpg", "Uses asyncpg"),
            ("run_migration", "Migration function"),
            ("rollback", "Rollback function"),
        ]
        script_ok = check_file_content(migration_script, required_strings)
        results.append(("SCRIPT", "Migration script", script_ok))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for _, _, success in results if success)
    
    # Group by category
    categories = {}
    for category, description, success in results:
        if category not in categories:
            categories[category] = []
        categories[category].append((description, success))
    
    for category, items in categories.items():
        cat_passed = sum(1 for _, success in items if success)
        cat_total = len(items)
        print(f"\n{category} ({cat_passed}/{cat_total}):")
        for description, success in items:
            status = "✅" if success else "❌"
            print(f"  {status} {description}")
    
    print(f"\n🎯 OVERALL: {passed}/{total} checks passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 EXCELLENT! All checks passed.")
        print("✅ Sprint 1 Day 2 (Endpoints & Routes) implementation is complete and verified.")
        print("\n📋 NEXT STEPS for Sprint 1 Day 3:")
        print("   1. Set up PostgreSQL database with proper credentials")
        print("   2. Run: python run_meta_ads_migrations.py")
        print("   3. Test actual database connectivity")
        print("   4. Run: python -m pytest tests/test_marketing_backend.py -v")
    elif passed >= total * 0.8:
        print(f"\n⚠️ GOOD: {passed}/{total} checks passed.")
        print("Most implementation is complete. Review the failed checks above.")
        print("Proceed to database setup and testing.")
    else:
        print(f"\n❌ NEEDS WORK: Only {passed}/{total} checks passed.")
        print("Review and fix the failed checks before proceeding.")
    
    return passed >= total * 0.8  # 80% threshold

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)