"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { useState, useEffect } from "react";
import { 
  Play, 
  Upload, 
  Sparkles, 
  ArrowRight, 
  ChevronDown,
  Palette,
  Hammer,
  GraduationCap,
  Building,
  Github,
  Twitter,
  Mail,
  Monitor
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Navbar } from "@/components/navbar";
import GradientText from "@/components/GradientText";

// 3D Model Viewer Component (placeholder)
const ModelViewer = ({ modelName }: { modelName: string }) => {
  return (
    <div className="w-full h-64 bg-white rounded-lg border border-slate-200 flex items-center justify-center relative overflow-hidden shadow-lg">
      <div className="absolute inset-0 bg-gradient-to-r from-slate-50 to-blue-50" />
      <motion.div
        animate={{ 
          rotateY: 360,
          scale: [1, 1.1, 1]
        }}
        transition={{ 
          rotateY: { duration: 20, repeat: Infinity, ease: "linear" },
          scale: { duration: 2, repeat: Infinity, ease: "easeInOut" }
        }}
        className="w-24 h-24 bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 rounded-lg flex items-center justify-center text-white font-semibold text-sm shadow-2xl"
      >
        {modelName}
      </motion.div>
      <div className="absolute bottom-4 left-4 text-xs text-slate-600">
        Interactive 3D Model
      </div>
    </div>
  );
};

