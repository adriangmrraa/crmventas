# 📊 Guía Completa del Dashboard CEO - Sprint 2

## 📋 **INTRODUCCIÓN**

El **Dashboard CEO** es el centro de control del **Sprint 2 - Tracking Avanzado**, proporcionando visibilidad completa y en tiempo real sobre el equipo de ventas, métricas de performance, y analytics avanzados para toma de decisiones estratégicas.

### **🎯 BENEFICIOS PRINCIPALES:**

1. **✅ Visibilidad 360°** - Todo el equipo de ventas en un solo lugar
2. **✅ Tiempo real** - Métricas actualizadas cada 15 minutos con Redis cache
3. **✅ Analytics avanzados** - 15+ métricas por vendedor y equipo
4. **✅ Leaderboard inteligente** - Ranking automático por performance
5. **✅ Alertas proactivas** - Notificaciones de problemas antes de que escalen
6. **✅ Exportación completa** - Reportes CSV/PDF para análisis externo

---

## 🏗️ **ARQUITECTURA DEL DASHBOARD**

### **📊 DIAGRAMA DE ARQUITECTURA:**

```
Data Sources
├── PostgreSQL (Conversaciones, Leads, Asignaciones)
├── Redis Cache (Métricas en tiempo real)
└── Background Jobs (Actualización automática)

        |
        v
SellerMetricsService
├── Cálculo 15+ métricas
├── Redis caching (5 min TTL)
└── Socket.IO updates

        |
        v
API Endpoints
├── GET /admin/core/sellers/metrics
├── GET /admin/core/sellers/leaderboard
├── GET /admin/core/sellers/dashboard
└── GET /admin/core/sellers/export

        |
        v
Frontend Dashboard
├── Gráficos en tiempo real (Chart.js)
├── Leaderboard ranking
├── Filtros por fecha/tenant
└── Exportación CSV/PDF
```

### **🔧 COMPONENTES PRINCIPALES:**

#### **1. Backend - SellerMetricsService (`services/seller_metrics_service.py`)**
```python
class SellerMetricsService:
    """Servicio principal para cálculo de métricas de vendedores"""
    
    def __init__(self):
        self.redis_client = None
        self.cache_ttl = 300  # 5 minutos
        
    async def calculate_seller_metrics(self, seller_id: int, period: str = 'daily'):
        """Calcula 15+ métricas para un vendedor"""
        metrics = {
            # Conversaciones
            'conversations_total': await self.get_total_conversations(seller_id, period),
            'conversations_active': await self.get_active_conversations(seller_id),
            'conversations_today': await get_today_conversations(seller_id),
            'conversations_unanswered': await get_unanswered_conversations(seller_id),
            
            # Tiempos
            'avg_response_time_minutes': await self.get_avg_response_time(seller_id, period),
            'total_chat_time_minutes': await self.get_total_chat_time(seller_id, period),
            'first_response_time_minutes': await self.get_first_response_time(seller_id, period),
            
            # Conversiones
            'leads_generated': await self.get_leads_generated(seller_id, period),
            'leads_converted': await self.get_leads_converted(seller_id, period),
            'conversion_rate': await self.get_conversion_rate(seller_id, period),
            'estimated_revenue': await self.get_estimated_revenue(seller_id, period),
            
            # Performance
            'productivity_score': await self.calculate_productivity_score(seller_id, period),
            'engagement_rate': await self.calculate_engagement_rate(seller_id, period),
            'activity_level': await self.determine_activity_level(seller_id, period),
            
            # Team comparison
            'team_rank': await self.get_team_rank(seller_id, period),
            'percentile': await self.get_percentile(seller_id, period),
            'improvement_trend': await self.get_improvement_trend(seller_id)
        }
        
        # Cache en Redis
        await self.cache_metrics(seller_id, period, metrics)
        
        return metrics
```

