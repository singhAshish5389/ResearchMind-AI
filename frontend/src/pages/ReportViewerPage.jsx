import React from "react";
import { Link } from "react-router-dom";
import { FileText } from "lucide-react";

export default function ReportViewerPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-96 gap-4 animate-fadeIn">
      <div className="w-16 h-16 bg-violet-600/20 border border-violet-500/30 rounded-2xl flex items-center justify-center">
        <FileText size={28} className="text-violet-400" />
      </div>
      <h1 className="text-2xl font-bold text-slate-100">Report Viewer</h1>
      <p className="text-slate-400 text-center max-w-md">
        Professional research reports with PDF export will be available after the full agent pipeline is complete (Phase 6).
      </p>
      <Link to="/dashboard" className="btn-primary">Back to Dashboard</Link>
    </div>
  );
}
