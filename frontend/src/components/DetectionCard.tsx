import type { Detection, ImageRecord } from '../types';
import { DAMAGE_COLORS, DAMAGE_LABELS } from '../types';

interface Props {
  detection: Detection;
  image: ImageRecord | undefined;
  onConfirm: (id: number) => void;
  onReject: (id: number) => void;
  selected?: boolean;
  onClick?: () => void;
}

export function DetectionCard({ detection, image, onConfirm, onReject, selected, onClick }: Props) {
  const color = DAMAGE_COLORS[detection.damage_type] || '#6b7280';
  const label = DAMAGE_LABELS[detection.damage_type] || detection.damage_type;

  return (
    <div
      className={`border rounded-lg p-4 cursor-pointer transition-all
        ${selected ? 'ring-2 ring-blue-500 border-blue-300' : 'border-gray-200 hover:border-gray-300'}`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
          <span className="font-medium text-sm">{label}</span>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full
          ${detection.review_status === 'confirmed' ? 'bg-green-100 text-green-800' :
            detection.review_status === 'rejected' ? 'bg-red-100 text-red-800' :
            'bg-gray-100 text-gray-600'}`}>
          {detection.review_status}
        </span>
      </div>

      {/* Confidence */}
      <div className="mb-2">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Confidence</span>
          <span>{(detection.confidence * 100).toFixed(1)}%</span>
        </div>
        <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{
              width: `${detection.confidence * 100}%`,
              backgroundColor: detection.confidence > 0.7 ? '#22c55e' :
                detection.confidence > 0.4 ? '#f59e0b' : '#ef4444',
            }}
          />
        </div>
      </div>

      {/* Image with bounding box preview */}
      {image?.storage_url && (
        <div className="relative mb-2 rounded overflow-hidden bg-gray-100" style={{ height: 120 }}>
          <img
            src={image.storage_url}
            alt={image.original_filename}
            className="w-full h-full object-cover"
          />
          {/* Bounding box overlay (approximate) */}
          {image.width && image.height && (
            <div
              className="absolute border-2 rounded"
              style={{
                borderColor: color,
                left: `${(detection.x_min / image.width) * 100}%`,
                top: `${(detection.y_min / image.height) * 100}%`,
                width: `${((detection.x_max - detection.x_min) / image.width) * 100}%`,
                height: `${((detection.y_max - detection.y_min) / image.height) * 100}%`,
              }}
            />
          )}
        </div>
      )}

      {/* Metadata */}
      <div className="text-xs text-gray-500 space-y-0.5">
        <div>ID: {detection.detection_id}</div>
        {detection.latitude && (
          <div>📍 {detection.latitude.toFixed(4)}, {detection.longitude?.toFixed(4)}</div>
        )}
        <div>Source: {image?.original_filename || `Image #${detection.image_id}`}</div>
      </div>

      {/* Action buttons */}
      {detection.review_status === 'unreviewed' && (
        <div className="flex gap-2 mt-3">
          <button
            onClick={(e) => { e.stopPropagation(); onConfirm(detection.id); }}
            className="flex-1 px-3 py-1.5 text-xs font-medium bg-green-50 text-green-700
              border border-green-200 rounded hover:bg-green-100 transition-colors"
          >
            ✓ Confirm
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onReject(detection.id); }}
            className="flex-1 px-3 py-1.5 text-xs font-medium bg-red-50 text-red-700
              border border-red-200 rounded hover:bg-red-100 transition-colors"
          >
            ✗ Reject
          </button>
        </div>
      )}
    </div>
  );
}
