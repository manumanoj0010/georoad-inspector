import { DAMAGE_LABELS } from '../types';

interface Filters {
  damageType: string;
  minConfidence: number;
  reviewStatus: string;
}

interface Props {
  filters: Filters;
  onChange: (filters: Filters) => void;
}

export function FilterPanel({ filters, onChange }: Props) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-800 mb-3">Filters</h3>

      <div className="space-y-3">
        {/* Damage type */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Damage Type</label>
          <select
            value={filters.damageType}
            onChange={(e) => onChange({ ...filters, damageType: e.target.value })}
            className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md
              focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All types</option>
            {Object.entries(DAMAGE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>

        {/* Confidence threshold */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">
            Min Confidence: {(filters.minConfidence * 100).toFixed(0)}%
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={filters.minConfidence}
            onChange={(e) => onChange({ ...filters, minConfidence: parseFloat(e.target.value) })}
            className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-0.5">
            <span>0%</span>
            <span>100%</span>
          </div>
        </div>

        {/* Review status */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Review Status</label>
          <select
            value={filters.reviewStatus}
            onChange={(e) => onChange({ ...filters, reviewStatus: e.target.value })}
            className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md
              focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All statuses</option>
            <option value="unreviewed">Unreviewed</option>
            <option value="confirmed">Confirmed</option>
            <option value="rejected">Rejected</option>
            <option value="needs_review">Needs Review</option>
          </select>
        </div>

        {/* Reset */}
        {(filters.damageType || filters.minConfidence > 0 || filters.reviewStatus) && (
          <button
            onClick={() => onChange({ damageType: '', minConfidence: 0, reviewStatus: '' })}
            className="w-full px-3 py-1.5 text-xs text-gray-600 bg-gray-100 rounded-md
              hover:bg-gray-200 transition-colors"
          >
            Reset Filters
          </button>
        )}
      </div>
    </div>
  );
}