export default function Page() {
  const [selectedModel, setSelectedModel] = useState("Shoe");
  const [showDemoModal, setShowDemoModal] = useState(false);
  
  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowDemoModal(false);
      }
    };
    
    if (showDemoModal) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [showDemoModal]);
  
  const models = ["Shoe", "Desk Setup", "Corner Room"];
  
  const useCases = [
    {
      icon: Building,
      title: "Real Estate",
      description: "Model specific fixtures, appliances, or furniture pieces for detailed property listings"
    },
    {
      icon: Palette,
      title: "Product Design",
      description: "Quickly capture prototypes, samples, or reference objects for design iteration"
    },
    {
      icon: Monitor,
      title: "E-commerce",
      description: "Create interactive 3D views of products for online stores and marketplaces"
    },
    {
      icon: GraduationCap,
      title: "Education",
      description: "Digitize artifacts, specimens, or tools for interactive learning experiences"
    }
  ];

  return (
    <div className="min-h-screen bg-orange-50 text-slate-900">
      
      {/* Navbar */}
      <Navbar />
      
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-12">
        {/* Background Image */}
        <div 
          className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-50"
          style={{ backgroundImage: 'url(/landinggradientbg.png)' }}
        />
        <div className="container mx-auto px-4 grid lg:grid-cols-2 gap-8 items-center relative z-10">
          {/* Left Side - Content */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
            className="space-y-8"
          >
           
            
            <div className="space-y-4">
              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="text-5xl lg:text-7xl font-bold tracking-tight text-black-900"
              >
                Turn Videos Into{" "}
                <GradientText
                  colors={["#0f172a", "#1e3a8a", "#1e293b", "#dc2626", "#ea580c", "#1e3a8a", "#0f172a"]}
                  animationSpeed={8}
                  showBorder={false}
                  className="text-6xl lg:text-8xl"
                >
                  3D Models
                </GradientText>{" "}
                <em>Seamlessly.</em>
              </motion.h1>
              
              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="text-xl text-slate-600 max-w-lg"
              >
                Upload a clip. Get a 3D model. No fancy app, no LiDAR.
              </motion.p>
            </div>
            
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="flex flex-col sm:flex-row gap-4"
            >
              <Link href="/signup">
                <Button size="lg" className="text-lg px-8 py-6 bg-gradient-to-r from-slate-900 to-blue-900 hover:from-slate-800 hover:to-blue-800 text-white border-0 shadow-lg">
                  Get started free
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
              <Button 
                variant="outline" 
                size="lg" 
                className="text-lg px-8 py-6 bg-white text-black border-slate-300 hover:bg-white hover:border-blue-500 hover:shadow-[0_0_20px_rgba(59,130,246,0.6)] hover:text-black transition-all duration-300"
                onClick={() => setShowDemoModal(true)}
              >
                <Play className="mr-2 w-5 h-5" />
                Watch demo
              </Button>
            </motion.div>
          </motion.div>
          
          {/* Right Side - 3D Preview */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="relative"
          >
            <div className="relative w-full h-96 bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-lg backdrop-blur-sm">
              <div className="absolute inset-0 bg-gradient-to-r from-slate-50 to-blue-50" />
              
              {/* Animated 3D Model Placeholder */}
              <motion.div
                animate={{ 
                  rotateY: 360,
                  rotateX: [0, 10, 0, -10, 0]
                }}
                transition={{ 
                  rotateY: { duration: 20, repeat: Infinity, ease: "linear" },
                  rotateX: { duration: 4, repeat: Infinity, ease: "easeInOut" }
                }}
                className="absolute inset-0 flex items-center justify-center"
              >
                <div className="w-32 h-32 bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 rounded-lg flex items-center justify-center text-white font-bold text-lg shadow-2xl">
                  3D
                </div>
              </motion.div>
              
              {/* Scanning Effect */}
              <motion.div
                animate={{ x: [-100, 400] }}
                transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                className="absolute top-0 bottom-0 w-1 bg-gradient-to-b from-transparent via-slate-900 to-transparent opacity-60"
              />
              
              <div className="absolute bottom-4 left-4 text-sm text-slate-600">
                Live 3D Preview
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-8 relative">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-12"
          >
            <h2 className="text-4xl lg:text-5xl font-bold mb-4 text-slate-900">
              How It Works
            </h2>
          </motion.div>
          
          <div className="flex flex-col md:flex-row items-center justify-center max-w-5xl mx-auto">
            {[
              {
                step: "1",
                title: "Upload",
                description: "Drop in a 10-second video of your subject from all angles"
              },
              {
                step: "2", 
                title: "Process",
                description: "An ML Model creates a 3D Gausssian Splats of your object"
              },
              {
                step: "3",
                title: "Share",
                description: "Get a link to view and interact with your 3D creation. Export it to .splat and .ply"
              }
            ].map((item, index) => (
              <div key={index} className="flex items-center">
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.6, delay: index * 0.2 }}
                  viewport={{ once: true }}
                  className="flex items-start text-left max-w-xs"
                >
                  {/* Step Number */}
                  <div className="text-6xl font-bold bg-gradient-to-r from-slate-900 via-blue-900 to-slate-800 bg-clip-text text-transparent mr-6">
                    {item.step}
                  </div>
                  
                  {/* Step Content */}
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-slate-900 mb-2">
                      {item.title}
                    </h3>
                    <p className="text-slate-600 text-sm leading-relaxed">
                      {item.description}
                    </p>
                  </div>
                </motion.div>
                
                {/* Curvy Dotted Connector Line */}
                {index < 2 && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    transition={{ duration: 1.0, delay: (index + 1) * 0.3 }}
                    viewport={{ once: true }}
                    className="hidden md:flex mx-8 lg:mx-12 items-center"
                  >
                    <svg
                      width="140"
                      height="60"
                      viewBox="0 0 140 60"
                      className="overflow-visible"
                    >
                      <motion.path
                        d="M 10 30 Q 35 10 70 30 Q 105 50 130 30"
                        fill="none"
                        stroke={`url(#curveGradient-${index})`}
                        strokeWidth="2.5"
                        strokeDasharray="6,6"
                        strokeLinecap="round"
                        initial={{ pathLength: 0 }}
                        whileInView={{ pathLength: 1 }}
                        transition={{ duration: 1.5, delay: (index + 1) * 0.4, ease: "easeInOut" }}
                        viewport={{ once: true }}
                      />
                      <defs>
                        <linearGradient id={`curveGradient-${index}`} x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#1e293b" />
                          <stop offset="50%" stopColor="#1e3a8a" />
                          <stop offset="100%" stopColor="#1f2937" />
                        </linearGradient>
                      </defs>
                    </svg>
                  </motion.div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section id="use-cases" className="py-16 relative">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-12"
          >
            <h2 className="text-4xl lg:text-5xl font-bold mb-4 text-slate-900">Who Uses Torque</h2>
            <p className="text-xl text-slate-600">
              Perfect for capturing detailed 3D models of specific objects and assets
            </p>
          </motion.div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
            {useCases.map((useCase, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                viewport={{ once: true }}
                whileHover={{ y: -5 }}
                className="bg-white rounded-xl p-6 border border-slate-200 hover:border-slate-300 transition-all shadow-lg hover:shadow-xl"
              >
                <div className="w-12 h-12 bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 rounded-lg flex items-center justify-center mb-4">
                  <useCase.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold mb-2 text-slate-900">{useCase.title}</h3>
                <p className="text-slate-600 text-sm">{useCase.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Live Demo Section */}
      <section id="demo" className="py-16 relative">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-12"
          >
            <h2 className="text-4xl lg:text-5xl font-bold mb-4 text-slate-900">Explore a Sample Scan</h2>
            <p className="text-xl text-slate-600">
              See the quality and detail of Torque-generated 3D models
            </p>
          </motion.div>
          
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            viewport={{ once: true }}
            className="max-w-4xl mx-auto"
          >
            {/* Model Selector */}
            <div className="flex justify-center mb-8">
              <div className="inline-flex items-center bg-white backdrop-blur-sm rounded-lg p-1 border border-slate-200 shadow-lg">
                {models.map((model) => (
                  <button
                    key={model}
                    onClick={() => setSelectedModel(model)}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                      selectedModel === model
                        ? "bg-gradient-to-r from-slate-900 to-blue-900 text-white shadow-sm"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    {model}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Model Viewer */}
            <motion.div
              key={selectedModel}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
            >
              <ModelViewer modelName={selectedModel} />
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 py-12 relative">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8">
            {/* Logo & Tagline */}
            <div className="md:col-span-2">
              <Link href="/" className="inline-flex items-center mb-4">
                <img 
                  src="/torqueicon.png" 
                  alt="Torque" 
                  style={{ height: '40px', width: 'auto' }}
                />
              </Link>
              <p className="text-slate-600 mb-6 max-w-md">
                Simple scans. Stunning results.
              </p>
              <div className="flex space-x-4">
                <Button variant="ghost" size="sm" className="text-slate-600 hover:text-slate-900 hover:bg-slate-100">
                  <Github className="w-4 h-4" />
                </Button>
                <Button variant="ghost" size="sm" className="text-slate-600 hover:text-slate-900 hover:bg-slate-100">
                  <Twitter className="w-4 h-4" />
                </Button>
                <Button variant="ghost" size="sm" className="text-slate-600 hover:text-slate-900 hover:bg-slate-100">
                  <Mail className="w-4 h-4" />
                </Button>
              </div>
            </div>
            
            {/* Navigation Links */}
            <div>
              <h4 className="font-semibold mb-4 text-slate-900">Product</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li><Link href="#" className="hover:text-slate-900 transition-colors">About</Link></li>
                <li><Link href="#" className="hover:text-slate-900 transition-colors">Features</Link></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4 text-slate-900">Support</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li><Link href="#" className="hover:text-slate-900 transition-colors">Contact</Link></li>
                <li><Link href="#" className="hover:text-slate-900 transition-colors">Help</Link></li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-slate-200 mt-12 pt-8 text-center text-sm text-slate-600">
            <p>&copy; 2025 Torque. All rights reserved.</p>
          </div>
        </div>
      </footer>

      {/* Demo Modal */}
      {showDemoModal && (
        <div 
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setShowDemoModal(false)}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-slate-200">
              <h3 className="text-2xl font-bold text-slate-900">Torque Demo</h3>
              <button 
                onClick={() => setShowDemoModal(false)}
                className="p-2 hover:bg-slate-100 rounded-full transition-colors"
              >
                <svg className="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            {/* Modal Content */}
            <div className="p-6">
              <div className="aspect-video bg-gradient-to-br from-slate-50 to-blue-50 rounded-xl flex items-center justify-center mb-6">
                <div className="text-center">
                  <div className="w-20 h-20 bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 rounded-full flex items-center justify-center mb-4 mx-auto">
                    <Play className="w-8 h-8 text-white ml-1" />
                  </div>
                  <h4 className="text-xl font-semibold mb-2 text-slate-900">Interactive Demo Video</h4>
                  <p className="text-slate-600 mb-4">See how Torque transforms a simple phone video into a stunning 3D model</p>
                  <Button className="bg-gradient-to-r from-slate-900 to-blue-900 hover:from-slate-800 hover:to-blue-800 text-white">
                    <Play className="w-4 h-4 mr-2" />
                    Play Demo
                  </Button>
                </div>
              </div>
              
              <div className="grid md:grid-cols-3 gap-4 text-sm">
                <div className="text-center p-4 bg-slate-50 rounded-lg">
                  <div className="w-8 h-8 bg-gradient-to-br from-slate-900 to-blue-900 rounded-full flex items-center justify-center text-white font-bold mx-auto mb-2">1</div>
                  <h5 className="font-semibold mb-1 text-slate-900">Upload Video</h5>
                  <p className="text-slate-600">Record a 360° video with your phone up to 10s</p>
                </div>
                <div className="text-center p-4 bg-slate-50 rounded-lg">
                  <div className="w-8 h-8 bg-gradient-to-br from-slate-900 to-blue-900 rounded-full flex items-center justify-center text-white font-bold mx-auto mb-2">2</div>
                  <h5 className="font-semibold mb-1 text-slate-900">Neural Gaussian Splatting</h5>
                  <p className="text-slate-600">We use a pretrained model to create splats</p>
                </div>
                <div className="text-center p-4 bg-slate-50 rounded-lg">
                  <div className="w-8 h-8 bg-gradient-to-br from-slate-900 to-blue-900 rounded-full flex items-center justify-center text-white font-bold mx-auto mb-2">3</div>
                  <h5 className="font-semibold mb-1 text-slate-900">3D Model</h5>
                  <p className="text-slate-600">Explore and share your interactive 3D model</p>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
