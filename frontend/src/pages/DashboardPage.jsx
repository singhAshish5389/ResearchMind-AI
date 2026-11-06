/**
 * ResearchMind AI – Dashboard Page
 */

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Brain, PlusCircle, Clock, CheckCircle, AlertCircle, Zap, ArrowRight, Server } from 'lucide-react';
import api from '../services/api.js';

export default function DashboardPage() {
  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);

  useEffect(() => {
    api.health()
      .then(res => setHealth(res.data))
      .catch(() => setHealth({ status: 'offline', services: {} }))
      .finally(() => setHealthLoading(false));
  }, []);

  const serviceStatus = (key) => {
    if (!health?.services) return 'unknown';
    const val = health.services[key] || 'unknown';
    return val;
  };

  const isConfigured = (key) =>
    ['configured', 'url_set', 'enabled'].includes(serviceStatus(key));

  const stats = [
    { label: 'Research Projects', value: '0', icon: Brain, color: 'text-primary-400' },
    { label: 'Completed', value: '0', icon: CheckCircle, color: 'text-emerald-400' },
    { label: 'In Progress', value: '0', icon: Clock, color: 'text-amber-400' },
    { label: 'Failed', value: '0', icon: AlertCircle, color: 'text-red-400' },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-slideUp">
      {/* Welcome header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Dashboard</h1>
          <p className="text-slate-400 mt-1">Welcome to ResearchMind AI – v0.1.0 (Phase 1 + 2)</p>
        </div>
        <Link to="/research/new" className="btn-primary shadow-glow">
          <PlusCircle size={18} /> New Research
        </Link>
      </div>

      {/* System Health */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-5">
          <Server size={18} className="text-primary-400" />
          <h2 className="section-title">System Status</h2>
          {healthLoading ? (
            <div className="w-4 h-4 border-2 border-primary-500/30 border-t-primary-500 rounded-full animate-spin ml-auto" />
          ) : (
            <span className={`badge ml-auto ${health?.status === 'ok' ? 'badge-success' : 'badge-danger'}`}>
              API {health?.status === 'ok' ? 'Online' : 'Offline'}
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { key: 'gemini', label: 'Gemini AI', hint: 'GEMINI_API_KEY' },
            { key: 'tavily', label: 'Tavily Search', hint: 'TAVILY_API_KEY' },
            { key: 'database', label: 'PostgreSQL', hint: 'DATABASE_URL' },
            { key: 'qdrant', label: 'Qdrant', hint: 'QDRANT_URL' },
          ].map(({ key, label, hint }) => (
            <div key={key} className="p-3 bg-surface-300 rounded-xl border border-white/5">
              <p className="text-xs text-slate-500 mb-1">{label}</p>
              <div className="flex items-center gap-1.5">
                <div className={`w-2 h-2 rounded-full ${isConfigured(key) ? 'bg-emerald-500' : 'bg-red-500'}`} />
                <span className="text-xs font-medium text-slate-300">
                  {isConfigured(key) ? 'Ready' : 'Not configured'}
                </span>
              </div>
              {!isConfigured(key) && (
                <p className="text-xs text-slate-600 mt-1 font-mono">{hint}</p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="glass-card p-5">
            <Icon size={20} className={`${color} mb-3`} />
            <p className="text-3xl font-bold text-slate-100">{value}</p>
            <p className="text-sm text-slate-400 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="section-title mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link to="/research/new" className="glass-card p-5 hover:bg-primary-600/10 hover:border-primary-500/30 transition-all duration-200 border border-white/10 group">
            <Brain size={24} className="text-primary-400 mb-3" />
            <h3 className="font-semibold text-slate-100 mb-1">Start New Research</h3>
            <p className="text-sm text-slate-400">Describe a topic and get a structured AI research plan.</p>
            <div className="flex items-center gap-1 text-primary-400 text-sm mt-3 group-hover:gap-2 transition-all">
              Start <ArrowRight size={14} />
            </div>
          </Link>

          <Link to="/documents" className="glass-card p-5 hover:bg-amber-600/10 hover:border-amber-500/30 transition-all duration-200 border border-white/10 group">
            <Zap size={24} className="text-amber-400 mb-3" />
            <h3 className="font-semibold text-slate-100 mb-1">Upload Documents</h3>
            <p className="text-sm text-slate-400">Add PDFs and research papers to your document library.</p>
            <div className="flex items-center gap-1 text-amber-400 text-sm mt-3 group-hover:gap-2 transition-all">
              Upload <ArrowRight size={14} />
            </div>
          </Link>

          <Link to="/history" className="glass-card p-5 hover:bg-emerald-600/10 hover:border-emerald-500/30 transition-all duration-200 border border-white/10 group">
            <CheckCircle size={24} className="text-emerald-400 mb-3" />
            <h3 className="font-semibold text-slate-100 mb-1">View History</h3>
            <p className="text-sm text-slate-400">Review past research projects and generated reports.</p>
            <div className="flex items-center gap-1 text-emerald-400 text-sm mt-3 group-hover:gap-2 transition-all">
              View <ArrowRight size={14} />
            </div>
          </Link>
        </div>
      </div>

      {/* Phase progress */}
      <div className="glass-card p-6">
        <h2 className="section-title mb-4">Development Progress</h2>
        <div className="space-y-3">
          {[
            { phase: 'Phase 1', name: 'Project Foundation', done: true },
            { phase: 'Phase 2', name: 'Planner MVP (Gemini + API)', done: true },
            { phase: 'Phase 3', name: 'Researcher, Analyst, Fact Checker, Report Writer', done: false },
            { phase: 'Phase 4', name: 'LangGraph Multi-Agent Orchestration', done: false },
            { phase: 'Phase 5', name: 'RAG Document Research (Qdrant)', done: false },
            { phase: 'Phase 6', name: 'PostgreSQL, Auth, Streaming', done: false },
            { phase: 'Phase 7', name: 'Full Frontend', done: false },
            { phase: 'Phase 8', name: 'Evaluation, Observability, Docker', done: false },
          ].map(({ phase, name, done }) => (
            <div key={phase} className="flex items-center gap-3">
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0
                ${done ? 'bg-emerald-500' : 'bg-surface-300 border border-white/10'}`}>
                {done && <CheckCircle size={12} className="text-white" />}
              </div>
              <span className={`text-xs font-medium ${done ? 'text-primary-300' : 'text-slate-600'} w-14 flex-shrink-0`}>
                {phase}
              </span>
              <span className={`text-sm ${done ? 'text-slate-300' : 'text-slate-600'}`}>{name}</span>
              {done && <span className="badge badge-success ml-auto">Complete</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