#### **2. Frontend - SellerMetricsDashboard (`components/SellerMetricsDashboard.tsx`)**
```typescript
// Dashboard principal del CEO
const SellerMetricsDashboard: React.FC = () => {
  const [timeRange, setTimeRange] = useState<'today' | 'week' | 'month' | 'custom'>('today');
  const [selectedSeller, setSelectedSeller] = useState<string | 'all'>('all');
  const [metrics, setMetrics] = useState<TeamMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Socket.IO para updates en tiempo real
  const { socketConnected } = useSocket();
  
  // Fetch metrics on mount and when filters change
  useEffect(() => {
    fetchMetrics();
  }, [timeRange, selectedSeller]);
  
  // Socket.IO listener para updates
  useEffect(() => {
    if (!socket) return;
    
    socket.on('metrics_updated', (data) => {
      if (data.seller_id === selectedSeller || selectedSeller === 'all') {
        setMetrics(data.metrics);
      }
    });
    
    return () => {
      socket.off('metrics_updated');
    };
  }, [socket, selectedSeller]);
  
  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const response = await api.get('/admin/core/sellers/dashboard', {
        params: {
          period: timeRange,
          seller_id: selectedSeller !== 'all' ? selectedSeller : undefined
        }
      });
      setMetrics(response.data);
    } catch (error) {
      console.error('Error fetching metrics:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="p-6">
      {/* Header con filtros */}
      <DashboardHeader
        timeRange={timeRange}
        onTimeRangeChange={setTimeRange}
        selectedSeller={selectedSeller}
        onSellerChange={setSelectedSeller}
        lastUpdated={metrics?.last_updated}
        connectionStatus={socketConnected ? 'live' : 'cached'}
      />
      
      {/* KPI Cards */}
      {metrics && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <KPICard
              title="Conversaciones Activas"
              value={metrics.team.conversations_active}
              change={metrics.team.conversations_active_change}
              icon={<MessageSquare className="w-5 h-5" />}
              color="blue"
            />
            <KPICard
              title="Leads Convertidos"
              value={metrics.team.leads_converted}
              change={metrics.team.leads_converted_change}
              icon={<Users className="w-5 h-5" />}
              color="green"
            />
            <KPICard
              title="Tiempo Respuesta Prom."
              value={`${metrics.team.avg_response_time_minutes}m`}
              change={-metrics.team.avg_response_time_change}
              icon={<Clock className="w-5 h-5" />}
              color="orange"
              lowerIsBetter
            />
            <KPICard
              title="Tasa Conversión"
              value={`${(metrics.team.conversion_rate * 100).toFixed(1)}%`}
              change={metrics.team.conversion_rate_change * 100}
              icon={<TrendingUp className="w-5 h-5" />}
              color="purple"
            />
          </div>
          
          {/* Gráficos y leaderboard */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <PerformanceChart
                data={metrics.performance_trend}
                timeRange={timeRange}
              />
            </div>
            <div>
              <Leaderboard
                sellers={metrics.leaderboard}
                selectedSeller={selectedSeller}
                onSelectSeller={setSelectedSeller}
              />
            </div>
          </div>
          
          {/* Tabla detallada */}
          <div className="mt-8">
            <SellerMetricsTable
              sellers={metrics.sellers}
              selectedSeller={selectedSeller}
              onSelectSeller={setSelectedSeller}
            />
          </div>
        </>
      )}
    </div>
  );
};
```

---

## 📈 **MÉTRICAS Y KPI's**

### **1. 📞 MÉTRICAS DE CONVERSACIÓN**

#### **Conversaciones Totales:**
```python
async def get_total_conversations(seller_id: int, period: str) -> int:
    """Total de conversaciones asignadas en el período"""
    query = """
        SELECT COUNT(*) as total
        FROM conversations
        WHERE assigned_seller_id = $1
        AND created_at >= $2
    """
    
    period_start = get_period_start(period)
    result = await db.fetchval(query, seller_id, period_start)
    return result or 0
```

#### **Conversaciones Activas:**
```python
async def get_active_conversations(seller_id: int) -> int:
    """Conversaciones con actividad en las últimas 24 horas"""
    query = """
        SELECT COUNT(DISTINCT conversation_id) as active
        FROM messages
        WHERE sender_id = $1
        AND created_at >= NOW() - INTERVAL '24 hours'
        AND conversation_id IN (
            SELECT id FROM conversations 
            WHERE assigned_seller_id = $1
            AND status = 'active'
        )
    """
    return await db.fetchval(query, seller_id) or 0
```

#### **Tiempo Promedio de Respuesta:**
```python
async def get_avg_response_time(seller_id: int, period: str) -> float:
    """Tiempo promedio de respuesta en minutos"""
    query = """
        SELECT AVG(
            EXTRACT(EPOCH FROM (m2.created_at - m1.created_at)) / 60
        ) as avg_response_minutes
        FROM messages m1
        JOIN messages m2 ON m1.conversation_id = m2.conversation_id
        WHERE m1.sender_role = 'customer'
        AND m2.sender_id = $1
        AND m2.created_at > m1.created_at
        AND m2.created_at <= m1.created_at + INTERVAL '24 hours'
        AND m1.created_at >= $2
        AND NOT EXISTS (
            SELECT 1 FROM messages m3
            WHERE m3.conversation_id = m1.conversation_id
            AND m3.sender_id = $1
            AND m3.created_at > m1.created_at
            AND m3.created_at < m2.created_at
        )
    """
    
    period_start = get_period_start(period)
    result = await db.fetchval(query, seller_id, period_start)
    return round(result or 0, 1)
```

### **2. 💰 MÉTRICAS DE CONVERSIÓN**

#### **Leads Generados:**
```python
async def get_leads_generated(seller_id: int, period: str) -> int:
    """Total de leads generados desde conversaciones"""
    query = """
        SELECT COUNT(DISTINCT l.id) as leads_generated
        FROM leads l
        JOIN conversations c ON l.conversation_id = c.id
        WHERE c.assigned_seller_id = $1
        AND l.created_at >= $2
    """
    
    period_start = get_period_start(period)
    return await db.fetchval(query, seller_id, period_start) or 0
```

