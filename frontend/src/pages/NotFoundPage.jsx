import React from "react";
import { Link } from "react-router-dom";
import { Brain } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-surface flex flex-col items-center justify-center gap-6 px-4 text-center">
      <div className="w-20 h-20 bg-primary-600/20 border border-primary-500/30 rounded-3xl flex items-center justify-center">
        <Brain size={36} className="text-primary-400" />
      </div>
      <div>
        <h1 className="text-8xl font-black gradient-text mb-4">404</h1>
        <h2 className="text-2xl font-bold text-slate-100 mb-2">Page Not Found</h2>
        <p className="text-slate-400 max-w-md">
          The page you are looking for does not exist or has been moved.
        </p>
      </div>
      <div className="flex gap-3">
        <Link to="/" className="btn-secondary">Home</Link>
        <Link to="/dashboard" className="btn-primary">Dashboard</Link>
      </div>
    </div>
  );
}
