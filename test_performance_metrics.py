#!/usr/bin/env python3
"""
Performance Testing Script
Test de carga y performance para el sistema de métricas y notificaciones
"""

import asyncio
import time
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List
import aiohttp
import json

# Configuración
BASE_URL = "http://localhost:8000"
TEST_TENANT_ID = 1
CONCURRENT_USERS = [1, 5, 10, 20, 50]  # Usuarios concurrentes a testear
REQUESTS_PER_USER = 10  # Requests por usuario

async def make_request(session, endpoint, method="GET", data=None):
    """Hacer una request HTTP y medir el tiempo"""
    start_time = time.time()
    
    try:
        if method == "GET":
            async with session.get(f"{BASE_URL}{endpoint}") as response:
                status = response.status
                response_time = time.time() - start_time
                return {
                    "success": 200 <= status < 300,
                    "status": status,
                    "response_time": response_time,
                    "error": None
                }
        elif method == "POST":
            async with session.post(f"{BASE_URL}{endpoint}", json=data) as response:
                status = response.status
                response_time = time.time() - start_time
                return {
                    "success": 200 <= status < 300,
                    "status": status,
                    "response_time": response_time,
                    "error": None
                }
    except Exception as e:
        return {
            "success": False,
            "status": 0,
            "response_time": time.time() - start_time,
            "error": str(e)
        }

async def test_endpoint_concurrent(endpoint, method="GET", data=None, concurrent_users=1):
    """Testear un endpoint con usuarios concurrentes"""
    print(f"\n🧪 Testing {endpoint} with {concurrent_users} concurrent users...")
    
    tasks = []
    async with aiohttp.ClientSession() as session:
        # Crear tasks para cada usuario
        for user_id in range(concurrent_users):
            for request_num in range(REQUESTS_PER_USER):
                task = make_request(session, endpoint, method, data)
                tasks.append(task)
        
        # Ejecutar todas las requests concurrentemente
        results = await asyncio.gather(*tasks)
    
    # Analizar resultados
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    response_times = [r["response_time"] for r in successful]
    
    if response_times:
        stats = {
            "total_requests": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) * 100,
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times),
            "requests_per_second": len(results) / (max(response_times) if response_times else 1)
        }
    else:
        stats = {
            "total_requests": len(results),
            "successful": 0,
            "failed": len(failed),
            "success_rate": 0,
            "avg_response_time": 0,
            "min_response_time": 0,
            "max_response_time": 0,
            "p95_response_time": 0,
            "requests_per_second": 0
        }
    
    return stats

async def test_metrics_endpoints():
    """Testear endpoints de métricas"""
    print("\n" + "="*60)
    print("📊 PERFORMANCE TESTING - METRICS ENDPOINTS")
    print("="*60)
    
    endpoints = [
        ("/admin/core/sellers/dashboard/overview?tenant_id=1", "GET"),
        ("/admin/core/sellers/available?tenant_id=1", "GET"),
        ("/admin/core/sellers/leaderboard?tenant_id=1", "GET"),
    ]
    
    all_results = {}
    
    for endpoint, method in endpoints:
        endpoint_results = {}
        
        for concurrent_users in CONCURRENT_USERS:
            stats = await test_endpoint_concurrent(
                endpoint=endpoint,
                method=method,
                concurrent_users=concurrent_users
            )
            
            endpoint_results[concurrent_users] = stats
            
            print(f"  {concurrent_users} users: {stats['success_rate']:.1f}% success, "
                  f"avg {stats['avg_response_time']*1000:.1f}ms, "
                  f"RPS: {stats['requests_per_second']:.1f}")
        
        all_results[endpoint] = endpoint_results
    
    return all_results

async def test_notification_endpoints():
    """Testear endpoints de notificaciones"""
    print("\n" + "="*60)
    print("🔔 PERFORMANCE TESTING - NOTIFICATION ENDPOINTS")
    print("="*60)
    
    endpoints = [
        ("/notifications/count", "GET"),
        ("/notifications?limit=20", "GET"),
    ]
    
    all_results = {}
    
    for endpoint, method in endpoints:
        endpoint_results = {}
        
        for concurrent_users in CONCURRENT_USERS[:3]:  # Menos usuarios para notificaciones
            stats = await test_endpoint_concurrent(
                endpoint=endpoint,
                method=method,
                concurrent_users=concurrent_users
            )
            
            endpoint_results[concurrent_users] = stats
            
            print(f"  {concurrent_users} users: {stats['success_rate']:.1f}% success, "
                  f"avg {stats['avg_response_time']*1000:.1f}ms, "
                  f"RPS: {stats['requests_per_second']:.1f}")
        
        all_results[endpoint] = endpoint_results
    
    return all_results

async def test_database_queries():
    """Testear queries de base de datos directamente"""
    print("\n" + "="*60)
    print("🗄️  PERFORMANCE TESTING - DATABASE QUERIES")
    print("="*60)
    
    # Este test requiere conexión a la base de datos
    # Por ahora solo mostramos métricas estimadas
    print("⚠️  Database query testing requires direct DB connection")
    print("   Estimated performance based on query complexity:")
    
    queries = [
        {"name": "Seller Metrics Calculation", "complexity": "High", "est_time_ms": 50},
        {"name": "Notification Checks", "complexity": "Medium", "est_time_ms": 30},
        {"name": "Conversation History", "complexity": "Low", "est_time_ms": 10},
        {"name": "Lead Statistics", "complexity": "Medium", "est_time_ms": 20},
    ]
    
    for query in queries:
        print(f"  {query['name']}: {query['complexity']} complexity, ~{query['est_time_ms']}ms")
    
    return {"note": "Direct DB testing not implemented in this script"}

