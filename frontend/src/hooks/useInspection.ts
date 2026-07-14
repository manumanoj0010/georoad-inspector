import { useState, useCallback } from 'react';
import type { Detection, ImageRecord, InspectionRun, ProcessingResult, UploadResult } from '../types';
import * as api from '../api/client';

/** Hook for managing a single inspection run workflow. */
export function useInspection() {
  const [run, setRun] = useState<InspectionRun | null>(null);
  const [images, setImages] = useState<ImageRecord[]>([]);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null);

  const createRun = useCallback(async (name: string) => {
    setLoading(true);
    setError(null);
    try {
      const newRun = await api.createRun(name);
      setRun(newRun);
      return newRun;
    } catch (e) {
      setError((e as Error).message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const uploadImages = useCallback(async (files: File[]) => {
    if (!run) return null;
    setLoading(true);
    setError(null);
    try {
      const result: UploadResult = await api.uploadImages(run.id, files);
      const updatedImages = await api.listImages(run.id);
      setImages(updatedImages);
      const updatedRun = await api.getRun(run.id);
      setRun(updatedRun);
      return result;
    } catch (e) {
      setError((e as Error).message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [run]);

  const process = useCallback(async () => {
    if (!run) return null;
    setLoading(true);
    setError(null);
    try {
      const result = await api.processRun(run.id);
      setProcessingResult(result);
      const updatedRun = await api.getRun(run.id);
      setRun(updatedRun);
      const dets = await api.listDetections(run.id);
      setDetections(dets);
      return result;
    } catch (e) {
      setError((e as Error).message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [run]);

  const refreshDetections = useCallback(async (params?: Record<string, string>) => {
    if (!run) return;
    try {
      const dets = await api.listDetections(run.id, params);
      setDetections(dets);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [run]);

  const confirmDetection = useCallback(async (id: number) => {
    try {
      const updated = await api.confirmDetection(id);
      setDetections(prev => prev.map(d => d.id === id ? updated : d));
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const rejectDetection = useCallback(async (id: number) => {
    try {
      const updated = await api.rejectDetection(id);
      setDetections(prev => prev.map(d => d.id === id ? updated : d));
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  return {
    run, images, detections, loading, error, processingResult,
    createRun, uploadImages, process, refreshDetections,
    confirmDetection, rejectDetection,
  };
}
