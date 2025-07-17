"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Plus, Search, Filter, Grid3X3, List } from "lucide-react";
import { Navbar } from "@/components/navbar";
import { ScanCard, Scan } from "@/components/ScanCard";
import { Button } from "@/components/ui/button";

// Mock data for scans
const dummyScans: Scan[] = [
  {
    id: "studio-desk-june-2024",
    title: "Studio A — April 9",
    date: "April 9, 2025",
    status: "complete",
    thumbnail: undefined
  },
  {
    id: "vintage-chair",
    title: "Vintage Camera Collection",
    date: "April 8, 2025",
    status: "processing",
    processingProgress: 67
  },
  {
    id: "corner-room-scan",
    title: "Office Chair Prototype",
    date: "April 7, 2025",
    status: "complete",
    thumbnail: undefined
  },
  {
    id: "processing-scan",
    title: "Ceramic Vase Series",
    date: "April 6, 2025",
    status: "failed",
    thumbnail: undefined
  },
  {
    id: "sneaker-design",
    title: "Sneaker Design Mockup",
    date: "April 5, 2025",
    status: "processing",
    processingProgress: 23
  },
  {
    id: "art-sculpture",
    title: "Art Sculpture — Bronze",
    date: "April 4, 2025",
    status: "complete",
    thumbnail: undefined
  },
  {
    id: "kitchen-appliance",
    title: "Kitchen Appliance Test",
    date: "April 3, 2025",
    status: "complete",
    thumbnail: undefined
  },
  {
    id: "jewelry-collection",
    title: "Jewelry Collection",
    date: "April 2, 2025",
    status: "processing",
    processingProgress: 89
  }
];

export default function DashboardPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [filterStatus, setFilterStatus] = useState<string>("all");

  // Filter scans based on search and status
  const filteredScans = dummyScans.filter(scan => {
    const matchesSearch = scan.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === "all" || scan.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const getStatusCounts = () => {
    return {
      all: dummyScans.length,
      complete: dummyScans.filter(s => s.status === "complete").length,
      processing: dummyScans.filter(s => s.status === "processing").length,
      failed: dummyScans.filter(s => s.status === "failed").length
    };
  };

  const statusCounts = getStatusCounts();

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      
      <div className="pt-24 pb-12">
        <div className="container mx-auto px-4 max-w-7xl">
          {/* Header Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="flex flex-col md:flex-row md:items-center md:justify-between mb-8"
          >
            <div>
              <h1 className="text-4xl lg:text-5xl font-bold mb-2 text-slate-900">
                Your Scans
              </h1>
              <p className="text-xl text-slate-600">
                Manage and view your 3D scan collection
              </p>
              <p className="text-lg text-black mt-1">
                @akhil
              </p>
            </div>
            
            <div className="mt-6 md:mt-0">
              <Link href="/upload">
                <Button 
                  size="lg"
                  className="bg-gradient-to-r from-slate-900 to-blue-900 hover:from-slate-800 hover:to-blue-800 text-white shadow-lg"
                >
                  <Plus className="w-5 h-5 mr-2" />
                  New Scan
                </Button>
              </Link>
            </div>
          </motion.div>

          {/* Search and Filter Bar */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 mb-8"
          >
            <div className="flex flex-col lg:flex-row gap-4 lg:items-center lg:justify-between">
              {/* Search */}
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
                <input
                  type="text"
                  placeholder="Search scans..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-900"
                />
              </div>

              <div className="flex items-center gap-4">
                {/* Status Filter */}
                <div className="flex items-center gap-2">
                  <Filter className="w-4 h-4 text-slate-500" />
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-900"
                  >
                    <option value="all">All ({statusCounts.all})</option>
                    <option value="complete">Complete ({statusCounts.complete})</option>
                    <option value="processing">Processing ({statusCounts.processing})</option>
                    <option value="failed">Failed ({statusCounts.failed})</option>
                  </select>
                </div>

                {/* View Toggle */}
                <div className="flex items-center border border-slate-300 rounded-lg p-1">
                  <button
                    onClick={() => setViewMode("grid")}
                    className={`p-1 rounded ${viewMode === "grid" 
                      ? "bg-slate-900 text-white" 
                      : "text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    <Grid3X3 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setViewMode("list")}
                    className={`p-1 rounded ${viewMode === "list" 
                      ? "bg-slate-900 text-white" 
                      : "text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    <List className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Scans Grid */}
          {filteredScans.length > 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className={`grid gap-6 ${
                viewMode === "grid" 
                  ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
                  : "grid-cols-1"
              }`}
            >
              {filteredScans.map((scan, index) => (
                <ScanCard key={scan.id} scan={scan} index={index} />
              ))}
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="text-center py-16"
            >
              <div className="w-24 h-24 bg-slate-200 rounded-full flex items-center justify-center mx-auto mb-6">
                <Search className="w-12 h-12 text-slate-400" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-2">
                No scans found
              </h3>
              <p className="text-slate-600 mb-6">
                {searchQuery 
                  ? `No scans match "${searchQuery}"`
                  : "You haven't created any scans yet"
                }
              </p>
              {!searchQuery && (
                <Link href="/upload">
                  <Button 
                    size="lg"
                    className="bg-gradient-to-r from-slate-900 to-blue-900 hover:from-slate-800 hover:to-blue-800 text-white"
                  >
                    <Plus className="w-5 h-5 mr-2" />
                    Create Your First Scan
                  </Button>
                </Link>
              )}
            </motion.div>
          )}

          {/* Stats Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-4"
          >
            {[
              { label: "Total Scans", value: statusCounts.all, color: "text-slate-900" },
              { label: "Complete", value: statusCounts.complete, color: "text-green-600" },
              { label: "Processing", value: statusCounts.processing, color: "text-yellow-600" },
              { label: "Failed", value: statusCounts.failed, color: "text-red-600" }
            ].map((stat, index) => (
              <div
                key={index}
                className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 text-center"
              >
                <div className={`text-2xl font-bold mb-1 ${stat.color}`}>
                  {stat.value}
                </div>
                <div className="text-sm text-slate-600">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
