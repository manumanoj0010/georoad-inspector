import { useCallback, useState } from 'react';

interface Props {
  onUpload: (files: File[]) => Promise<unknown>;
  disabled?: boolean;
}

export function ImageUpload({ onUpload, disabled }: Props) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      await onUpload(Array.from(files));
    } finally {
      setUploading(false);
    }
  }, [onUpload]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  return (
    <div
      className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors
        ${dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
        ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
      onDragLeave={() => setDragActive(false)}
      onDrop={handleDrop}
    >
      {uploading ? (
        <div className="flex items-center justify-center gap-2">
          <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full" />
          <span className="text-gray-600">Uploading...</span>
        </div>
      ) : (
        <>
          <div className="text-4xl mb-2">📸</div>
          <p className="text-gray-600 mb-2">
            Drag & drop road images here, or click to browse
          </p>
          <p className="text-sm text-gray-400">JPEG, PNG • Max 50 MB each</p>
          <input
            type="file"
            multiple
            accept=".jpg,.jpeg,.png"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </>
      )}
    </div>
  );
}
