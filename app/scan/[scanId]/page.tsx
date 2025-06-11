"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Eye, RotateCcw, ZoomIn, Move3D, ExternalLink } from "lucide-react";
import { Navbar } from "@/components/navbar";
import { ModelViewer } from "@/components/ModelViewer";
import { ScanMetadataCard } from "@/components/ScanMetadataCard";
import { Button } from "@/components/ui/button";

// Mock scan data - in a real app, this would come from an API
const mockScans = {
  "studio-desk-june-2024": {
    id: "studio-desk-june-2024",
    title: "Studio Desk — June 2024",
    size: "78MB",
    status: "complete" as const,
    createdDate: "June 15, 2024",
    processingTime: "2m 34s",
    format: "GLB",
    dimensions: "1.5m × 0.8m × 0.9m",
    modelType: "desk" as const,
    description: "Modern office desk with monitor stand and storage drawers"
  },
  "vintage-chair": {
    id: "vintage-chair",
    title: "Vintage Leather Chair",
    size: "45MB",
    status: "complete" as const,
    createdDate: "June 10, 2024",
    processingTime: "1m 56s",
    format: "PLY",
    dimensions: "0.7m × 0.8m × 1.2m",
    modelType: "chair" as const,
    description: "Classic leather armchair with wooden frame"
  },
  "corner-room-scan": {
    id: "corner-room-scan",
    title: "Living Room Corner",
    size: "156MB",
    status: "processing" as const,
    createdDate: "June 20, 2024",
    format: "SPLAT",
    modelType: "room" as const,
    description: "Corner of living room with furniture and decorations"
  },
  "processing-scan": {
    id: "processing-scan",
    title: "Kitchen Appliance",
    size: "32MB",
    status: "processing" as const,
    createdDate: "June 21, 2024",
    format: "GLB",
    modelType: "cube" as const,
    description: "Modern coffee machine scan in progress"
  }
};

export default function ScanPage() {
  const params = useParams();
  const scanId = params.scanId as string;
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  // Get scan data (mock data for now)
  const scanData = mockScans[scanId as keyof typeof mockScans];
  
  // Handle case where scan is not found
  if (!scanData) {
    return (
      <div className="min-h-screen bg-slate-50">
        <Navbar />
        <div className="pt-24 pb-12">
          <div className="container mx-auto px-4 max-w-4xl">
            <div className="text-center py-16">
              <div className="w-24 h-24 bg-slate-200 rounded-full flex items-center justify-center mx-auto mb-6">
                <Eye className="w-12 h-12 text-slate-400" />
              </div>
              <h1 className="text-3xl font-bold text-slate-900 mb-4">Scan Not Found</h1>
              <p className="text-slate-600 mb-8">The scan you&apos;re looking for doesn&apos;t exist or has been removed.</p>
              <Link href="/dashboard">
                <Button className="bg-gradient-to-r from-slate-900 to-blue-900 hover:from-slate-800 hover:to-blue-800 text-white">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Dashboard
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      
      <div className="pt-24 pb-12">
        <div className="container mx-auto px-4 max-w-7xl">
          {/* Breadcrumb Navigation */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="flex items-center gap-2 text-sm text-slate-600 mb-8"
          >
            <Link href="/dashboard" className="hover:text-slate-900 transition-colors">
              Dashboard
            </Link>
            <span>/</span>
            <Link href="/dashboard" className="hover:text-slate-900 transition-colors">
              Scans
            </Link>
            <span>/</span>
            <span className="text-slate-900 font-medium">{scanData.title}</span>
          </motion.div>

          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="flex flex-col md:flex-row md:items-center md:justify-between mb-8"
          >
            <div>
              <h1 className="text-4xl lg:text-5xl font-bold mb-2 text-slate-900">
                {scanData.title}
              </h1>
              <p className="text-xl text-slate-600">
                {scanData.description}
              </p>
            </div>
            
            <div className="mt-6 md:mt-0 flex items-center gap-3">
              <Button
                variant="outline"
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="border-slate-300 hover:border-slate-400"
              >
                <ExternalLink className="w-4 h-4 mr-2" />
                Fullscreen
              </Button>
              <Link href="/dashboard">
                <Button variant="outline" className="border-slate-300 hover:border-slate-400">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
              </Link>
            </div>
          </motion.div>

          {/* Main Content */}
          <div className="grid lg:grid-cols-3 gap-8">
            {/* 3D Model Viewer */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="lg:col-span-2"
            >
              <div className="space-y-4">
                <ModelViewer 
                  modelType={scanData.modelType}
                  className="h-[600px]"
                />
                
                {/* Viewer Controls Info */}
                <div className="bg-white rounded-lg border border-slate-200 p-4">
                  <h3 className="font-semibold text-slate-900 mb-3 flex items-center">
                    <Move3D className="w-5 h-5 mr-2" />
                    3D Viewer Controls
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-slate-600">
                    <div className="flex items-center gap-2">
                      <RotateCcw className="w-4 h-4" />
                      Click + drag to rotate
                    </div>
                    <div className="flex items-center gap-2">
                      <ZoomIn className="w-4 h-4" />
                      Scroll to zoom
                    </div>
                    <div className="flex items-center gap-2">
                      <Move3D className="w-4 h-4" />
                      Right-click + drag to pan
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Metadata Panel */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="lg:col-span-1"
            >
              <ScanMetadataCard 
                metadata={{
                  title: scanData.title,
                  size: scanData.size,
                  status: scanData.status,
                  createdDate: scanData.createdDate,
                  processingTime: "processingTime" in scanData ? scanData.processingTime : undefined,
                  format: scanData.format,
                  dimensions: "dimensions" in scanData ? scanData.dimensions : undefined
                }}
              />
            </motion.div>
          </div>

          {/* Additional Info Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="mt-12 grid md:grid-cols-3 gap-6"
          >
            {[
              {
                title: "High Quality",
                description: "Captured using Neural Gaussian Splatting for photorealistic detail",
                icon: "✨"
              },
              {
                title: "Interactive",
                description: "Full 360° viewing with zoom and pan controls",
                icon: "🔄"
              },
              {
                title: "Multiple Formats",
                description: "Export to GLB, PLY, OBJ, and SPLAT formats",
                icon: "📁"
              }
            ].map((feature, index) => (
              <div
                key={index}
                className="bg-white rounded-xl p-6 border border-slate-200 text-center"
              >
                <div className="text-3xl mb-3">{feature.icon}</div>
                <h3 className="font-semibold text-slate-900 mb-2">{feature.title}</h3>
                <p className="text-sm text-slate-600">{feature.description}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </div>

      {/* Fullscreen Modal */}
      {isFullscreen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black z-50 flex items-center justify-center p-4"
          onClick={() => setIsFullscreen(false)}
        >
          <div className="w-full h-full max-w-6xl max-h-[90vh]" onClick={(e) => e.stopPropagation()}>
            <div className="absolute top-4 right-4 z-10">
              <Button
                variant="outline"
                onClick={() => setIsFullscreen(false)}
                className="bg-white/90 backdrop-blur-sm border-slate-300"
              >
                Exit Fullscreen
              </Button>
            </div>
            <ModelViewer 
              modelType={scanData.modelType}
              className="w-full h-full"
            />
          </div>
        </motion.div>
      )}
    </div>
  );
}