#### **Tasa de Conversión:**
```python
async def get_conversion_rate(seller_id: int, period: str) -> float:
    """Porcentaje de leads que se convirtieron en ventas"""
    leads_generated = await get_leads_generated(seller_id, period)
    
    if leads_generated == 0:
        return 0.0
    
    query = """
        SELECT COUNT(DISTINCT l.id) as leads_converted
        FROM leads l
        JOIN conversations c ON l.conversation_id = c.id
        WHERE c.assigned_seller_id = $1
        AND l.created_at >= $2
        AND l.status = 'closed_won'
    """
    
    period_start = get_period_start(period)
    leads_converted = await db.fetchval(query, seller_id, period_start) or 0
    
    return round(leads_converted / leads_generated, 3)
```

#### **Ingreso Estimado:**
```python
async def get_estimated_revenue(seller_id: int, period: str) -> float:
    """Ingreso estimado basado en leads convertidos"""
    query = """
        SELECT COALESCE(SUM(
            CASE 
                WHEN l.estimated_value IS NOT NULL THEN l.estimated_value
                WHEN l.product_value IS NOT NULL THEN l.product_value
                ELSE 1000  -- Valor promedio por defecto
            END
        ), 0) as estimated_revenue
        FROM leads l
        JOIN conversations c ON l.conversation_id = c.id
        WHERE c.assigned_seller_id = $1
        AND l.created_at >= $2
        AND l.status = 'closed_won'
    """
    
    period_start = get_period_start(period)
    result = await db.fetchval(query, seller_id, period_start)
    return round(result or 0, 2)
```

### **3. 🏆 MÉTRICAS DE PERFORMANCE**

#### **Score de Productividad:**
```python
async def calculate_productivity_score(seller_id: int, period: str) -> float:
    """Score compuesto de 0-10 basado en múltiples métricas"""
    metrics = await self.calculate_seller_metrics(seller_id, period)
    
    # Ponderación de métricas
    weights = {
        'conversion_rate': 0.3,
        'avg_response_time_minutes': 0.25,
        'leads_converted': 0.2,
        'engagement_rate': 0.15,
        'conversations_active': 0.1
    }
    
    # Normalizar cada métrica a 0-1
    normalized_metrics = {
        'conversion_rate': min(metrics['conversion_rate'] * 10, 1.0),
        'avg_response_time_minutes': 1.0 - min(metrics['avg_response_time_minutes'] / 60, 1.0),
        'leads_converted': min(metrics['leads_converted'] / 20, 1.0),
        'engagement_rate': metrics['engagement_rate'],
        'conversations_active': min(metrics['conversations_active'] / 10, 1.0)
    }
    
    # Calcular score ponderado
    score = sum(
        normalized_metrics[metric] * weight
        for metric, weight in weights.items()
    )
    
    return round(score * 10, 1)  # Escalar a 0-10
```

#### **Nivel de Actividad:**
```python
async def determine_activity_level(seller_id: int, period: str) -> str:
    """Determina nivel de actividad basado en métricas"""
    metrics = await self.calculate_seller_metrics(seller_id, period)
    
    score = metrics['productivity_score']
    
    if score >= 8.0:
        return 'excelente'
    elif score >= 6.0:
        return 'alto'
    elif score >= 4.0:
        return 'medio'
    elif score >= 2.0:
        return 'bajo'
    else:
        return 'crítico'
```

#### **Ranking en Equipo:**
```python
async def get_team_rank(seller_id: int, period: str) -> int:
    """Posición del vendedor en el ranking del equipo"""
    query = """
        WITH seller_scores AS (
            SELECT 
                assigned_seller_id as seller_id,
                COUNT(DISTINCT CASE WHEN l.status = 'closed_won' THEN l.id END) as conversions,
                AVG(
                    CASE WHEN m.sender_role = 'customer' THEN
                        EXTRACT(EPOCH FROM (
                            SELECT MIN(created_at) 
                            FROM messages m2 
                            WHERE m2.conversation_id = m.conversation_id
                            AND m2.sender_id = conversations.assigned_seller_id
                            AND m2.created_at > m.created_at
                        ) - m.created_at) / 60
                    END
                ) as avg_response_time
            FROM conversations
            LEFT JOIN leads l ON conversations.id = l.conversation_id
            LEFT JOIN messages m ON conversations.id = m.conversation_id
            WHERE conversations.assigned_seller_id IS NOT NULL
            AND conversations.created_at >= $1
            GROUP BY assigned_seller_id
        ),
        ranked_sellers AS (
            SELECT 
                seller_id,
                ROW_NUMBER() OVER (
                    ORDER BY 
                        conversions DESC,
                        avg_response_time ASC
                ) as rank
            FROM seller_scores
        )
        SELECT rank
        FROM ranked_sellers
        WHERE seller_id = $2
    """
    
    period_start = get_period_start(period)
    result = await db.fetchval(query, period_start, seller_id)
    return result or 0
```

