/** Typed API client for the GeoRoad Inspector backend. */

import type {
  InspectionRun,
  ImageRecord,
  Detection,
  UploadResult,
  ProcessingResult,
} from '../types';

const BASE = '';  // Uses Vite proxy in dev

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, options);
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Inspection Runs
export async function createRun(name: string): Promise<InspectionRun> {
  return request('/api/inspection-runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
}

export async function listRuns(): Promise<InspectionRun[]> {
  return request('/api/inspection-runs');
}

export async function getRun(id: number): Promise<InspectionRun> {
  return request(`/api/inspection-runs/${id}`);
}

export async function deleteRun(id: number): Promise<void> {
  return request(`/api/inspection-runs/${id}`, { method: 'DELETE' });
}

// Images
export async function uploadImages(runId: number, files: File[]): Promise<UploadResult> {
  const formData = new FormData();
  files.forEach(f => formData.append('files', f));
  return request(`/api/inspection-runs/${runId}/images`, {
    method: 'POST',
    body: formData,
  });
}

export async function listImages(runId: number): Promise<ImageRecord[]> {
  return request(`/api/inspection-runs/${runId}/images`);
}

// Processing
export async function processRun(runId: number): Promise<ProcessingResult> {
  return request(`/api/inspection-runs/${runId}/process`, { method: 'POST' });
}

export async function getRunStatus(runId: number) {
  return request<{
    status: string;
    total_images: number;
    processed_images: number;
    failed_images: number;
    total_detections: number;
  }>(`/api/inspection-runs/${runId}/status`);
}

// Detections
export async function listDetections(
  runId: number,
  params?: Record<string, string>
): Promise<Detection[]> {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  return request(`/api/inspection-runs/${runId}/detections${query}`);
}

export async function confirmDetection(id: number): Promise<Detection> {
  return request(`/api/detections/${id}/confirm`, { method: 'POST' });
}

export async function rejectDetection(id: number): Promise<Detection> {
  return request(`/api/detections/${id}/reject`, { method: 'POST' });
}

// GeoJSON
export async function getGeoJSON(
  runId: number,
  params?: Record<string, string>
): Promise<unknown> {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  return request(`/api/inspection-runs/${runId}/geojson${query}`);
}

export function getGeoJSONDownloadUrl(runId: number, confirmedOnly = false): string {
  const params = confirmedOnly ? '?confirmed_only=true' : '';
  return `/api/inspection-runs/${runId}/geojson/download${params}`;
}

// ArcGIS Publishing
export async function publishToArcGIS(runId: number): Promise<{
  status: string;
  mode?: string;
  message?: string;
  published_count: number;
  failed_count: number;
  feature_layer_url?: string;
  web_map_url?: string;
}> {
  return request(`/api/inspection-runs/${runId}/publish/arcgis`, { method: 'POST' });
}

export async function getArcGISStatus(runId: number) {
  return request<{
    run_id: number;
    published: boolean;
    arcgis_configured: boolean;
    publications: Array<{
      id: number;
      status: string;
      published_count: number;
      failed_count: number;
      feature_layer_url: string | null;
      published_at: string | null;
    }>;
  }>(`/api/inspection-runs/${runId}/publish/arcgis/status`);
}
