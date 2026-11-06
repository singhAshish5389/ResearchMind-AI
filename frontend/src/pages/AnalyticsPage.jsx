import React from "react";
import { BarChart2 } from "lucide-react";

export default function AnalyticsPage() {
  return (
    <div className="max-w-6xl mx-auto animate-slideUp">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-100">Analytics</h1>
        <p className="text-slate-400 mt-1">Research activity, source quality, and API usage</p>
      </div>
      <div className="glass-card p-12 flex flex-col items-center gap-4 text-center">
        <div className="w-16 h-16 bg-cyan-500/10 border border-cyan-500/20 rounded-2xl flex items-center justify-center">
          <BarChart2 size={28} className="text-cyan-400" />
        </div>
        <h2 className="text-xl font-semibold text-slate-300">Analytics dashboard coming soon</h2>
        <p className="text-slate-500 max-w-sm">
          Real analytics powered by Recharts will be available in Phase 8 after research data is being persisted.
        </p>
      </div>
    </div>
  );
}
