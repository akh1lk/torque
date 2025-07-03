"use client";

import { Button } from "./ui/button";
import Link from "next/link";

export const Navbar = () => {
  return (
    <nav className="absolute top-0 left-0 right-0 z-50 bg-transparent">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center">
          <img 
            src="/torqueicon.png" 
            alt="torque"
            style={{ height: '60px', width: 'auto' }}
          />
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
          <Link href="/login">
            <Button variant="outline" className="text-black hover:text-white border-slate-300 hover:border-slate-400">
              Login
            </Button>
          </Link>
          <Link href="/signup">
            <Button className="bg-gradient-to-r from-slate-900 to-blue-900 hover:from-slate-800 hover:to-blue-800 text-white">
              Get Started
            </Button>
          </Link>
        </div>
      </div>
    </nav>
  );
};
