/**
 * StaleDealIndicator — SPEC-09: Pulsing red dot for stale deals.
 */
interface Props {
  fechaUltimaActividad: string | null;
  thresholdDays?: number;
}

export default function StaleDealIndicator({ fechaUltimaActividad, thresholdDays = 7 }: Props) {
  if (!fechaUltimaActividad) return null;
  const daysSince = Math.floor((Date.now() - new Date(fechaUltimaActividad).getTime()) / (1000 * 60 * 60 * 24));
  if (daysSince <= thresholdDays) return null;

  return (
    <span className="relative flex h-3 w-3" title={`Sin actividad hace ${daysSince} dias`}>
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
    </span>
  );
}
