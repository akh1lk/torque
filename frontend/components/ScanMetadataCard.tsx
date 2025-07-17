"use client";

import { motion } from "framer-motion";
import { Calendar, HardDrive, CheckCircle, Clock, Download, Share2, FileUp } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ScanMetadata {
  title: string;
  size: string;
  status: "complete" | "processing" | "failed";
  createdDate: string;
  processingTime?: string;
  format?: string;
  dimensions?: string;
}

interface ScanMetadataCardProps {
  metadata: ScanMetadata;
  className?: string;
}

export function ScanMetadataCard({ metadata, className = "" }: ScanMetadataCardProps) {
  const getStatusConfig = (status: string) => {
    switch (status) {
      case "complete":
        return {
          icon: CheckCircle,
          color: "text-green-600",
          bgColor: "bg-green-100",
          borderColor: "border-green-200",
          text: "Complete"
        };
      case "processing":
        return {
          icon: Clock,
          color: "text-yellow-600",
          bgColor: "bg-yellow-100",
          borderColor: "border-yellow-200",
          text: "Processing"
        };
      case "failed":
        return {
          icon: Clock,
          color: "text-red-600",
          bgColor: "bg-red-100",
          borderColor: "border-red-200",
          text: "Failed"
        };
      default:
        return {
          icon: Clock,
          color: "text-gray-600",
          bgColor: "bg-gray-100",
          borderColor: "border-gray-200",
          text: "Unknown"
        };
    }
  };

  const statusConfig = getStatusConfig(metadata.status);
  const StatusIcon = statusConfig.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className={`bg-white rounded-xl border border-slate-200 shadow-lg p-6 ${className}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex-1">
          <h2 className="text-2xl font-bold text-slate-900 mb-2">{metadata.title}</h2>
          <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium border ${statusConfig.bgColor} ${statusConfig.color} ${statusConfig.borderColor}`}>
            <StatusIcon className="w-4 h-4" />
            {statusConfig.text}
          </div>
        </div>
      </div>

      {/* Metadata Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
            <HardDrive className="w-5 h-5 text-slate-600" />
          </div>
          <div>
            <p className="text-sm text-slate-500">File Size</p>
            <p className="font-semibold text-slate-900">{metadata.size}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
            <Calendar className="w-5 h-5 text-slate-600" />
          </div>
          <div>
            <p className="text-sm text-slate-500">Created</p>
            <p className="font-semibold text-slate-900">{metadata.createdDate}</p>
          </div>
        </div>

        {metadata.format && (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
              <FileUp className="w-5 h-5 text-slate-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Format</p>
              <p className="font-semibold text-slate-900">{metadata.format}</p>
            </div>
          </div>
        )}

        {metadata.dimensions && (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
              <div className="w-4 h-4 border-2 border-slate-600 rounded-sm"></div>
            </div>
            <div>
              <p className="text-sm text-slate-500">Dimensions</p>
              <p className="font-semibold text-slate-900">{metadata.dimensions}</p>
            </div>
          </div>
        )}
      </div>

      {/* Processing Time (if available) */}
      {metadata.processingTime && (
        <div className="bg-slate-50 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <Clock className="w-4 h-4" />
            Processing time: {metadata.processingTime}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3">
        <Button 
          className="flex-1 bg-gradient-to-r from-slate-900 to-blue-900 hover:from-slate-800 hover:to-blue-800 text-white"
          disabled={metadata.status !== "complete"}
        >
          <Download className="w-4 h-4 mr-2" />
          Download Model
        </Button>
        
        <Button 
          variant="outline" 
          className="flex-1 border-slate-300 hover:border-slate-400"
          disabled={metadata.status !== "complete"}
        >
          <Share2 className="w-4 h-4 mr-2" />
          Share Link
        </Button>
      </div>

      {/* Export Options */}
      {metadata.status === "complete" && (
        <div className="mt-4 pt-4 border-t border-slate-200">
          <p className="text-sm text-slate-600 mb-3">Export formats:</p>
          <div className="flex flex-wrap gap-2">
            {[".GLB", ".PLY", ".OBJ", ".SPLAT"].map((format) => (
              <button
                key={format}
                className="px-3 py-1 text-xs bg-slate-100 hover:bg-slate-200 rounded-md transition-colors text-slate-700 font-medium"
              >
                {format}
              </button>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}