async def test_concurrent_assignments():
    """Testear asignaciones concurrentes de vendedores"""
    print("\n" + "="*60)
    print("👥 PERFORMANCE TESTING - CONCURRENT ASSIGNMENTS")
    print("="*60)
    
    # Datos de prueba para asignación
    test_data = {
        "phone": f"+54911{random.randint(1000000, 9999999)}",
        "seller_id": "test-seller-id",
        "source": "manual"
    }
    
    endpoint = "/admin/core/sellers/conversations/assign"
    
    results = {}
    
    for concurrent_users in [1, 3, 5]:  # Pocos usuarios para operaciones de escritura
        print(f"\nTesting {endpoint} with {concurrent_users} concurrent assignments...")
        
        stats = await test_endpoint_concurrent(
            endpoint=endpoint,
            method="POST",
            data=test_data,
            concurrent_users=concurrent_users
        )
        
        results[concurrent_users] = stats
        
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        print(f"  Avg response time: {stats['avg_response_time']*1000:.1f}ms")
        print(f"  Requests per second: {stats['requests_per_second']:.1f}")
    
    return results

async def run_stress_test():
    """Ejecutar test de estrés completo"""
    print("\n" + "="*60)
    print("🚀 STRESS TEST - FULL SYSTEM LOAD")
    print("="*60)
    
    # Combinar todos los endpoints
    stress_endpoints = [
        "/admin/core/sellers/dashboard/overview?tenant_id=1",
        "/notifications/count",
        "/admin/core/sellers/available?tenant_id=1",
    ]
    
    print(f"Running stress test with {CONCURRENT_USERS[-1]} concurrent users...")
    
    start_time = time.time()
    
    tasks = []
    async with aiohttp.ClientSession() as session:
        for _ in range(CONCURRENT_USERS[-1] * 5):  # 5 requests por usuario
            endpoint = random.choice(stress_endpoints)
            task = make_request(session, endpoint)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    successful = [r for r in results if r["success"]]
    response_times = [r["response_time"] for r in successful]
    
    if response_times:
        stats = {
            "total_requests": len(results),
            "total_time": total_time,
            "requests_per_second": len(results) / total_time,
            "success_rate": len(successful) / len(results) * 100,
            "avg_response_time": statistics.mean(response_times),
            "max_response_time": max(response_times),
            "concurrent_users": CONCURRENT_USERS[-1]
        }
    else:
        stats = {
            "total_requests": len(results),
            "total_time": total_time,
            "requests_per_second": 0,
            "success_rate": 0,
            "avg_response_time": 0,
            "max_response_time": 0,
            "concurrent_users": CONCURRENT_USERS[-1]
        }
    
    print(f"\n📈 Stress Test Results:")
    print(f"  Total Requests: {stats['total_requests']}")
    print(f"  Total Time: {stats['total_time']:.2f}s")
    print(f"  Requests/Second: {stats['requests_per_second']:.1f}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")
    print(f"  Avg Response Time: {stats['avg_response_time']*1000:.1f}ms")
    print(f"  Max Response Time: {stats['max_response_time']*1000:.1f}ms")
    
    return stats

def generate_report(all_results):
    """Generar reporte de testing"""
    print("\n" + "="*60)
    print("📋 PERFORMANCE TESTING REPORT")
    print("="*60)
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "tests": all_results,
        "recommendations": []
    }
    
    # Analizar resultados y generar recomendaciones
    for test_name, results in all_results.items():
        if isinstance(results, dict) and "metrics" in str(test_name).lower():
            # Analizar métricas
            worst_case = None
            for concurrency, stats in results.items():
                if isinstance(stats, dict):
                    if stats.get("avg_response_time", 0) > 1.0:  # > 1 segundo
                        report["recommendations"].append(
                            f"Optimize {test_name}: Response time >1s with {concurrency} users"
                        )
                    if stats.get("success_rate", 100) < 95:  # < 95% success
                        report["recommendations"].append(
                            f"Improve reliability of {test_name}: Success rate {stats.get('success_rate', 0):.1f}% with {concurrency} users"
                        )
    
    # Recomendaciones generales
    if not report["recommendations"]:
        report["recommendations"].append("System performance is within acceptable limits")
    
    # Agregar recomendaciones de optimización
    report["recommendations"].append("Consider implementing Redis cache for frequently accessed metrics")
    report["recommendations"].append("Add database indexes for seller_metrics and notifications tables")
    report["recommendations"].append("Implement query optimization for complex metric calculations")
    
    print("\n✅ TESTING COMPLETED")
    print("\n📝 RECOMMENDATIONS:")
    for rec in report["recommendations"]:
        print(f"  • {rec}")
    
    # Guardar reporte
    with open("performance_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Report saved to: performance_test_report.json")

async def main():
    """Función principal"""
    print("🚀 STARTING PERFORMANCE TESTING SUITE")
    print(f"Base URL: {BASE_URL}")
    print(f"Test Tenant ID: {TEST_TENANT_ID}")
    
    all_results = {}
    
    try:
        # 1. Test endpoints de métricas
        metrics_results = await test_metrics_endpoints()
        all_results["metrics_endpoints"] = metrics_results
        
        # 2. Test endpoints de notificaciones
        notification_results = await test_notification_endpoints()
        all_results["notification_endpoints"] = notification_results
        
        # 3. Test de queries de base de datos
        db_results = await test_database_queries()
        all_results["database_queries"] = db_results
        
        # 4. Test de asignaciones concurrentes
        assignment_results = await test_concurrent_assignments()
        all_results["concurrent_assignments"] = assignment_results
        
        # 5. Test de estrés
        stress_results = await run_stress_test()
        all_results["stress_test"] = stress_results
        
        # 6. Generar reporte
        generate_report(all_results)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())