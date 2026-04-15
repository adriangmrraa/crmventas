import { useMemo } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, LabelList } from 'recharts';

interface FunnelData {
  stage: string;
  count: number;
}

interface SalesFunnelChartProps {
  data: FunnelData[];
}

const STAGE_COLORS: Record<string, string> = {
  'Nuevo': '#8F3DFF',        // Blue
  'Contactado': '#8b5cf6',   // Violet
  'Calificado': '#ec4899',   // Pink
  'Propuesta': '#f59e0b',    // Amber
  'Negociación': '#10b981',  // Emerald
  'Cerrado ganado': '#22c55e', // Green
  'Cerrado perdido': '#ef4444'  // Red
};

export default function SalesFunnelChart({ data }: SalesFunnelChartProps) {
  const chartData = useMemo(() => {
    // Sort stages by a predefined order if possible, or just use as is
    const order = ['Nuevo', 'Contactado', 'Calificado', 'Propuesta', 'Negociación', 'Cerrado ganado', 'Cerrado perdido'];
    return [...data].sort((a, b) => order.indexOf(a.stage) - order.indexOf(b.stage));
  }, [data]);

  return (
    <div className="w-full h-[350px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          layout="vertical"
          data={chartData}
          margin={{ top: 5, right: 80, left: 20, bottom: 5 }}
        >
          <XAxis type="number" hide />
          <YAxis 
            dataKey="stage" 
            type="category" 
            axisLine={false} 
            tickLine={false}
            tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
            width={120}
          />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.05)' }}
            contentStyle={{
              backgroundColor: 'rgba(15, 23, 42, 0.9)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '12px',
              backdropFilter: 'blur(8px)',
              color: '#fff',
              fontSize: '12px'
            }}
            itemStyle={{ color: '#fff' }}
          />
          <Bar dataKey="count" radius={[0, 8, 8, 0]} barSize={24}>
            {chartData.map((entry, index) => (
              <Cell 
                key={`cell-${index}`} 
                fill={STAGE_COLORS[entry.stage] || '#64748b'} 
                fillOpacity={0.8}
              />
            ))}
            <LabelList 
              dataKey="count" 
              position="right" 
              style={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12, fontWeight: 'bold' }} 
              offset={10}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
