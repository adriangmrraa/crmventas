#!/usr/bin/env python3
"""
Query Optimization Script
Analizar y optimizar queries de base de datos para el sistema de métricas
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

# Configuración de base de datos (simulada para análisis)
# En producción, esto se conectaría a la DB real

class QueryAnalyzer:
    """Analizador de queries para identificar optimizaciones"""
    
    def __init__(self):
        self.queries = []
        self.recommendations = []
    
    def add_query(self, query: str, execution_time: float, rows_returned: int):
        """Agregar query para análisis"""
        self.queries.append({
            "query": query,
            "execution_time": execution_time,
            "rows_returned": rows_returned,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def analyze_seller_metrics_queries(self):
        """Analizar queries del sistema de métricas de vendedores"""
        print("\n" + "="*60)
        print("📊 ANALYZING SELLER METRICS QUERIES")
        print("="*60)
        
        # Queries comunes del sistema de métricas
        common_queries = [
            {
                "name": "Cálculo de métricas por vendedor",
                "query": """
                    SELECT 
                        seller_id,
                        COUNT(DISTINCT conversation_id) as total_conversations,
                        COUNT(DISTINCT CASE WHEN created_at > NOW() - INTERVAL '24 hours' THEN conversation_id END) as today_conversations,
                        COUNT(DISTINCT lead_id) as leads_assigned,
                        COUNT(DISTINCT CASE WHEN lead_status = 'cerrado_ganado' THEN lead_id END) as leads_converted,
                        AVG(response_time_seconds) as avg_response_time
                    FROM seller_activity
                    WHERE tenant_id = ?
                        AND created_at > NOW() - INTERVAL '7 days'
                    GROUP BY seller_id
                """,
                "issues": ["Full table scan", "No index on created_at", "Complex aggregation"]
            },
            {
                "name": "Dashboard overview para CEO",
                "query": """
                    SELECT 
                        COUNT(DISTINCT seller_id) as active_sellers,
                        SUM(total_conversations) as total_conversations,
                        SUM(leads_converted) as leads_converted_today,
                        AVG(avg_response_time_seconds) as avg_response_time
                    FROM seller_metrics
                    WHERE tenant_id = ?
                        AND metrics_period_start >= DATE_TRUNC('day', NOW())
                """,
                "issues": ["Missing composite index on (tenant_id, metrics_period_start)"]
            },
            {
                "name": "Leaderboard de performance",
                "query": """
                    SELECT 
                        seller_id,
                        conversion_rate,
                        total_conversations,
                        avg_response_time_seconds
                    FROM seller_metrics
                    WHERE tenant_id = ?
                        AND metrics_period_start >= NOW() - INTERVAL '30 days'
                    ORDER BY conversion_rate DESC
                    LIMIT 10
                """,
                "issues": ["Sorting on large dataset", "No index on conversion_rate"]
            }
        ]
        
        for query_info in common_queries:
            print(f"\n🔍 {query_info['name']}:")
            print(f"   Query: {query_info['query'].strip()[:100]}...")
            print(f"   Issues: {', '.join(query_info['issues'])}")
            
            # Generar recomendaciones
            recommendations = self._generate_recommendations(query_info)
            for rec in recommendations:
                self.recommendations.append(rec)
                print(f"   💡 {rec}")
    
    def analyze_notification_queries(self):
        """Analizar queries del sistema de notificaciones"""
        print("\n" + "="*60)
        print("🔔 ANALYZING NOTIFICATION QUERIES")
        print("="*60)
        
        notification_queries = [
            {
                "name": "Detección de conversaciones sin respuesta",
                "query": """
                    SELECT 
                        conversation_id,
                        from_number,
                        assigned_seller_id,
                        MAX(created_at) as last_message_time
                    FROM chat_messages
                    WHERE tenant_id = ?
                        AND assigned_seller_id IS NOT NULL
                        AND created_at > NOW() - INTERVAL '24 hours'
                    GROUP BY conversation_id, from_number, assigned_seller_id
                    HAVING MAX(created_at) < NOW() - INTERVAL '1 hour'
                """,
                "issues": ["Group by on multiple columns", "No index on (tenant_id, assigned_seller_id, created_at)"]
            },
            {
                "name": "Detección de leads calientes",
                "query": """
                    WITH lead_engagement AS (
                        SELECT 
                            lead_id,
                            phone_number,
                            COUNT(message_id) as message_count,
                            MAX(created_at) as last_interaction
                        FROM chat_messages
                        WHERE tenant_id = ?
                            AND created_at > NOW() - INTERVAL '24 hours'
                        GROUP BY lead_id, phone_number
                    )
                    SELECT * FROM lead_engagement
                    WHERE message_count >= 3
                        AND last_interaction > NOW() - INTERVAL '2 hours'
                """,
                "issues": ["CTE overhead", "No index on created_at for time-based queries"]
            },
            {
                "name": "Obtención de notificaciones por usuario",
                "query": """
                    SELECT 
                        id, type, title, message, priority, read,
                        created_at, expires_at
                    FROM notifications
                    WHERE recipient_id = ?
                        AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY 
                        CASE priority
                            WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                        END,
                        created_at DESC
                    LIMIT 50
                """,
                "issues": ["Complex ORDER BY", "No composite index on (recipient_id, priority, created_at)"]
            }
        ]
        
        for query_info in notification_queries:
            print(f"\n🔍 {query_info['name']}:")
            print(f"   Query: {query_info['query'].strip()[:100]}...")
            print(f"   Issues: {', '.join(query_info['issues'])}")
            
            recommendations = self._generate_recommendations(query_info)
            for rec in recommendations:
                self.recommendations.append(rec)
                print(f"   💡 {rec}")
    
    def _generate_recommendations(self, query_info: Dict) -> List[str]:
        """Generar recomendaciones de optimización para una query"""
        recommendations = []
        query = query_info["query"].lower()
        issues = query_info.get("issues", [])
        
        # Recomendaciones basadas en issues
        for issue in issues:
            if "index" in issue.lower():
                if "created_at" in query:
                    recommendations.append(f"Add index on created_at column for time-based queries")
                if "tenant_id" in query and "assigned_seller_id" in query:
                    recommendations.append(f"Add composite index on (tenant_id, assigned_seller_id, created_at)")
                if "recipient_id" in query and "priority" in query:
                    recommendations.append(f"Add composite index on (recipient_id, priority, created_at) DESC")
            
            if "full table scan" in issue.lower():
                recommendations.append(f"Add WHERE clause conditions to limit scanned rows")
            
            if "complex aggregation" in issue.lower():
                recommendations.append(f"Consider materialized views for aggregated metrics")
            
            if "cte overhead" in issue.lower():
                recommendations.append(f"Rewrite CTE as subquery or temporary table")
        
        # Recomendaciones generales
        if "count(distinct" in query:
            recommendations.append(f"Consider approximate counting for large datasets")
        
        if "order by" in query and "limit" in query:
            recommendations.append(f"Ensure ORDER BY uses indexed columns")
        
        if "group by" in query and len([c for c in query.split() if c == "group"]) > 1:
            recommendations.append(f"Reduce GROUP BY columns or add composite index")
        
        return recommendations
    
    def generate_index_recommendations(self):
        """Generar recomendaciones de índices específicos"""
        print("\n" + "="*60)
        print("📈 INDEX OPTIMIZATION RECOMMENDATIONS")
        print("="*60)
        
        index_recommendations = [
            {
                "table": "seller_metrics",
                "index": "idx_seller_metrics_tenant_period",
                "columns": ["tenant_id", "metrics_period_start"],
                "type": "BTREE",
                "reason": "Optimize dashboard and period-based queries"
            },
            {
                "table": "seller_metrics",
                "index": "idx_seller_metrics_seller_period",
                "columns": ["seller_id", "metrics_period_start DESC"],
                "type": "BTREE",
                "reason": "Optimize seller-specific metric queries"
            },
            {
                "table": "chat_messages",
                "index": "idx_chat_messages_tenant_seller_time",
                "columns": ["tenant_id", "assigned_seller_id", "created_at DESC"],
                "type": "BTREE",
                "reason": "Optimize conversation history and notification queries"
            },
            {
                "table": "notifications",
                "index": "idx_notifications_recipient_priority_time",
                "columns": ["recipient_id", "priority", "created_at DESC"],
                "type": "BTREE",
                "reason": "Optimize notification retrieval and sorting"
            },
            {
                "table": "notifications",
                "index": "idx_notifications_expires",
                "columns": ["expires_at"],
                "type": "BTREE",
                "where": "expires_at IS NOT NULL",
                "reason": "Optimize cleanup of expired notifications"
            },
            {
                "table": "leads",
                "index": "idx_leads_tenant_status_time",
                "columns": ["tenant_id", "status", "created_at DESC"],
                "type": "BTREE",
                "reason": "Optimize lead filtering and reporting"
            }
        ]
        
        print("\nRecommended Indexes:")
        for idx in index_recommendations:
            print(f"\n📌 {idx['table']}.{idx['index']}:")
            print(f"   Columns: {', '.join(idx['columns'])}")
            print(f"   Type: {idx['type']}")
            if idx.get('where'):
                print(f"   WHERE: {idx['where']}")
            print(f"   Reason: {idx['reason']}")
            
            # Agregar a recomendaciones generales
            self.recommendations.append(
                f"Create index {idx['index']} on {idx['table']}({', '.join(idx['columns'])})"
            )
    
    def generate_query_rewrite_suggestions(self):
        """Generar sugerencias para reescribir queries"""
        print("\n" + "="*60)
        print("🔄 QUERY REWRITE SUGGESTIONS")
        print("="*60)
        
        suggestions = [
            {
                "original": "COUNT(DISTINCT column) in large tables",
                "suggestion": "Use approximate count with HyperLogLog or materialized counters",
                "benefit": "10-100x faster for large datasets"
            },
            {
                "original": "Complex CTEs with multiple aggregations",
                "suggestion": "Break into temporary tables or materialized views",
                "benefit": "Better query planning and caching"
            },
            {
                "original": "ORDER BY with LIMIT on unindexed columns",
                "suggestion": "Add appropriate indexes or use different sorting strategy",
                "benefit": "Avoid full table scans for sorting"
            },
            {
                "original": "Frequent metric calculations on-the-fly",
                "suggestion": "Implement incremental metric updates with triggers",
                "benefit": "Constant time metric retrieval"
            },
            {
                "original": "Time-based range queries without partitions",
                "suggestion": "Implement table partitioning by date",
                "benefit": "Faster data pruning and maintenance"
            }
        ]
        
        for suggestion in suggestions:
            print(f"\n📝 {suggestion['original']}:")
            print(f"   → {suggestion['suggestion']}")
            print(f"   Benefit: {suggestion['benefit']}")
    
    def generate_caching_recommendations(self):
        """Generar recomendaciones de caching"""
        print("\n" + "="*60)
        print("💾 CACHING RECOMMENDATIONS")
        print("="*60)
        
        caching_strategies = [
            {
                "data": "Seller metrics for today",
                "strategy": "Redis cache with 5-minute TTL",
                "key_pattern": "metrics:tenant:{tenant_id}:seller:{seller_id}:today",
                "benefit": "Reduce database load for frequently accessed metrics"
            },
            {
                "data": "Notification counts per user",
                "strategy": "Redis cache with 1-minute TTL",
                "key_pattern": "notifications:count:user:{user_id}",
                "benefit": "Fast badge updates without DB queries"
            },
            {
                "data": "Leaderboard data",
                "strategy": "Redis cache with 15-minute TTL",
                "key_pattern": "leaderboard:tenant:{tenant_id}:period:{period}",
                "benefit": "Reduce complex aggregation queries"
            },
            {
                "data": "User notification settings",
                "strategy": "Redis cache with 1-hour TTL",
                "key_pattern": "settings:notifications:user:{user_id}",
                "benefit": "Fast access to user preferences"
            }
        ]
        
        print("\nRecommended Caching Strategies:")
        for cache in caching_strategies:
            print(f"\n🔑 {cache['data']}:")
            print(f"   Strategy: {cache['strategy']}")
            print(f"   Key: {cache['key_pattern']}")
            print(f"   Benefit: {cache['benefit']}")
            
            self.recommendations.append(
                f"Implement {cache['strategy']} for {cache['data']}"
            )
    
    def generate_performance_targets(self):
        """Generar objetivos de performance"""
        print("\n" + "="*60)
        print("🎯 PERFORMANCE TARGETS")
        print("="*60)
        
        targets = [
            {"metric": "Dashboard load time", "target": "< 500ms", "current": "~800ms (estimated)"},
            {"metric": "Notification checks", "target": "< 100ms per tenant", "current": "~200ms (estimated)"},
            {"metric": "Metrics calculation", "target": "< 50ms per seller", "current": "~100ms (estimated)"},
            {"metric": "API response time (p95)", "target": "< 200ms", "current": "~400ms (estimated)"},
            {"metric": "Database query time (worst)", "target": "< 1000ms", "current": "~2000ms (complex queries)"},
        ]
        
        print("\nPerformance Targets vs Current State:")
        for target in targets:
            status = "⚠️ " if ">" in target["current"] else "✅ "
            print(f"\n{status} {target['metric']}:")
            print(f"   Target: {target['target']}")
            print(f"   Current: {target['current']}")
    
    def generate_implementation_plan(self):
        """Generar plan de implementación priorizado"""
        print("\n" + "="*60)
        print("📅 IMPLEMENTATION PLAN (PRIORITIZED)")
        print("="*60)
        
        plan = [
            {
                "priority": "P0 - Critical",
                "tasks": [
                    "Add composite indexes on seller_metrics(tenant_id, metrics_period_start)",
                    "Add index on chat_messages(tenant_id, assigned_seller_id, created_at)",
                    "Implement Redis cache for notification counts"
                ],
                "estimated_effort": "2-3 days",
                "expected_improvement": "50-70% faster dashboard"
            },
            {
                "priority": "P1 - High",
                "tasks": [
                    "Add index on notifications(recipient_id, priority, created_at)",
                    "Implement materialized views for daily metrics",
                    "Add query timeouts for long-running operations"
                ],
                "estimated_effort": "3-4 days",
                "expected_improvement": "30-50% faster notifications"
            },
            {
                "priority": "P2 - Medium",
                "tasks": [
                    "Implement table partitioning for chat_messages by date",
                    "Add database connection pooling",
                    "Implement query result caching"
                ],
                "estimated_effort": "5-7 days",
                "expected_improvement": "20-40% better scalability"
            },
            {
                "priority": "P3 - Low",
                "tasks": [
                    "Implement advanced query monitoring",
                    "Add database read replicas",
                    "Implement automatic query optimization"
                ],
                "estimated_effort": "7-10 days",
                "expected_improvement": "10-20% incremental gains"
            }
        ]
        
        for phase in plan:
            print(f"\n{phase['priority']}:")
            print(f"   Effort: {phase['estimated_effort']}")
            print(f"   Expected Improvement: {phase['expected_improvement']}")
            print(f"   Tasks:")
            for task in phase['tasks']:
                print(f"     • {task}")
    
    def save_report(self):
        """Guardar reporte de optimización"""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_queries_analyzed": len(self.queries),
            "recommendations": self.recommendations,
            "summary": f"Generated {len(self.recommendations)} optimization recommendations"
        }
        
        with open("query_optimization_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved to: query_optimization_report.json")
        print(f"   Total recommendations: {len(self.recommendations)}")

async def main():
    """Función principal"""
    print("🔧 QUERY OPTIMIZATION ANALYSIS TOOL")
    print("="*60)
    
    analyzer = QueryAnalyzer()
    
    # Ejecutar análisis
    analyzer.analyze_seller_metrics_queries()
    analyzer.analyze_notification_queries()
    analyzer.generate_index_recommendations()
    analyzer.generate_query_rewrite_suggestions()
    analyzer.generate_caching_recommendations()
    analyzer.generate_performance_targets()
    analyzer.generate_implementation_plan()
    
    # Guardar reporte
    analyzer.save_report()
    
    print("\n" + "="*60)
    print("✅ ANALYSIS COMPLETED")
    print("="*60)
    print("\nNext steps:")
    print("1. Review the optimization recommendations")
    print("2. Implement P0 and P1 priorities first")
    print("3. Monitor performance after each change")
    print("4. Run performance tests to validate improvements")

if __name__ == "__main__":
    asyncio.run(main())
