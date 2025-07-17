"use client";

import { useCallback, useState, useMemo } from "react";
import { Upload, File, X } from "lucide-react";
import { motion } from "framer-motion";

interface FileDropzoneProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
}

export function FileDropzone({ selectedFile, onFileSelect }: FileDropzoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);

  const acceptedTypes = useMemo(() => [".mp4", ".mov", ".avi"], []);
  const maxFileSize = useMemo(() => 100 * 1024 * 1024, []); // 100MB

  const validateFile = useCallback((file: File): boolean => {
    const fileExtension = "." + file.name.split(".").pop()?.toLowerCase();
    return acceptedTypes.includes(fileExtension) && file.size <= maxFileSize;
  }, [acceptedTypes, maxFileSize]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    const validFile = files.find(validateFile);

    if (validFile) {
      onFileSelect(validFile);
    } else {
      alert("Please select a valid video file (.mp4, .mov, .avi) under 100MB.");
    }
  }, [onFileSelect, validateFile]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && validateFile(file)) {
      onFileSelect(file);
    } else {
      alert("Please select a valid video file (.mp4, .mov, .avi) under 100MB.");
    }
    e.target.value = "";
  };

  const removeFile = () => {
    onFileSelect(null);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="space-y-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`
          relative border-2 border-dashed rounded-xl p-8 text-center transition-all
          ${isDragOver
            ? "border-blue-500 bg-blue-50"
            : selectedFile
            ? "border-green-500 bg-green-50"
            : "border-slate-300 bg-slate-50 hover:border-slate-400 hover:bg-slate-100"
          }
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept={acceptedTypes.join(",")}
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          id="file-upload"
        />

        {!selectedFile ? (
          <div className="space-y-4">
            <div className={`
              w-16 h-16 mx-auto rounded-full flex items-center justify-center
              ${isDragOver ? "bg-blue-100" : "bg-slate-200"}
            `}>
              <Upload className={`w-8 h-8 ${isDragOver ? "text-blue-600" : "text-slate-600"}`} />
            </div>
            <div>
              <p className="text-lg font-medium text-slate-900 mb-2">
                {isDragOver ? "Drop your video file here" : "Drag and drop your video file"}
              </p>
              <p className="text-slate-600 mb-4">
                or{" "}
                <label
                  htmlFor="file-upload"
                  className="text-blue-600 hover:text-blue-700 font-medium cursor-pointer underline"
                >
                  browse to choose a file
                </label>
              </p>
              <p className="text-sm text-slate-500">
                Supports MP4, MOV, AVI files up to 100MB
              </p>
            </div>
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center justify-between bg-white rounded-lg p-4 border border-green-200"
          >
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                <File className="w-5 h-5 text-green-600" />
              </div>
              <div className="text-left">
                <p className="font-medium text-slate-900 truncate max-w-xs">
                  {selectedFile.name}
                </p>
                <p className="text-sm text-slate-500">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
            </div>
            <button
              onClick={removeFile}
              className="p-1 hover:bg-red-100 rounded-full transition-colors group"
              type="button"
            >
              <X className="w-5 h-5 text-slate-400 group-hover:text-red-500" />
            </button>
          </motion.div>
        )}
      </motion.div>

      <div className="text-xs text-slate-500 space-y-1">
        <p>• Video should be recorded around the object (360° recommended)</p>
        <p>• Keep the video under 10 seconds for best results</p>
        <p>• Ensure good lighting and steady recording</p>
      </div>
    </div>
  );
}