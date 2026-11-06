import React from "react";
import { Link } from "react-router-dom";
import { Construction, Clock } from "lucide-react";

export default function ResearchWorkspacePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-96 gap-4 animate-fadeIn">
      <div className="w-16 h-16 bg-primary-600/20 border border-primary-500/30 rounded-2xl flex items-center justify-center">
        <Clock size={28} className="text-primary-400" />
      </div>
      <h1 className="text-2xl font-bold text-slate-100">Research Workspace</h1>
      <p className="text-slate-400 text-center max-w-md">
        Live agent progress, source discovery, and research execution will be available in Phase 4 (LangGraph workflow).
      </p>
      <Link to="/research/new" className="btn-primary">Start New Research</Link>
    </div>
  );
}
