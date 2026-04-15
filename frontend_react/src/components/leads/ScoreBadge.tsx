import { Flame, Thermometer, Snowflake, Wind } from 'lucide-react';

interface ScoreBadgeProps {
  score: number | null | undefined;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const getScoreConfig = (score: number) => {
  if (score >= 80) return {
    label: 'Hot',
    icon: Flame,
    bg: 'bg-red-500/15',
    text: 'text-red-400',
    border: 'border-red-500/30',
    glow: 'shadow-red-500/10',
  };
  if (score >= 50) return {
    label: 'Warm',
    icon: Thermometer,
    bg: 'bg-orange-500/15',
    text: 'text-orange-400',
    border: 'border-orange-500/30',
    glow: 'shadow-orange-500/10',
  };
  if (score >= 20) return {
    label: 'Cool',
    icon: Wind,
    bg: 'bg-violet-500/15',
    text: 'text-violet-400',
    border: 'border-violet-500/30',
    glow: '',
  };
  return {
    label: 'Cold',
    icon: Snowflake,
    bg: 'bg-white/[0.04]',
    text: 'text-white/30',
    border: 'border-white/[0.08]',
    glow: '',
  };
};

export default function ScoreBadge({ score, size = 'sm', showLabel = false }: ScoreBadgeProps) {
  if (score === null || score === undefined) return null;

  const config = getScoreConfig(score);
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'text-[10px] px-1.5 py-0.5 gap-1',
    md: 'text-xs px-2 py-1 gap-1.5',
    lg: 'text-sm px-3 py-1.5 gap-2',
  };

  const iconSizes = { sm: 10, md: 12, lg: 14 };

  return (
    <span
      className={`inline-flex items-center rounded-full font-bold border ${config.bg} ${config.text} ${config.border} ${config.glow} ${sizeClasses[size]} transition-all`}
      title={`Score: ${score}/100 (${config.label})`}
    >
      <Icon size={iconSizes[size]} />
      <span>{score}</span>
      {showLabel && <span className="font-medium opacity-70">{config.label}</span>}
    </span>
  );
}
