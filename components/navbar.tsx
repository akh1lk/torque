"use client";

import { Button } from "./ui/button";
import Link from "next/link";
import Image from "next/image";

export const Navbar = () => {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center space-x-2">
          <Image 
            src="/TorqueIcon.svg" 
            alt="Torque" 
            width={32} 
            height={32}
            className="w-8 h-8"
          />
          <span className="text-xl font-bold text-slate-900">Torque</span>
        </Link>

        {/* Navigation Links */}
        <div className="hidden md:flex items-center space-x-8">
          <Link href="#how-it-works" className="text-slate-600 hover:text-slate-900 transition-colors">
            How It Works
          </Link>
          <Link href="#use-cases" className="text-slate-600 hover:text-slate-900 transition-colors">
            Use Cases
          </Link>
          <Link href="#demo" className="text-slate-600 hover:text-slate-900 transition-colors">
            Demo
          </Link>
          <Link href="/chat" className="text-slate-600 hover:text-slate-900 transition-colors">
            Chat
          </Link>
        </div>

        {/* CTA Buttons */}
        <div className="flex items-center space-x-3">
          <Button variant="outline" className="text-white hover:text-white border-slate-300 hover:border-slate-400">
            Login
          </Button>
          <Button className="bg-gradient-to-r from-slate-900 to-blue-900 hover:from-slate-800 hover:to-blue-800 text-white">
            Get Started
          </Button>
        </div>
      </div>
    </nav>
  );
};
