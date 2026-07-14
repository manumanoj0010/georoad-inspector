/** Shared TypeScript interfaces matching backend Pydantic schemas. */

export interface InspectionRun {
  id: number;
  name: string;
  status: string;
  total_images: number;
  processed_images: number;
  failed_images: number;
  total_detections: number;
  model_version: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImageRecord {
  id: number;
  inspection_run_id: number;
  original_filename: string;
  stored_filename: string;
  storage_url: string | null;
  width: number | null;
  height: number | null;
  latitude: number | null;
  longitude: number | null;
  captured_at: string | null;
  camera_make: string | null;
  camera_model: string | null;
  location_method: string;
  processing_status: string;
  error_message: string | null;
  created_at: string;
}

export interface Detection {
  id: number;
  detection_id: string;
  inspection_run_id: number;
  image_id: number;
  damage_type: string;
  class_id: number;
  confidence: number;
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
  center_x: number;
  center_y: number;
  latitude: number | null;
  longitude: number | null;
  location_method: string;
  review_status: string;
  review_notes: string | null;
  model_version: string | null;
  arcgis_object_id: number | null;
  created_at: string;
}

export interface UploadResult {
  uploaded: number;
  failed: number;
  errors: string[];
  images: ImageRecord[];
}

export interface ProcessingResult {
  status: string;
  run_id: number;
  processed: number;
  failed: number;
  detections: number;
  elapsed_seconds: number;
  model_version: string;
}

export type ReviewStatus = 'unreviewed' | 'confirmed' | 'rejected' | 'needs_review' | 'published';

export const DAMAGE_COLORS: Record<string, string> = {
  pothole: '#dc2626',
  longitudinal_crack: '#f59e0b',
  transverse_crack: '#3b82f6',
  alligator_crack: '#8b5cf6',
};

export const DAMAGE_LABELS: Record<string, string> = {
  pothole: 'Pothole',
  longitudinal_crack: 'Longitudinal Crack',
  transverse_crack: 'Transverse Crack',
  alligator_crack: 'Alligator Crack',
};
