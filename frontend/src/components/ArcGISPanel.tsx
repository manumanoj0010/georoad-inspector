import { useState } from 'react';
import { publishToArcGIS } from '../api/client';
import type { InspectionRun, Detection } from '../types';

interface Props {
  run: InspectionRun;
  detections: Detection[];
}

export function ArcGISPanel({ run, detections }: Props) {
  const [publishing, setPublishing] = useState(false);
  const [result, setResult] = useState<{
    status: string;
    mode?: string;
    message?: string;
    published_count: number;
    failed_count: number;
    feature_layer_url?: string;
    web_map_url?: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const confirmedCount = detections.filter(
    d => d.review_status === 'confirmed' && d.latitude !== null
  ).length;

  const handlePublish = async () => {
    setPublishing(true);
    setError(null);
    setResult(null);
    try {
      const res = await publishToArcGIS(run.id);
      setResult(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-800 mb-3">Publish to ArcGIS</h3>

      <p className="text-xs text-gray-500 mb-3">
        Publish confirmed detections as features to an ArcGIS Online hosted layer.
        Only confirmed + GPS-mapped detections are eligible.
      </p>

      <div className="text-sm mb-3">
        <span className="text-gray-600">Eligible: </span>
        <span className="font-medium">{confirmedCount} confirmed detection{confirmedCount !== 1 ? 's' : ''}</span>
      </div>

      <button
        onClick={handlePublish}
        disabled={publishing || confirmedCount === 0}
        className={`w-full px-4 py-2.5 text-sm font-medium rounded-lg transition-colors
          ${confirmedCount > 0
            ? 'bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50'
            : 'bg-gray-100 text-gray-400 cursor-not-allowed'}`}
      >
        {publishing ? (
          <span className="flex items-center justify-center gap-2">
            <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
            Publishing...
          </span>
        ) : (
          `🌐 Publish to ArcGIS (${confirmedCount})`
        )}
      </button>

      {/* Result */}
      {result && (
        <div className={`mt-3 p-3 rounded-lg text-xs ${
          result.status === 'completed'
            ? 'bg-green-50 border border-green-200 text-green-700'
            : 'bg-amber-50 border border-amber-200 text-amber-700'
        }`}>
          <div className="font-medium mb-1">
            {result.status === 'completed' ? '✓ Published successfully' : `Status: ${result.status}`}
          </div>
          <div>{result.published_count} features published</div>
          {result.failed_count > 0 && <div>{result.failed_count} failed</div>}
          {result.mode === 'mock' && (
            <div className="mt-1 text-gray-500 italic">
              (Mock mode — ArcGIS credentials not configured)
            </div>
          )}
          {result.feature_layer_url && result.mode !== 'mock' && (
            <a
              href={result.feature_layer_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-1 text-blue-600 underline"
            >
              Open Feature Layer →
            </a>
          )}
          {result.web_map_url && (
            <a
              href={result.web_map_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-1 ml-2 text-blue-600 underline"
            >
              Open Web Map →
            </a>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
          {error}
        </div>
      )}

      {confirmedCount === 0 && (
        <p className="mt-2 text-xs text-gray-400">
          Confirm detections first before publishing.
        </p>
      )}
    </div>
  );
}
