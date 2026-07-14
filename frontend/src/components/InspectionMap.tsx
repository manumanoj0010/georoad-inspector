import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Detection } from '../types';
import { DAMAGE_COLORS, DAMAGE_LABELS } from '../types';
import { getGeoJSON } from '../api/client';

interface Props {
  runId: number | null;
  detections: Detection[];
  selectedDetectionId: number | null;
  onMarkerClick: (detectionId: number) => void;
  filters?: {
    damageType?: string;
    minConfidence?: number;
    reviewStatus?: string;
  };
}

export function InspectionMap({ runId, detections, selectedDetectionId, onMarkerClick, filters }: Props) {
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<L.LayerGroup | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [featureCount, setFeatureCount] = useState(0);

  // Initialize map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current).setView([39.8, -98.5], 4); // Center US

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);

    markersRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Load GeoJSON and render markers
  useEffect(() => {
    if (!runId || !mapRef.current || !markersRef.current) return;

    const loadData = async () => {
      try {
        const params: Record<string, string> = {};
        if (filters?.damageType) params.damage_type = filters.damageType;
        if (filters?.minConfidence) params.min_confidence = String(filters.minConfidence);
        if (filters?.reviewStatus) params.review_status = filters.reviewStatus;

        const geojson = await getGeoJSON(runId, Object.keys(params).length ? params : undefined) as GeoJSONFeatureCollection;
        renderMarkers(geojson);
      } catch (err) {
        console.error('Failed to load GeoJSON:', err);
      }
    };

    loadData();
  }, [runId, detections, filters]);

  // Highlight selected marker
  useEffect(() => {
    // Re-render to update selected state
    if (!markersRef.current) return;
    markersRef.current.eachLayer((layer) => {
      const marker = layer as L.CircleMarker;
      const id = (marker as unknown as { _detectionId?: number })._detectionId;
      if (id === selectedDetectionId) {
        marker.setStyle({ weight: 4, color: '#1d4ed8' });
        marker.bringToFront();
      } else {
        marker.setStyle({ weight: 2, color: '#ffffff' });
      }
    });
  }, [selectedDetectionId]);

  function renderMarkers(geojson: GeoJSONFeatureCollection) {
    if (!markersRef.current || !mapRef.current) return;

    markersRef.current.clearLayers();
    const bounds: L.LatLngExpression[] = [];

    geojson.features.forEach((feature) => {
      if (!feature.geometry || feature.geometry.type !== 'Point') return;

      const [lon, lat] = feature.geometry.coordinates;
      const props = feature.properties || {};
      const damageType = String(props.damageType || 'unknown');
      const confidence = Number(props.confidence || 0);
      const color = DAMAGE_COLORS[damageType] || '#6b7280';
      const label = DAMAGE_LABELS[damageType] || damageType;

      // Find the detection ID from our local detections array
      const detection = detections.find(d => d.detection_id === String(props.detectionId));
      const detId = detection?.id;

      const marker = L.circleMarker([lat, lon], {
        radius: 6 + confidence * 5,
        fillColor: color,
        color: detId === selectedDetectionId ? '#1d4ed8' : '#ffffff',
        weight: detId === selectedDetectionId ? 4 : 2,
        opacity: 1,
        fillOpacity: 0.85,
      });

      // Store detection ID on marker for selection tracking
      (marker as unknown as { _detectionId?: number })._detectionId = detId;

      // Popup
      marker.bindPopup(`
        <div style="min-width:180px">
          <div style="font-weight:600;margin-bottom:4px;color:${color}">${label}</div>
          <div style="font-size:12px;color:#555">
            Confidence: ${(confidence * 100).toFixed(1)}%<br/>
            Status: ${String(props.reviewStatus || 'unreviewed')}<br/>
            ID: ${String(props.detectionId || '—')}<br/>
            <em style="color:#999">Location is approximate (camera position)</em>
          </div>
        </div>
      `);

      marker.on('click', () => {
        if (detId) onMarkerClick(detId);
      });

      marker.addTo(markersRef.current!);
      bounds.push([lat, lon]);
    });

    setFeatureCount(bounds.length);

    // Fit map to markers
    if (bounds.length > 0) {
      mapRef.current.fitBounds(L.latLngBounds(bounds).pad(0.1));
    }
  }

  return (
    <div className="relative">
      <div ref={containerRef} className="w-full rounded-lg border border-gray-200 overflow-hidden" style={{ height: 400 }} />

      {/* Feature count badge */}
      <div className="absolute top-3 right-3 z-[1000] bg-white/90 backdrop-blur px-2.5 py-1 rounded-md shadow text-xs text-gray-700">
        {featureCount} point{featureCount !== 1 ? 's' : ''} on map
      </div>

      {/* Approximate location notice */}
      <div className="absolute bottom-3 left-3 z-[1000] bg-amber-50/90 backdrop-blur px-2.5 py-1 rounded-md text-xs text-amber-700 border border-amber-200">
        ⚠ Locations are approximate (camera position)
      </div>

      {/* Legend */}
      <div className="absolute top-3 left-3 z-[1000] bg-white/90 backdrop-blur px-3 py-2 rounded-md shadow">
        <div className="text-xs font-medium text-gray-700 mb-1">Damage Types</div>
        {Object.entries(DAMAGE_LABELS).map(([key, label]) => (
          <div key={key} className="flex items-center gap-1.5 text-xs text-gray-600">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: DAMAGE_COLORS[key] }} />
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}

// GeoJSON type declarations for TypeScript
interface GeoJSONFeatureCollection {
  type: string;
  features: GeoJSONFeature[];
}
interface GeoJSONFeature {
  type: string;
  id?: string;
  geometry: { type: string; coordinates: number[] } | null;
  properties: Record<string, string | number | boolean | null | undefined> | null;
}
