"use client";

import { useState } from "react";
import { Navbar } from "@/components/navbar";
import { FileDropzone } from "@/components/FileDropzone";
import { UploadForm } from "@/components/UploadForm";
import { Button } from "@/components/ui/button";
import { Upload, CheckCircle } from "lucide-react";
import { motion } from "framer-motion";

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [scanTitle, setScanTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const isFormValid = selectedFile && scanTitle.trim().length > 0;

  const handleFileSelect = (file: File | null) => {
    setSelectedFile(file);
    setUploadSuccess(false);
  };

  const handleUpload = async () => {
    if (!isFormValid) return;

    setIsUploading(true);
    setUploadProgress(0);

    // Simulate upload progress
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          return 100;
        }
        return prev + Math.random() * 15;
      });
    }, 150);

    // Simulate upload completion after 2 seconds
    setTimeout(() => {
      clearInterval(progressInterval);
      setUploadProgress(100);
      setIsUploading(false);
      setUploadSuccess(true);
      
      // Show success message
      alert("Upload successful! Your scan is being processed.");
    }, 2000);
  };

  const resetForm = () => {
    setSelectedFile(null);
    setScanTitle("");
    setDescription("");
    setUploadProgress(0);
    setUploadSuccess(false);
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      <div className="pt-24 pb-12">
        <div className="container mx-auto px-4 max-w-4xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <h1 className="text-4xl lg:text-5xl font-bold mb-4 text-slate-900">
              Upload a Scan
            </h1>
            <p className="text-xl text-slate-600 max-w-2xl mx-auto">
              Drag and drop your video file or select it manually. We will transform it into a stunning 3D model.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="bg-white rounded-2xl border border-slate-200 shadow-lg p-8"
          >
            {!uploadSuccess ? (
              <div className="space-y-8">
                <FileDropzone
                  selectedFile={selectedFile}
                  onFileSelect={handleFileSelect}
                />

                <UploadForm
                  scanTitle={scanTitle}
                  description={description}
                  onTitleChange={setScanTitle}
                  onDescriptionChange={setDescription}
                />

                {isUploading && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    className="space-y-3"
                  >
                    <div className="flex items-center justify-between text-sm text-slate-600">
                      <span>Uploading...</span>
                      <span>{Math.round(uploadProgress)}%</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-2">
                      <motion.div
                        className="bg-gradient-to-r from-slate-900 to-blue-900 h-2 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${uploadProgress}%` }}
                        transition={{ duration: 0.3 }}
                      />
                    </div>
                  </motion.div>
                )}

                <Button
                  onClick={handleUpload}
                  disabled={!isFormValid || isUploading}
                  size="lg"
                  className="w-full text-lg py-6 bg-gradient-to-r from-slate-900 to-blue-900 hover:from-slate-800 hover:to-blue-800 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isUploading ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="w-5 h-5 mr-2" />
                      Upload Scan
                    </>
                  )}
                </Button>
              </div>
            ) : (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5 }}
                className="text-center py-8"
              >
                <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                  <CheckCircle className="w-10 h-10 text-green-600" />
                </div>
                <h2 className="text-2xl font-bold text-slate-900 mb-4">
                  Upload Successful!
                </h2>
                <p className="text-slate-600 mb-8 max-w-md mx-auto">
                  Your scan "{scanTitle}" has been uploaded successfully. We are now processing your video to create a 3D model.
                </p>
                <div className="space-y-4">
                  <Button
                    onClick={resetForm}
                    variant="outline"
                    size="lg"
                    className="mr-4"
                  >
                    Upload Another Scan
                  </Button>
                  <Button
                    size="lg"
                    className="bg-gradient-to-r from-slate-900 to-blue-900 hover:from-slate-800 hover:to-blue-800 text-white"
                  >
                    View My Scans
                  </Button>
                </div>
              </motion.div>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="mt-12 grid md:grid-cols-3 gap-6"
          >
            {[
              {
                title: "Video Tips",
                description: "Record a 360° video around your object. Keep it steady and well-lit."
              },
              {
                title: "Best Results",
                description: "Use videos under 10 seconds with clear focus on the subject."
              },
              {
                title: "File Formats",
                description: "Supports MP4, MOV, and AVI files up to 100MB in size."
              }
            ].map((tip, index) => (
              <div
                key={index}
                className="bg-slate-50 rounded-xl p-6 border border-slate-200"
              >
                <h3 className="font-semibold text-slate-900 mb-2">{tip.title}</h3>
                <p className="text-sm text-slate-600">{tip.description}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
