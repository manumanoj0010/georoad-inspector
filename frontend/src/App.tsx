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

  const handleNewInspection = () => {
    window.location.reload();
  };

  // Images where YOLO found no road damage (likely non-road photos)
  const nonRoadImages = images.filter(i =>
    i.processing_status === 'completed' && i.error_message === 'no_road_damage_detected'
  );

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <button
            onClick={handleNewInspection}
            className="flex items-center gap-3 hover:opacity-75 transition-opacity cursor-pointer group"
            title="Click to start a new inspection"
          >
            <span className="text-2xl">🛣️</span>
            <div>
              <h1 className="text-xl font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                GeoRoad Inspector
              </h1>
              <p className="text-xs text-gray-400 hidden sm:block">AI-powered road damage detection</p>
            </div>
          </button>
          <div className="flex items-center gap-4">
            {run && (
              <div className="text-sm text-gray-500 hidden sm:block">
                Run: <span className="font-medium text-gray-700">{run.name}</span>
              </div>
            )}
            {currentStep === 'review' && (
              <button
                onClick={handleNewInspection}
                className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg
                  hover:bg-blue-700 transition-colors"
              >
                + New Inspection
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 flex-1 w-full">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Non-road image warning */}
        {nonRoadImages.length > 0 && currentStep === 'review' && (
          <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-start gap-2">
              <span className="text-amber-500 text-lg">⚠️</span>
              <div>
                <p className="text-sm font-semibold text-amber-800">
                  {nonRoadImages.length} image{nonRoadImages.length > 1 ? 's' : ''} had no road damage detected
                </p>
                <p className="text-xs text-amber-700 mt-1">
                  These images may not show road surfaces, or road damage is not visible.
                  The YOLO model only detects: potholes, longitudinal cracks, transverse cracks, alligator cracks.
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {nonRoadImages.map(img => (
                    <span key={img.id} className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded">
                      {img.original_filename}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* All images had no detections */}
        {currentStep === 'review' && detections.length === 0 && images.length > 0 &&
          images.every(i => i.processing_status === 'completed') && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
            <div className="flex items-start gap-2">
              <span className="text-xl">🔍</span>
              <div>
                <p className="font-semibold">No road damage detected in any uploaded image.</p>
                <p className="mt-1 text-xs text-blue-700">
                  This can happen if: images are not of road surfaces, the road appears undamaged,
                  image quality is low, or damage is not one of the 4 supported types.
                  Try uploading clearer road-surface images with visible damage.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Step 1: Create inspection */}
        {currentStep === 'create' && (
          <div className="max-w-2xl mx-auto mt-10">
            <div className="mb-8">
              <h2 className="text-lg font-semibold text-gray-700 mb-4 text-center">How it works</h2>
              <div className="grid grid-cols-4 gap-3">
                {[
                  { icon: '📸', step: '1', label: 'Upload', desc: 'Upload GPS-tagged road photos (JPEG/PNG)' },
                  { icon: '🤖', step: '2', label: 'Analyze', desc: 'YOLOv8 AI detects damage: potholes, cracks' },
                  { icon: '🗺️', step: '3', label: 'Review', desc: 'Review detections on an interactive map' },
                  { icon: '📡', step: '4', label: 'Publish', desc: 'Export GeoJSON or publish to ArcGIS Online' },
                ].map(({ icon, step, label, desc }) => (
                  <div key={step} className="bg-white rounded-xl border border-gray-200 p-4 text-center shadow-sm">
                    <div className="text-3xl mb-2">{icon}</div>
                    <div className="text-xs font-semibold text-blue-600 mb-1">Step {step}</div>
                    <div className="text-sm font-semibold text-gray-800 mb-1">{label}</div>
                    <div className="text-xs text-gray-500">{desc}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
              <div className="text-5xl mb-4">🔍</div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Start New Inspection</h2>
              <p className="text-gray-500 mb-6">
                Name your inspection run and upload road images to get started.
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
              <ImageUpload onUpload={handleUpload} disabled={loading} />
              {images.length > 0 && (
                <p className="mt-4 text-sm text-green-600 font-medium">
                  ✓ {images.length} image(s) uploaded • {images.filter(i => i.latitude).length} with GPS
                </p>
              )}
            </div>
          </div>
        )}

        {/* Step 3: Process */}
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

        {/* Step 4: Review */}
        {currentStep === 'review' && (
          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-3">
              <Dashboard run={run} detections={detections} />
              <div className="mt-4">
                <FilterPanel filters={filters} onChange={setFilters} />
              </div>
              {processingResult && (
                <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-700">
                  Processed {processingResult.processed} images in{' '}
                  {processingResult.elapsed_seconds}s — {processingResult.detections} detections found
                </div>
              )}
              {run && detections.length > 0 && (
                <div className="mt-4">
                  <ExportPanel run={run} detections={detections} />
                </div>
              )}
              {run && detections.length > 0 && (
                <div className="mt-4">
                  <ArcGISPanel run={run} detections={detections} />
                </div>
              )}
              <div className="mt-4">
                <button
                  onClick={handleNewInspection}
                  className="w-full px-4 py-2.5 border border-blue-300 text-blue-600 font-medium
                    rounded-lg hover:bg-blue-50 transition-colors text-sm"
                >
                  + Start New Inspection
                </button>
              </div>
            </div>

            <div className="col-span-9 space-y-6">
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

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white mt-auto">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center gap-2">
            <span>🛣️ GeoRoad Inspector</span>
            <span>·</span>
            <span>AI-powered road damage detection & GIS publishing</span>
          </div>
          <div className="flex items-center gap-3">
            <span>Built by</span>
            <a
              href="https://www.linkedin.com/in/manumanoj0010/"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-blue-600 hover:text-blue-800 transition-colors flex items-center gap-1"
            >
              Manoj Boddu
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
              </svg>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
