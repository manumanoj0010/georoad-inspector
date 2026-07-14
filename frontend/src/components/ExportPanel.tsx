import { useState } from 'react';
import { getGeoJSONDownloadUrl } from '../api/client';
import type { InspectionRun, Detection } from '../types';

interface Props {
  run: InspectionRun;
  detections: Detection[];
}

export function ExportPanel({ run, detections }: Props) {
  const [confirmedOnly, setConfirmedOnly] = useState(false);

  const confirmedCount = detections.filter(d => d.review_status === 'confirmed').length;
  const mappedCount = detections.filter(d => d.latitude !== null).length;
  const exportCount = confirmedOnly ? confirmedCount : mappedCount;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-800 mb-3">Export GeoJSON</h3>

      <div className="space-y-3">
        {/* Toggle: all vs confirmed only */}
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={confirmedOnly}
            onChange={(e) => setConfirmedOnly(e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-gray-600">Confirmed detections only</span>
        </label>

        {/* Export count */}
        <p className="text-xs text-gray-500">
          {exportCount} mapped detection{exportCount !== 1 ? 's' : ''} will be exported
        </p>

        {/* Download button */}
        <a
          href={getGeoJSONDownloadUrl(run.id, confirmedOnly)}
          download
          className={`block w-full px-4 py-2.5 text-center text-sm font-medium rounded-lg transition-colors
            ${exportCount > 0
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-100 text-gray-400 pointer-events-none'}`}
        >
          📥 Download .geojson ({exportCount} features)
        </a>

        {/* Info text */}
        <p className="text-xs text-gray-400">
          Import into ArcGIS Online, QGIS, or paste into geojson.io
        </p>
      </div>
    </div>
  );
}
