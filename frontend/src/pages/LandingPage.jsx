/**
 * ResearchMind AI – Landing Page
 * ================================
 * The public home page showcasing the platform's capabilities.
 */

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Brain, Search, FileText, Shield, Zap, ArrowRight,
  CheckCircle, ChevronDown, Globe, Database, BarChart2,
} from 'lucide-react';
import api from '../services/api.js';

const features = [
  {
    icon: Brain,
    title: 'Multi-Agent Orchestration',
    description: 'Five specialized AI agents work in concert: Planner, Researcher, Analyst, Fact Checker, and Report Writer.',
    color: 'text-violet-400',
    bg: 'bg-violet-500/10 border-violet-500/20',
  },
  {
    icon: Search,
    title: 'Real Internet Research',
    description: 'The Researcher Agent uses Tavily to search the internet. No hallucinated sources — only real URLs.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10 border-blue-500/20',
  },
  {
    icon: Shield,
    title: 'Fact Verification',
    description: 'The Fact Checker assesses whether claims are supported by collected evidence before they reach your report.',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10 border-emerald-500/20',
  },
  {
    icon: Database,
    title: 'RAG Document Research',
    description: 'Upload PDFs, research papers, or reports and let the AI research your own document collection.',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10 border-amber-500/20',
  },
  {
    icon: FileText,
    title: 'Professional Reports',
    description: 'Receive a comprehensive, downloadable PDF report with citations, findings, and verified claims.',
    color: 'text-pink-400',
    bg: 'bg-pink-500/10 border-pink-500/20',
  },
  {
    icon: BarChart2,
    title: 'Research Analytics',
    description: 'Track research history, source quality, agent performance, and estimated API usage.',
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10 border-cyan-500/20',
  },
];

const agentSteps = [
  { name: 'Planner Agent', desc: 'Analyses your topic and generates structured research questions', icon: Brain },
  { name: 'Researcher Agent', desc: 'Searches the internet and collects real sources via Tavily', icon: Globe },
  { name: 'Analyst Agent', desc: 'Identifies themes, trends, opportunities, and contradictions', icon: Zap },
  { name: 'Fact Checker Agent', desc: 'Verifies claims against collected evidence', icon: Shield },
  { name: 'Report Writer Agent', desc: 'Generates a professional, cited research report', icon: FileText },
];

