"use client";

import { Suspense, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Environment, ContactShadows, Text } from "@react-three/drei";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import * as THREE from "three";

// Placeholder 3D Model Component
const PlaceholderModel = ({ modelType = "chair" }: { modelType?: string }) => {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  
  useFrame((state) => {
    const ref = modelType === "cube" ? meshRef : groupRef;
    if (ref.current) {
      ref.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.1;
    }
  });

  const renderModel = () => {
    switch (modelType) {
      case "chair":
        return (
          <group ref={groupRef}>
            {/* Chair seat */}
            <mesh position={[0, 0.5, 0]}>
              <boxGeometry args={[1.2, 0.1, 1.2]} />
              <meshStandardMaterial color="#8b5a3c" />
            </mesh>
            {/* Chair back */}
            <mesh position={[0, 1.2, -0.55]}>
              <boxGeometry args={[1.2, 1.4, 0.1]} />
              <meshStandardMaterial color="#8b5a3c" />
            </mesh>
            {/* Chair legs */}
            {[
              [-0.5, 0, -0.5],
              [0.5, 0, -0.5],
              [-0.5, 0, 0.5],
              [0.5, 0, 0.5],
            ].map((position, index) => (
              <mesh key={index} position={position as [number, number, number]}>
                <cylinderGeometry args={[0.05, 0.05, 1]} />
                <meshStandardMaterial color="#654321" />
              </mesh>
            ))}
          </group>
        );
      case "desk":
        return (
          <group ref={groupRef}>
            {/* Desk top */}
            <mesh position={[0, 0.8, 0]}>
              <boxGeometry args={[2.5, 0.1, 1.2]} />
              <meshStandardMaterial color="#d4a574" />
            </mesh>
            {/* Desk legs */}
            {[
              [-1.1, 0.4, -0.5],
              [1.1, 0.4, -0.5],
              [-1.1, 0.4, 0.5],
              [1.1, 0.4, 0.5],
            ].map((position, index) => (
              <mesh key={index} position={position as [number, number, number]}>
                <boxGeometry args={[0.1, 0.8, 0.1]} />
                <meshStandardMaterial color="#8b4513" />
              </mesh>
            ))}
          </group>
        );
      case "room":
        return (
          <group ref={groupRef}>
            {/* Floor */}
            <mesh position={[0, -0.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
              <planeGeometry args={[4, 4]} />
              <meshStandardMaterial color="#e8e8e8" />
            </mesh>
            {/* Walls */}
            <mesh position={[0, 1, -2]}>
              <planeGeometry args={[4, 3]} />
              <meshStandardMaterial color="#f5f5f5" />
            </mesh>
            <mesh position={[-2, 1, 0]} rotation={[0, Math.PI / 2, 0]}>
              <planeGeometry args={[4, 3]} />
              <meshStandardMaterial color="#f0f0f0" />
            </mesh>
            {/* Simple furniture */}
            <mesh position={[-1, 0.2, -1.5]}>
              <boxGeometry args={[0.8, 0.4, 0.4]} />
              <meshStandardMaterial color="#8b5a3c" />
            </mesh>
          </group>
        );
      default:
        return (
          <mesh ref={meshRef}>
            <boxGeometry args={[1, 1, 1]} />
            <meshStandardMaterial 
              color="#3b82f6" 
              metalness={0.3}
              roughness={0.4}
            />
          </mesh>
        );
    }
  };

  return renderModel();
};

// Loading Component
const LoadingFallback = () => (
  <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-slate-50 to-blue-50">
    <div className="text-center">
      <Loader2 className="w-8 h-8 animate-spin text-slate-600 mx-auto mb-2" />
      <p className="text-sm text-slate-600">Loading 3D model...</p>
    </div>
  </div>
);

// Error Fallback Component
const ErrorFallback = ({ error }: { error?: string }) => (
  <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-red-50 to-slate-50">
    <div className="text-center">
      <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-slate-900 mb-2">Failed to load 3D model</h3>
      <p className="text-sm text-slate-600">{error || "An error occurred while loading the model"}</p>
    </div>
  </div>
);

interface ModelViewerProps {
  modelType?: "chair" | "desk" | "room" | "cube";
  className?: string;
  showControls?: boolean;
}

export function ModelViewer({ 
  modelType = "chair", 
  className = "",
  showControls = true 
}: ModelViewerProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Simulate loading time
  useState(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 1500);
    return () => clearTimeout(timer);
  });

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className={`relative w-full h-[500px] bg-white rounded-xl border border-slate-200 shadow-lg overflow-hidden ${className}`}
    >
      {/* Loading State */}
      {isLoading && <LoadingFallback />}
      
      {/* Error State */}
      {error && <ErrorFallback error={error} />}
      
      {/* 3D Canvas */}
      {!isLoading && !error && (
        <Canvas
          camera={{ 
            position: [3, 2, 3], 
            fov: 50,
            near: 0.1,
            far: 100
          }}
          shadows
          className="w-full h-full"
          onCreated={(state) => {
            state.gl.setClearColor('#f8fafc');
          }}
        >
          <Suspense fallback={null}>
            {/* Lighting */}
            <ambientLight intensity={0.6} />
            <directionalLight 
              position={[5, 5, 5]} 
              intensity={1}
              castShadow
              shadow-mapSize={[1024, 1024]}
            />
            <pointLight position={[-3, 3, -3]} intensity={0.4} />
            
            {/* Environment */}
            <Environment preset="studio" />
            
            {/* 3D Model */}
            <PlaceholderModel modelType={modelType} />
            
            {/* Ground Shadow */}
            <ContactShadows 
              opacity={0.4} 
              scale={5} 
              blur={2} 
              far={4} 
              resolution={256} 
              color="#000000" 
            />
            
            {/* Controls */}
            {showControls && (
              <OrbitControls
                enablePan={true}
                enableZoom={true}
                enableRotate={true}
                minDistance={1}
                maxDistance={8}
                minPolarAngle={0}
                maxPolarAngle={Math.PI / 2}
              />
            )}
          </Suspense>
        </Canvas>
      )}
      
      {/* Controls Info */}
      {!isLoading && !error && showControls && (
        <div className="absolute bottom-4 left-4 bg-black/70 text-white text-xs px-3 py-2 rounded-lg backdrop-blur-sm">
          <p>Click + drag to rotate • Scroll to zoom • Right-click + drag to pan</p>
        </div>
      )}
      
      {/* Model Type Label */}
      {!isLoading && !error && (
        <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-sm text-slate-700 text-sm px-3 py-1 rounded-full border border-slate-200">
          {modelType.charAt(0).toUpperCase() + modelType.slice(1)} Model
        </div>
      )}
    </motion.div>
  );
}
