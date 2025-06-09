"use client";

import { motion } from "framer-motion";
import { Calendar, Clock, CheckCircle, Loader2, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface Scan {
  id: string;
  title: string;
  date: string;
  status: "processing" | "complete" | "failed";
  thumbnail?: string;
  processingProgress?: number;
}

interface ScanCardProps {
  scan: Scan;
  index: number;
}

export function ScanCard({ scan, index }: ScanCardProps) {
  const getStatusConfig = (status: string) => {
    switch (status) {
      case "complete":
        return {
          badge: "bg-green-100 text-green-800 border-green-200",
          icon: <CheckCircle className="w-3 h-3" />,
          text: "Complete"
        };
      case "processing":
        return {
          badge: "bg-yellow-100 text-yellow-800 border-yellow-200",
          icon: <Loader2 className="w-3 h-3 animate-spin" />,
          text: "Processing"
        };
      case "failed":
        return {
          badge: "bg-red-100 text-red-800 border-red-200",
          icon: <Clock className="w-3 h-3" />,
          text: "Failed"
        };
      default:
        return {
          badge: "bg-gray-100 text-gray-800 border-gray-200",
          icon: <Clock className="w-3 h-3" />,
          text: "Unknown"
        };
    }
  };

  const statusConfig = getStatusConfig(scan.status);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden group"
    >
      {/* Thumbnail */}
      <div className="aspect-video bg-gradient-to-br from-slate-100 to-slate-200 relative overflow-hidden">
        {scan.thumbnail ? (
          <img
            src={scan.thumbnail}
            alt={scan.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <div className="w-16 h-16 bg-slate-300 rounded-lg flex items-center justify-center">
              <div className="w-8 h-8 bg-slate-400 rounded opacity-60"></div>
            </div>
          </div>
        )}
        
        {/* Overlay on hover */}
        <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-200 flex items-center justify-center">
          <Button
            size="sm"
            className="opacity-0 group-hover:opacity-100 transition-all duration-200 bg-white text-slate-900 hover:bg-slate-100"
          >
            <Eye className="w-4 h-4 mr-1" />
            View
          </Button>
        </div>

        {/* Status badge */}
        <div className="absolute top-3 right-3">
          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${statusConfig.badge}`}>
            {statusConfig.icon}
            {statusConfig.text}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-semibold text-slate-900 mb-2 line-clamp-1">
          {scan.title}
        </h3>
        
        <div className="flex items-center text-sm text-slate-500 mb-3">
          <Calendar className="w-4 h-4 mr-1" />
          {scan.date}
        </div>

        {/* Processing progress bar for processing status */}
        {scan.status === "processing" && scan.processingProgress !== undefined && (
          <div className="mb-3">
            <div className="flex items-center justify-between text-xs text-slate-600 mb-1">
              <span>Processing...</span>
              <span>{scan.processingProgress}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-1.5">
              <motion.div
                className="bg-gradient-to-r from-slate-900 to-blue-900 h-1.5 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${scan.processingProgress}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-2">
          {scan.status === "complete" && (
            <>
              <Button size="sm" variant="outline" className="flex-1">
                Download
              </Button>
              <Button size="sm" className="flex-1 bg-gradient-to-r from-slate-900 to-blue-900 hover:from-slate-800 hover:to-blue-800 text-white">
                View 3D
              </Button>
            </>
          )}
          {scan.status === "processing" && (
            <Button size="sm" variant="outline" className="w-full" disabled>
              Processing...
            </Button>
          )}
          {scan.status === "failed" && (
            <Button size="sm" variant="outline" className="w-full">
              Retry Upload
            </Button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
