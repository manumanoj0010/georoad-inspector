import { useState } from 'react';
import { useInspection } from './hooks/useInspection';
import { ImageUpload } from './components/ImageUpload';
import { Dashboard } from './components/Dashboard';
import { DetectionCard } from './components/DetectionCard';
import { ExportPanel } from './components/ExportPanel';
import { InspectionMap } from './components/InspectionMap';
import { FilterPanel } from './components/FilterPanel';
import { ArcGISPanel } from './components/ArcGISPanel';

type Step = 'create' | 'upload' | 'process' | 'review';

export default function App() {
  const {
    run, images, detections, loading, error, processingResult,
    createRun, uploadImages, process, confirmDetection, rejectDetection,
  } = useInspection();

  const [runName, setRunName] = useState('');
  const [selectedDetection, setSelectedDetection] = useState<number | null>(null);
  const [filters, setFilters] = useState({ damageType: '', minConfidence: 0, reviewStatus: '' });

  // Determine current step from state
  const currentStep: Step = !run ? 'create' :
    images.length === 0 ? 'upload' :
    (detections.length === 0 && run.status !== 'completed') ? 'process' : 'review';

  const handleCreate = async () => {
    const name = runName.trim() || `Inspection ${new Date().toLocaleDateString()}`;
    await createRun(name);
  };

  const handleUpload = async (files: File[]) => {
    await uploadImages(files);
  };

  const handleProcess = async () => {
    await process();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🛣️</span>
            <h1 className="text-xl font-bold text-gray-900">GeoRoad Inspector</h1>
          </div>
          {run && (
            <div className="text-sm text-gray-500">
              Run: <span className="font-medium text-gray-700">{run.name}</span>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {/* Error banner */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Step 1: Create inspection */}
        {currentStep === 'create' && (
          <div className="max-w-md mx-auto mt-20">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
              <div className="text-5xl mb-4">🔍</div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">New Inspection</h2>
              <p className="text-gray-500 mb-6">
                Create an inspection run to upload and analyze road images.
              </p>
              <input
                type="text"
                placeholder="Inspection name (optional)"
                value={runName}
                onChange={(e) => setRunName(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg mb-4
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              />
              <button
                onClick={handleCreate}
                disabled={loading}
                className="w-full px-4 py-2.5 bg-blue-600 text-white font-medium rounded-lg
                  hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {loading ? 'Creating...' : 'Create Inspection'}
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Upload images */}
        {currentStep === 'upload' && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
              <h2 className="text-xl font-bold text-gray-800 mb-2">Upload Road Images</h2>
              <p className="text-gray-500 mb-6">
                Upload GPS-tagged road photos for damage detection analysis.
              </p>
              <div className="relative">
                <ImageUpload onUpload={handleUpload} disabled={loading} />
              </div>
              {images.length > 0 && (
                <p className="mt-4 text-sm text-green-600 font-medium">
                  ✓ {images.length} image(s) uploaded • {images.filter(i => i.latitude).length} with GPS
                </p>
              )}
            </div>
          </div>
        )}

        {/* Step 3: Ready to process / Processing */}
        {currentStep === 'process' && (
          <div className="max-w-2xl mx-auto">
            {loading ? (
              <div className="text-center mt-20">
                <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4" />
                <h2 className="text-xl font-bold text-gray-800 mb-2">Analyzing Images...</h2>
                <p className="text-gray-500">Running YOLO road damage detection model</p>
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
                <h2 className="text-xl font-bold text-gray-800 mb-2">Ready to Analyze</h2>
                <p className="text-gray-500 mb-4">
                  {images.length} image(s) uploaded • {images.filter(i => i.latitude).length} with GPS
                </p>
                <button
                  onClick={handleProcess}
                  className="w-full px-4 py-3 bg-green-600 text-white font-medium rounded-lg
                    hover:bg-green-700 transition-colors text-lg"
                >
                  🔍 Analyze {images.length} Image(s)
                </button>
              </div>
            )}
          </div>
        )}

        {/* Step 4: Review detections */}
        {currentStep === 'review' && (
          <div className="grid grid-cols-12 gap-6">
            {/* Sidebar: Dashboard */}
            <div className="col-span-3">
              <Dashboard run={run} detections={detections} />

              {/* Filters */}
              <div className="mt-4">
                <FilterPanel filters={filters} onChange={setFilters} />
              </div>

              {processingResult && (
                <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-700">
                  Processed {processingResult.processed} images in{' '}
                  {processingResult.elapsed_seconds}s — {processingResult.detections} detections found
                </div>
              )}

              {/* GeoJSON Export */}
              {run && detections.length > 0 && (
                <div className="mt-4">
                  <ExportPanel run={run} detections={detections} />
                </div>
              )}

              {/* ArcGIS Publish */}
              {run && detections.length > 0 && (
                <div className="mt-4">
                  <ArcGISPanel run={run} detections={detections} />
                </div>
              )}
            </div>

            {/* Main: Map + Detection cards */}
            <div className="col-span-9 space-y-6">
              {/* Leaflet Map */}
              {run && (
                <InspectionMap
                  runId={run.id}
                  detections={detections}
                  selectedDetectionId={selectedDetection}
                  onMarkerClick={(id) => setSelectedDetection(id)}
                  filters={filters.damageType || filters.minConfidence > 0 || filters.reviewStatus
                    ? {
                        damageType: filters.damageType || undefined,
                        minConfidence: filters.minConfidence || undefined,
                        reviewStatus: filters.reviewStatus || undefined,
                      }
                    : undefined}
                />
              )}

              {/* Detection cards */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-bold text-gray-800">
                    Detections ({detections.length})
                  </h2>
                  <div className="text-xs text-gray-500">
                    Click to select • Confirm or reject detections
                  </div>
                </div>

                {detections.length === 0 ? (
                  <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                    <div className="text-4xl mb-3">🔍</div>
                    <p className="text-gray-500">No detections found. Try uploading more images or lowering the confidence threshold.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {detections.map(det => (
                      <DetectionCard
                        key={det.id}
                        detection={det}
                        image={images.find(i => i.id === det.image_id)}
                        onConfirm={confirmDetection}
                        onReject={rejectDetection}
                        selected={selectedDetection === det.id}
                        onClick={() => setSelectedDetection(det.id)}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