---

## 📊 **COMPONENTES DEL DASHBOARD**

### **1. 🎯 KPI CARDS**

```typescript
// Componente de tarjeta KPI
interface KPICardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'orange' | 'purple' | 'red';
  lowerIsBetter?: boolean;
}

const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  change,
  icon,
  color,
  lowerIsBetter = false
}) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    green: 'bg-green-50 text-green-700 border-green-200',
    orange: 'bg-orange-50 text-orange-700 border-orange-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
    red: 'bg-red-50 text-red-700 border-red-200'
  };
  
  const iconClasses = {
    blue: 'text-blue-600',
    green: 'text-green-600',
    orange: 'text-orange-600',
    purple: 'text-purple-600',
    red: 'text-red-600'
  };
  
  const getChangeColor = (changeValue?: number) => {
    if (!changeValue) return 'text-gray-500';
    
    const isPositive = lowerIsBetter ? changeValue <= 0 : changeValue >= 0;
    return isPositive ? 'text-green-600' : 'text-red-600';
  };
  
  const getChangeIcon = (changeValue?: number) => {
    if (!changeValue) return null;
    
    const isPositive = lowerIsBetter ? changeValue <= 0 : changeValue >= 0;
    return isPositive ? (
      <TrendingUp className="w-4 h-4" />
    ) : (
      <TrendingDown className="w-4 h-4" />
    );
  };
  
  const formatChange = (changeValue?: number) => {
    if (!changeValue) return '';
    
    const sign = changeValue > 0 ? '+' : '';
    return `${sign}${changeValue.toFixed(1)}%`;
  };
  
  return (
    <div className={`p-6 rounded-lg border ${colorClasses[color]}`}>
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className={`p-2 rounded-full ${iconClasses[color]}`}>
              {icon}
            </div>
            <span className="text-sm font-medium">{title}</span>
          </div>
          <div className="text-3xl font-bold">{value}</div>
        </div>
        
        {change !== undefined && (
          <div className={`flex items-center gap-1 ${getChangeColor(change)}`}>
            {getChangeIcon(change)}
            <span className="text-sm font-medium">{formatChange(change)}</span>
          </div>
        )}
      </div>
      
      {/* Progress bar for productivity score */}
      {title.includes('Score') && typeof value === 'number' && (
        <div className="mt-4">
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className={`h-full ${colorClasses[color].split(' ')[0]}`}
              style={{ width: `${(value / 10) * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>0</span>
            <span>5</span>
            <span>10</span>
          </div>
        </div>
      )}
    </div>
  );
};
```

### **2. 📈 PERFORMANCE CHART**

```typescript
// Gráfico de performance con Chart.js
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface PerformanceChartProps {
  data: {
    dates: string[];
    conversions: number[];
    responseTimes: number[];
    activity: number[];
  };
  timeRange: 'today' | 'week' | 'month' | 'custom';
}

const PerformanceChart: React.FC<PerformanceChartProps> = ({ data, timeRange }) => {
  const chartData = {
    labels: data.dates,
    datasets: [
      {
        label: 'Conversiones',
        data: data.conversions,
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        fill: true,
        tension: 0.4,
        yAxisID: 'y'
      },
      {
        label: 'Tiempo Respuesta (min)',
        data: data.responseTimes,
        borderColor: 'rgb(249, 115, 22)',
        backgroundColor: 'rgba(249, 115, 22, 0.1)',
        fill: true,
        tension: 0.4,
        yAxisID: 'y1'
      },
      {
        label: 'Actividad',
        data: data.activity,
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        yAxisID: 'y'
      }
    ]
  };
  
  const options = {
    responsive: true,
    interaction: {
      mode: 'index' as const,
      intersect: false
    },
    scales: {
      x: {
        grid: {
          display: false
        }
      },
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        title: {
          display: true,
          text: 'Conversiones / Actividad'
        }
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        title: {
          display: true,
          text: 'Tiempo Respuesta (min)'
        },
        grid: {
          drawOnChartArea: false
        },
        reverse: true  // Lower is better for response time
      }
    },
    plugins: {
      legend: {
        position: 'top' as const
      },
      title: {
        display: true,
        text: `Trend de Performance - ${getTimeRangeLabel(timeRange)}`
      },
      tooltip: {
        callbacks: {
          label: (context: any) => {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.dataset.label === 'Tiempo Respuesta (min)') {
              label += `${context.parsed.y} min`;
            } else {
              label += context.parsed.y;
            }
            return label;
          }
        }
      }
    }
  };
  
  return (
    <div className="bg-white p-6 rounded-lg border">
      <Line data={chartData} options={options} />
    </div>
  );
};
```

### **3. 🏆 LEADERBOARD**

```typescript
// Tabla de ranking de vendedores
interface LeaderboardProps {
  sellers: Array<{
    id: number;
    name: string;
    avatar?: string;
    rank: number;
    score: number;
    conversions: number;
    responseTime: number;
    activity: string;
    trend: 'up' | 'down' | 'stable';
  }>;
  selectedSeller: string | 'all';
  onSelectSeller: (sellerId: string) => void;
}

