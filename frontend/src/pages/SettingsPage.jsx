import React from "react";
import { Settings } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="max-w-2xl mx-auto animate-slideUp">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-100">Settings</h1>
        <p className="text-slate-400 mt-1">Manage your account and preferences</p>
      </div>
      <div className="glass-card p-12 flex flex-col items-center gap-4 text-center">
        <div className="w-16 h-16 bg-slate-600/20 border border-slate-500/20 rounded-2xl flex items-center justify-center">
          <Settings size={28} className="text-slate-400" />
        </div>
        <h2 className="text-xl font-semibold text-slate-300">Settings coming soon</h2>
        <p className="text-slate-500 max-w-sm">
          User profile, API preferences, notification settings, and theme options will be available in Phase 6.
        </p>
      </div>
    </div>
  );
}
