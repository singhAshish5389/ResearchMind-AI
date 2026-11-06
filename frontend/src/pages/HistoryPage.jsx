import React from "react";
import { Link } from "react-router-dom";
import { History, Construction } from "lucide-react";

export default function HistoryPage() {
  return (
    <div className="max-w-4xl mx-auto animate-slideUp">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-100">Research History</h1>
        <p className="text-slate-400 mt-1">Your past research projects and reports</p>
      </div>
      <div className="glass-card p-12 flex flex-col items-center gap-4 text-center">
        <div className="w-16 h-16 bg-surface-300 rounded-2xl flex items-center justify-center">
          <History size={28} className="text-slate-500" />
        </div>
        <h2 className="text-xl font-semibold text-slate-300">No research yet</h2>
        <p className="text-slate-500 max-w-sm">
          Your completed research projects will appear here. Start your first research to get going.
        </p>
        <Link to="/research/new" className="btn-primary mt-2">Start New Research</Link>
        <p className="text-xs text-slate-600 mt-2">Full persistence coming in Phase 6 (PostgreSQL)</p>
      </div>
    </div>
  );
}
