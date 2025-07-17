"use client";

import { motion } from "framer-motion";

interface UploadFormProps {
  scanTitle: string;
  description: string;
  onTitleChange: (title: string) => void;
  onDescriptionChange: (description: string) => void;
}

export function UploadForm({
  scanTitle,
  description,
  onTitleChange,
  onDescriptionChange,
}: UploadFormProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="space-y-6"
    >
      <div className="grid md:grid-cols-2 gap-6">
        {/* Scan Title Input */}
        <div className="space-y-2">
          <label
            htmlFor="scan-title"
            className="block text-sm font-medium text-slate-900"
          >
            Scan Title *
          </label>
          <input
            type="text"
            id="scan-title"
            value={scanTitle}
            onChange={(e) => onTitleChange(e.target.value)}
            placeholder="e.g., Vintage Sneaker, Coffee Mug, etc."
            className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all placeholder-slate-400 text-slate-900"
            required
          />
          <p className="text-xs text-slate-500">
            Give your scan a descriptive name
          </p>
        </div>

        {/* Category Selection */}
        <div className="space-y-2">
          <label
            htmlFor="scan-category"
            className="block text-sm font-medium text-slate-900"
          >
            Category
          </label>
          <select
            id="scan-category"
            className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white text-slate-900"
          >
            <option value="">Select a category</option>
            <option value="product">Product</option>
            <option value="furniture">Furniture</option>
            <option value="art">Art & Collectibles</option>
            <option value="prototype">Prototype</option>
            <option value="other">Other</option>
          </select>
          <p className="text-xs text-slate-500">
            Help organize your scans
          </p>
        </div>
      </div>

      {/* Description Textarea */}
      <div className="space-y-2">
        <label
          htmlFor="scan-description"
          className="block text-sm font-medium text-slate-900"
        >
          Description
          <span className="text-slate-500 font-normal ml-1">(optional)</span>
        </label>
        <textarea
          id="scan-description"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="Add any additional details about your scan..."
          rows={4}
          className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all placeholder-slate-400 resize-none text-slate-900"
        />
        <div className="flex justify-between text-xs text-slate-500">
          <span>Provide context or notes about your scan</span>
          <span>{description.length}/500</span>
        </div>
      </div>

      {/* Privacy & Sharing Options */}
      <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
        <h4 className="font-medium text-slate-900 mb-3">Sharing Options</h4>
        <div className="space-y-3">
          <label className="flex items-center">
            <input
              type="radio"
              name="privacy"
              value="private"
              defaultChecked
              className="w-4 h-4 text-blue-600 border-slate-300 focus:ring-blue-500"
            />
            <div className="ml-3">
              <div className="text-sm font-medium text-slate-900">Private</div>
              <div className="text-xs text-slate-500">Only you can view this scan</div>
            </div>
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              name="privacy"
              value="public"
              className="w-4 h-4 text-blue-600 border-slate-300 focus:ring-blue-500"
            />
            <div className="ml-3">
              <div className="text-sm font-medium text-slate-900">Public</div>
              <div className="text-xs text-slate-500">Anyone with the link can view</div>
            </div>
          </label>
        </div>
      </div>

      {/* Processing Options */}
      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
        <h4 className="font-medium text-slate-900 mb-3 flex items-center">
          <div className="w-2 h-2 bg-blue-600 rounded-full mr-2"></div>
          Processing Quality
        </h4>
        <div className="space-y-2">
          <label className="flex items-center">
            <input
              type="radio"
              name="quality"
              value="standard"
              defaultChecked
              className="w-4 h-4 text-blue-600 border-slate-300 focus:ring-blue-500"
            />
            <div className="ml-3">
              <div className="text-sm font-medium text-slate-900">Standard Quality</div>
              <div className="text-xs text-slate-500">~2-3 minutes processing time</div>
            </div>
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              name="quality"
              value="high"
              className="w-4 h-4 text-blue-600 border-slate-300 focus:ring-blue-500"
            />
            <div className="ml-3">
              <div className="text-sm font-medium text-slate-900">High Quality</div>
              <div className="text-xs text-slate-500">~5-7 minutes processing time</div>
            </div>
          </label>
        </div>
      </div>
    </motion.div>
  );
}