import type { InspectionRun, Detection } from '../types';
import { DAMAGE_LABELS } from '../types';

interface Props {
  run: InspectionRun | null;
  detections: Detection[];
}

export function Dashboard({ run, detections }: Props) {
  if (!run) return null;

  const confirmed = detections.filter(d => d.review_status === 'confirmed').length;
  const rejected = detections.filter(d => d.review_status === 'rejected').length;
  const unreviewed = detections.filter(d => d.review_status === 'unreviewed').length;
  const mapped = detections.filter(d => d.latitude !== null).length;

  // Damage type counts
  const damageCounts: Record<string, number> = {};
  detections.forEach(d => {
    damageCounts[d.damage_type] = (damageCounts[d.damage_type] || 0) + 1;
  });

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Inspection Summary</h2>

      {/* Status badge */}
      <div className="flex items-center gap-2 mb-4">
        <span className={`px-2.5 py-1 text-xs font-medium rounded-full
          ${run.status === 'completed' ? 'bg-green-100 text-green-800' :
            run.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
            'bg-gray-100 text-gray-600'}`}>
          {run.status.toUpperCase()}
        </span>
        {run.model_version && (
          <span className="text-xs text-gray-500">Model: {run.model_version}</span>
        )}
      </div>

      {/* Image stats */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <Stat label="Images" value={run.total_images} />
        <Stat label="Processed" value={run.processed_images} />
        <Stat label="Detections" value={run.total_detections} />
        <Stat label="Failed" value={run.failed_images} color="red" />
      </div>

      {/* Review stats */}
      {detections.length > 0 && (
        <>
          <h3 className="text-sm font-medium text-gray-700 mb-2">Review Status</h3>
          <div className="grid grid-cols-2 gap-2 mb-4">
            <MiniStat label="Unreviewed" value={unreviewed} color="gray" />
            <MiniStat label="Confirmed" value={confirmed} color="green" />
            <MiniStat label="Rejected" value={rejected} color="red" />
            <MiniStat label="Mapped" value={mapped} color="blue" />
          </div>

          <h3 className="text-sm font-medium text-gray-700 mb-2">Damage Types</h3>
          <div className="space-y-1.5">
            {Object.entries(damageCounts)
              .sort((a, b) => b[1] - a[1])
              .map(([type, count]) => (
                <div key={type} className="flex justify-between text-sm">
                  <span className="text-gray-600">{DAMAGE_LABELS[type] || type}</span>
                  <span className="font-medium text-gray-800">{count}</span>
                </div>
              ))}
          </div>
        </>
      )}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`text-xl font-bold ${color === 'red' && value > 0 ? 'text-red-600' : 'text-gray-800'}`}>
        {value}
      </div>
    </div>
  );
}

function MiniStat({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    gray: 'bg-gray-100 text-gray-700',
    green: 'bg-green-50 text-green-700',
    red: 'bg-red-50 text-red-700',
    blue: 'bg-blue-50 text-blue-700',
  };
  return (
    <div className={`rounded px-2 py-1.5 text-xs ${colors[color]}`}>
      <span className="font-medium">{value}</span> {label}
    </div>
  );
}