export default function LandingPage() {
  const [backendStatus, setBackendStatus] = useState(null);

  useEffect(() => {
    api.health()
      .then((res) => setBackendStatus(res.data))
      .catch(() => setBackendStatus({ status: 'offline' }));
  }, []);

  return (
    <div className="min-h-screen bg-surface text-slate-100 overflow-x-hidden">

      {/* ── Navigation ─────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-4
                      bg-surface/80 backdrop-blur-lg border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center shadow-glow-sm">
            <Brain size={18} className="text-white" />
          </div>
          <span className="font-bold text-slate-100">ResearchMind AI</span>
          {backendStatus && (
            <span className={`badge ${backendStatus.status === 'ok' ? 'badge-success' : 'badge-danger'} ml-2`}>
              API {backendStatus.status === 'ok' ? 'Online' : 'Offline'}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="btn-ghost text-sm">Sign in</Link>
          <Link to="/register" className="btn-primary text-sm">Get Started</Link>
        </div>
      </nav>

      {/* ── Hero Section ───────────────────────────────────────────────────── */}
      <section className="relative flex flex-col items-center justify-center min-h-screen text-center px-6 pt-16">
        {/* Background glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px]
                          bg-primary-600/10 rounded-full blur-[120px]" />
          <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px]
                          bg-violet-600/5 rounded-full blur-[80px]" />
        </div>

        <div className="relative z-10 max-w-4xl mx-auto animate-slideUp">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full
                          bg-primary-500/10 border border-primary-500/20 text-primary-300 text-sm mb-8">
            <Zap size={14} />
            <span>Powered by Gemini · LangGraph · Tavily · Qdrant</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold leading-tight mb-6">
            <span className="gradient-text">AI-Powered</span>
            <br />
            Research Intelligence
          </h1>

          <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            ResearchMind AI deploys a team of specialized agents to conduct deep research,
            verify facts, and deliver comprehensive reports — autonomously.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/dashboard" className="btn-primary text-base px-8 py-3 shadow-glow">
              Start Researching <ArrowRight size={18} />
            </Link>
            <Link to="/register" className="btn-secondary text-base px-8 py-3">
              Create Free Account
            </Link>
          </div>

          {/* Quick example */}
          <div className="mt-12 p-4 glass-card max-w-2xl mx-auto text-left">
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Example query</p>
            <p className="text-slate-300 text-sm italic">
              "Analyze the future of Generative AI engineering jobs in India over the next five years.
              Identify important skills, industry adoption, salary trends, risks, and future challenges."
            </p>
          </div>
        </div>

        {/* Scroll hint */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-slate-600">
          <span className="text-xs">Scroll to explore</span>
          <ChevronDown size={18} className="animate-bounce" />
        </div>
      </section>

      {/* ── Agent Workflow ─────────────────────────────────────────────────── */}
      <section className="py-24 px-6 bg-surface-50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Five Specialized Agents</h2>
            <p className="text-slate-400 text-lg">Coordinated by LangGraph for autonomous research</p>
          </div>

          <div className="relative">
            {/* Connecting line */}
            <div className="absolute left-8 top-12 bottom-12 w-px bg-gradient-to-b from-primary-500/50 via-primary-400/20 to-transparent hidden md:block" />

            <div className="space-y-4">
              {agentSteps.map((step, i) => {
                const Icon = step.icon;
                return (
                  <div key={step.name} className="flex items-start gap-6 pl-4 md:pl-0">
                    <div className="relative flex-shrink-0">
                      <div className="w-12 h-12 bg-primary-600/20 border border-primary-500/30
                                      rounded-xl flex items-center justify-center shadow-glow-sm">
                        <Icon size={20} className="text-primary-300" />
                      </div>
                      <span className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-primary-600
                                       rounded-full flex items-center justify-center text-xs font-bold">
                        {i + 1}
                      </span>
                    </div>
                    <div className="flex-1 glass-card p-4">
                      <h3 className="font-semibold text-slate-100 mb-1">{step.name}</h3>
                      <p className="text-sm text-slate-400">{step.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ── Features Grid ──────────────────────────────────────────────────── */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Built for Serious Research</h2>
            <p className="text-slate-400 text-lg">Every feature designed for accuracy, not convenience</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <div key={feature.title}
                     className={`glass-card p-6 border ${feature.bg}
                                 hover:scale-[1.02] transition-transform duration-200`}>
                  <div className={`w-10 h-10 rounded-lg ${feature.bg} border
                                   flex items-center justify-center mb-4`}>
                    <Icon size={20} className={feature.color} />
                  </div>
                  <h3 className="font-semibold text-slate-100 mb-2">{feature.title}</h3>
                  <p className="text-sm text-slate-400 leading-relaxed">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────────────────────── */}
      <section className="py-24 px-6 bg-surface-50">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-4xl font-bold mb-4">Ready to research smarter?</h2>
          <p className="text-slate-400 text-lg mb-8">
            Start with a free account. Configure your API keys and run research immediately.
          </p>
          <Link to="/register" className="btn-primary text-base px-10 py-4 shadow-glow">
            Get Started Free <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/10 py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-slate-400 text-sm">
            <Brain size={16} className="text-primary-400" />
            <span>ResearchMind AI © 2024</span>
          </div>
          <div className="flex items-center gap-2 text-slate-600 text-xs">
            <CheckCircle size={12} className="text-emerald-500" />
            <span>Built with Gemini · LangGraph · FastAPI · React</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