const Leaderboard: React.FC<LeaderboardProps> = ({
  sellers,
  selectedSeller,
  onSelectSeller
}) => {
  const getRankColor = (rank: number) => {
    switch (rank) {
      case 1: return 'bg-yellow-100 text-yellow-800';
      case 2: return 'bg-gray-100 text-gray-800';
      case 3: return 'bg-orange-100 text-orange-800';
      default: return 'bg-blue-50 text-blue-800';
    }
  };
  
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return <TrendingUp className="w-4 h-4 text-green-600" />;
      case 'down': return <TrendingDown className="w-4 h-4 text-red-600" />;
      default: return <Minus className="w-4 h-4 text-gray-400" />;
    }
  };
  
  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <div className="p-4 border-b">
        <h3 className="font-semibold text-lg">🏆 Leaderboard</h3>
        <p className="text-sm text-gray-500">Ranking por performance</p>
      </div>
      
      <div className="divide-y">
        {sellers.map((seller) => (
          <button
            key={seller.id}
            onClick={() => onSelectSeller(seller.id.toString())}
            className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
              selectedSeller === seller.id.toString() ? 'bg-blue-50' : ''
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${getRankColor(seller.rank)}`}>
                  {seller.rank}
                </div>
                
                <div>
                  <div className="font-medium">{seller.name}</div>
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <span>Score: {seller.score.toFixed(1)}</span>
                    <span>•</span>
                    <span>{seller.conversions} conv.</span>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {getTrendIcon(seller.trend)}
                <span className="text-sm font-medium">
                  {seller.responseTime}m
                </span>
              </div>
            </div>
            
            {/* Activity indicator */}
            <div className="mt-2 flex items-center gap-2">
              <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${
                    seller.activity === 'excelente' ? 'bg-green-500' :
                    seller.activity === 'alto' ? 'bg-blue-500' :
                    seller.activity === 'medio' ? 'bg-yellow-500' :
                    seller.activity === 'bajo' ? 'bg-orange-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${(seller.score / 10) * 100}%` }}
                />
              </div>
              <span className="text-xs capitalize text-gray-500">
                {seller.activity}
              </span>
            </div>
          </button>
        ))}
      </div>
      
      <div className="p-4 border-t">
        <button
          onClick={() => onSelectSeller('all')}
          className={`w-full py-2 px-4 rounded ${
            selectedSeller === 'all' 
              ? 'bg-blue-600 text-white' 
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Ver todo el equipo
        </button>
      </div>
    </div>
  );
};
```

### **4. 📋 SELLER METRICS TABLE**

```typescript
// Tabla detallada de métricas por vendedor
interface SellerMetricsTableProps {
  sellers: Array<{
    id: number;
    name: string;
    role: string;
    metrics: {
      conversations: {
        total: number;
        active: number;
        today: number;
        unanswered: number;
      };
      times: {
        avg_response: number;
        first_response: number;
        total_chat: number;
      };
      conversions: {
        generated: number;
        converted: number;
        rate: number;
        revenue: number;
      };
      performance: {
        score: number;
        engagement: number;
        activity: string;
        rank: number;
      };
    };
  }>;
  selectedSeller: string | 'all';
  onSelectSeller: (sellerId: string) => void;
}

const SellerMetricsTable: React.FC<SellerMetricsTableProps> = ({
  sellers,
  selectedSeller,
  onSelectSeller
}) => {
  const [sortBy, setSortBy] = useState<'score' | 'conversions' | 'response' | 'activity'>('score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  
  // Sort sellers
  const sortedSellers = [...sellers].sort((a, b) => {
    let aValue: number, bValue: number;
    
    switch (sortBy) {
      case 'score':
        aValue = a.metrics.performance.score;
        bValue = b.metrics.performance.score;
        break;
      case 'conversions':
        aValue = a.metrics.conversions.converted;
        bValue = b.metrics.conversions.converted;
        break;
      case 'response':
        aValue = a.metrics.times.avg_response;
        bValue = b.metrics.times.avg_response;
        break;
      case 'activity':
        aValue = a.metrics.conversations.active;
        bValue = b.metrics.conversations.active;
        break;
      default:
        return 0;
    }
    
    const multiplier = sortOrder === 'asc' ? 1 : -1;
    return (aValue - bValue) * multiplier;
  });
  
  const handleSort = (column: typeof sortBy) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };
  
  const getSortIcon = (column: typeof sortBy) => {
    if (sortBy !== column) return <ChevronUpDown className="w-4 h-4" />;
    return sortOrder === 'asc' ? 
      <ChevronUp className="w-4 h-4" /> : 
      <ChevronDown className="w-4 h-4" />;
  };
  
  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <div className="p-4 border-b">
        <div className="flex justify-between items-center">
          <h3 className="font-semibold text-lg">Métricas Detalladas</h3>
          <div className="flex gap-2">
            <button className="px-3 py-1 text-sm border rounded hover:bg-gray-50">
              <FileText className="w-4 h-4 inline mr-1" />
              Exportar CSV
            </button>
            <button className="px-3 py-1 text-sm border rounded hover:bg-gray-50">
              <Printer className="w-4 h-4 inline mr-1" />
              Imprimir
            </button>
          </div>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="p-3 text-left font-medium">Vendedor</th>
              <th 
                className="p-3 text-left font-medium cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('score')}
              >
                <div className="flex items-center gap-1">
                  Score
                  {getSortIcon('score')}
                </div>
              </th>
              <th className="p-3 text-left font-medium">Conversaciones</th>
              <th 
                className="p-3 text-left font-medium cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('response')}
              >
                <div className="flex items-center gap-1">
                  Tiempo Resp.
                  {getSortIcon('response')}
                </div>
              </th>
              <th 
                className="p-3 text-left font-medium cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('conversions')}
              >
                <div className="flex items-center gap-1">
                  Conversiones
                  {getSortIcon('conversions')}
                </div>
              </th>
              <th className="p-3 text-left font-medium">Ingreso Est.</th>
              <th 
                className="p-3 text-left font-medium cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('activity')}
              >
                <div className="flex items-center gap-1">
                  Actividad
                  {getSortIcon('activity')}
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {sortedSellers.map((seller) => (
              <tr 
                key={seller.id}
                className={`hover:bg-gray-50 cursor-pointer ${
                  selectedSeller === seller.id.toString() ? 'bg-blue-50' : ''
                }`}
                onClick={() => onSelectSeller(seller.id.toString())}
              >
                <td className="p-3">
                  <div className="font-medium">{seller.name}</div>
                  <div className="text-sm text-gray-500">{seller.role}</div>
                </td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <div className="text-xl font-bold">
                      {seller.metrics.performance.score.toFixed(1)}
                    </div>
                    <div className={`text-xs px-2 py-1 rounded-full ${
                      seller.metrics.performance.score >= 8 ? 'bg-green-100 text-green-800' :
                      seller.metrics.performance.score >= 6 ? 'bg-blue-100 text-blue-800' :
                      seller.metrics.performance.score >= 4 ? 'bg-yellow-100 text-yellow-800' :
                      seller.metrics.performance.score >= 2 ? 'bg-orange-100 text-orange-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {seller.metrics.performance.activity}
                    </div>
                  </div>
                </td>
                <td className="p-3">
                  <div className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Activas:</span>
                      <span className="font-medium">{seller.metrics.conversations.active}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Sin respuesta:</span>
                      <span className={`font-medium ${
                        seller.metrics.conversations.unanswered > 0 ? 'text-red-600' : 'text-green-600'
                      }`}>
                        {seller.metrics.conversations.unanswered}
                      </span>
                    </div>
                  </div>
                </td>
                <td className="p-3">
                  <div className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Promedio:</span>
                      <span className={`font-medium ${
                        seller.metrics.times.avg_response > 30 ? 'text-red-600' :
                        seller.metrics.times.avg_response > 15 ? 'text-orange-600' : 'text-green-600'
                      }`}>
                        {seller.metrics.times.avg_response}m
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Primera:</span>
                      <span>{seller.metrics.times.first_response}m</span>
                    </div>
                  </div>
                </td>
                <td className="p-3">
                  <div className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Total:</span>
                      <span className="font-medium">{seller.metrics.conversions.converted}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Tasa:</span>
                      <span className={`font-medium ${
                        seller.metrics.conversions.rate > 0.3 ? 'text-green-600' :
                        seller.metrics.conversions.rate > 0.15 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {(seller.metrics.conversions.rate * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </td>
                <td className="p-3">
                  <div className="font-medium">
                    ${seller.metrics.conversions.revenue.toLocaleString()}
                  </div>
                </td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div 
                        className={`h-full ${
                          seller.metrics.performance.activity === 'excelente' ? 'bg-green-500' :
                          seller.metrics.performance.activity === 'alto' ? 'bg-blue-500' :
                          seller.metrics.performance.activity === 'medio' ? 'bg-yellow-500' :
                          seller.metrics.performance.activity === 'bajo' ? 'bg-orange-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${(seller.metrics.performance.engagement * 100)}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-500">
                      {(seller.metrics.performance.engagement * 100).toFixed(0)}%
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
```

---

## ⚙️ **CONFIGURACIÓN Y PERSONALIZACIÓN**

### **1. CONFIGURACIÓN DE MÉTRICAS**

#### **Environment Variables:**
```bash
# Métricas configuration
METRICS_REFRESH_INTERVAL_MINUTES=15
METRICS_RETENTION_DAYS=30
REAL_TIME_METRICS_ENABLED=true

# Thresholds para alertas
RESPONSE_TIME_THRESHOLD_MINUTES=30
UNANSWERED_CONVERSATIONS_THRESHOLD=5
CONVERSION_RATE_THRESHOLD=0.1
ACTIVITY_THRESHOLD_LOW=2.0
ACTIVITY_THRESHOLD_MEDIUM=4.0
ACTIVITY_THRESHOLD_HIGH=6.0
ACTIVITY_THRESHOLD_EXCELLENT=8.0

# Leaderboard configuration
LEADERBOARD_UPDATE_INTERVAL=5
LEADERBOARD_MAX_SELLERS=20
LEADERBOARD_MIN_CONVERSATIONS=5
```

#### **Weight Configuration:**
```python
# Ponderación de métricas para score
METRIC_WEIGHTS = {
    'conversion_rate': 0.30,
    'avg_response_time': 0.25,
    'leads_converted': 0.20,
    'engagement_rate': 0.15,
    'conversations_active': 0.10
}

# Normalization ranges
NORMALIZATION_RANGES = {
    'conversion_rate': (0.0, 1.0),
    'avg_response_time': (0, 60),  # 0-60 minutos
    'leads_converted': (0, 50),    # 0-50 leads
    'engagement_rate': (0.0, 1.0),
    'conversations_active': (0, 20)  # 0-20 conversaciones
}
```

### **2. PERSONALIZACIÓN POR ROL**

#### **CEO View:**
```json
{
  "dashboard_config": {
    "default_time_range": "week",
    "default_view": "team",
    "charts_enabled": true,
    "leaderboard_enabled": true,
    "detailed_table_enabled": true,
    "export_enabled": true,
    "alerts_enabled": true,
    "refresh_interval": 300000,  // 5 minutos
    "show_estimated_revenue": true,
    "show_performance_scores": true,
    "show_response_times": true,
    "show_conversion_rates": true
  }
}
```

#### **Manager View:**
```json
{
  "dashboard_config": {
    "default_time_range": "today",
    "default_view": "team",
    "charts_enabled": true,
    "leaderboard_enabled": true,
    "detailed_table_enabled": true,
    "export_enabled": false,
    "alerts_enabled": true,
    "refresh_interval": 600000,  // 10 minutos
    "show_estimated_revenue": false,
    "show_performance_scores": true,
    "show_response_times": true,
    "show_conversion_rates": true
  }
}
```

#### **Seller View:**
```json
{
  "dashboard_config": {
    "default_time_range": "today",
    "default_view": "personal",
    "charts_enabled": true,
    "leaderboard_enabled": false,
    "detailed_table_enabled": false,
    "export_enabled": false,
    "alerts_enabled": false,
    "refresh_interval": 900000,  // 15 minutos
    "show_estimated_revenue": false,
    "show_performance_scores": true,
    "show_response_times": true,
    "show_conversion_rates": true
  }
}
```

### **3. EXPORTACIÓN DE DATOS**

#### **CSV Export:**
```python
async def export_metrics_csv(period: str, seller_id: Optional[int] = None):
    """Exporta métricas a formato CSV"""
    metrics = await get_metrics_for_export(period, seller_id)
    
    # Crear CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Vendedor', 'Período', 'Conversaciones Totales',
        'Conversaciones Activas', 'Sin Respuesta', 'Tiempo Respuesta Prom (min)',
        'Leads Generados', 'Leads Convertidos', 'Tasa Conversión (%)',
        'Ingreso Estimado', 'Score Performance', 'Nivel Actividad', 'Ranking'
    ])
    
    # Data
    for metric in metrics:
        writer.writerow([
            metric['seller_name'],
            metric['period'],
            metric['conversations_total'],
            metric['conversations_active'],
            metric['conversations_unanswered'],
            metric['avg_response_time_minutes'],
            metric['leads_generated'],
            metric['leads_converted'],
            f"{metric['conversion_rate'] * 100:.1f}",
            f"${metric['estimated_revenue']:,.2f}",
            metric['productivity_score'],
            metric['activity_level'],
            metric['team_rank']
        ])
    
    return output.getvalue()
```

#### **PDF Report:**
```python
async def generate_pdf_report(period: str):
    """Genera reporte PDF para CEO"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    
    # Obtener métricas
    metrics = await get_metrics_for_export(period)
    
    # Crear PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Título
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"Reporte de Performance - {period}", styles['Title']))
    elements.append(Paragraph(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    
    # Tabla de métricas
    data = [['Vendedor', 'Score', 'Conversiones', 'Tiempo Resp.', 'Actividad', 'Rank']]
    
    for metric in metrics:
        data.append([
            metric['seller_name'],
            f"{metric['productivity_score']:.1f}",
            metric['leads_converted'],
            f"{metric['avg_response_time_minutes']}m",
            metric['activity_level'],
            metric['team_rank']
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    
    # Generar PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer
```

---

## 🚀 **OPTIMIZACIÓN DE PERFORMANCE**

### **1. REDIS CACHING**

```python
# Estrategia de caching para métricas
class MetricsCache:
    def __init__(self, redis_client, ttl_minutes=5):
        self.redis = redis_client
        self.ttl = ttl_minutes * 60
    
    async def get_cached_metrics(self, seller_id: int, period: str):
        """Obtiene métricas desde cache"""
        cache_key = f"metrics:{seller_id}:{period}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_metrics(self, seller_id: int, period: str, metrics: dict):
        """Guarda métricas en cache"""
        cache_key = f"metrics:{seller_id}:{period}"
        await self.redis.setex(
            cache_key,
            self.ttl,
            json.dumps(metrics)
        )
    
    async def invalidate_cache(self, seller_id: Optional[int] = None):
        """Invalida cache de métricas"""
        if seller_id:
            pattern = f"metrics:{seller_id}:*"
        else:
            pattern = "metrics:*"
        
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
```

### **2. QUERY OPTIMIZATION**

```python
# Optimización de queries para métricas
async def get_optimized_metrics(seller_id: int, period: str):
    """Query optimizada que obtiene múltiples métricas en una sola consulta"""
    period_start = get_period_start(period)
    
    query = """
        WITH conversation_stats AS (
            SELECT 
                COUNT(*) as total_conversations,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_conversations,
                COUNT(CASE WHEN last_message_from_customer = true 
                          AND last_message_time < NOW() - INTERVAL '1 hour' 
                     THEN 1 END) as unanswered_conversations,
                AVG(
                    CASE WHEN last_message_from_customer = true THEN
                        EXTRACT(EPOCH FROM (NOW() - last_message_time)) / 60
                    END
                ) as avg_response_time
            FROM conversations
            WHERE assigned_seller_id = $1
            AND created_at >= $2
        ),
        lead_stats AS (
            SELECT 
                COUNT(*) as leads_generated,
                COUNT(CASE WHEN status = 'closed_won' THEN 1 END) as leads_converted,
                COALESCE(SUM(
                    CASE 
                        WHEN estimated_value IS NOT NULL THEN estimated_value
                        WHEN product_value IS NOT NULL THEN product_value
                        ELSE 1000
                    END
                ), 0) as estimated_revenue
            FROM leads
            WHERE conversation_id IN (
                SELECT id FROM conversations 
                WHERE assigned_seller_id = $1
                AND created_at >= $2
            )
        )
        SELECT 
            cs.*,
            ls.*,
            CASE 
                WHEN ls.leads_generated > 0 
                THEN ls.leads_converted::float / ls.leads_generated
                ELSE 0 
            END as conversion_rate
        FROM conversation_stats cs, lead_stats ls
    """
    
    return await db.fetchrow(query, seller_id, period_start)
```

### **3. BACKGROUND UPDATES**

```python
# Actualización automática de métricas
async def refresh_all_metrics():
    """Actualiza métricas de todos los vendedores en background"""
    sellers = await get_active_sellers()
    
    for seller in sellers:
        try:
            # Calcular métricas
            metrics = await calculate_seller_metrics(seller.id, 'daily')
            
            # Guardar en database
            await save_metrics_to_db(seller.id, 'daily', metrics)
            
            # Cachear en Redis
            await cache_metrics(seller.id, 'daily', metrics)
            
            # Emitir update via Socket.IO
            await emit_metrics_update(seller.id, metrics)
            
        except Exception as e:
            logger.error(f"Error updating metrics for seller {seller.id}: {e}")
            continue
    
    logger.info(f"Updated metrics for {len(sellers)} sellers")
```

---

## 🔧 **TROUBLESHOOTING**

### **1. PROBLEMAS DE PERFORMANCE**

#### **Dashboard Lento:**
```bash
# Verificar cache Redis
redis-cli keys "metrics:*" | wc -l

# Verificar queries lentas
EXPLAIN ANALYZE SELECT * FROM conversations WHERE assigned_seller_id = 1;

# Verificar tamaño de tablas
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### **Métricas Desactualizadas:**
```bash
# Verificar background jobs
curl http://localhost:8000/health/tasks

# Forzar refresh de métricas
curl -X POST http://localhost:8000/admin/core/sellers/refresh-metrics

# Verificar cache TTL
redis-cli ttl metrics:1:daily
```

### **2. PROBLEMAS DE DATOS**

#### **Métricas Incorrectas:**
```python
# Debug script para verificar cálculos
async def debug_metrics(seller_id: int):
    """Script de debug para métricas"""
    print(f"Debug metrics for seller {seller_id}")
    print("="*50)
    
    # Verificar conversaciones
    conversations = await db.fetch("""
        SELECT id, status, last_message_time, last_message_from_customer
        FROM conversations 
        WHERE assigned_seller_id = $1
        ORDER BY created_at DESC
        LIMIT 10
    """, seller_id)
    
    print(f"Last 10 conversations: {len(con