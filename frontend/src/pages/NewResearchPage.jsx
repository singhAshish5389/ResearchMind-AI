/**
 * ResearchMind AI – New Research Page
 * =====================================
 * The main page for creating a new research job.
 * Contains the ResearchForm component which calls the Planner Agent.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Brain, Search, BookOpen, Globe, Zap, AlertCircle, ChevronRight } from 'lucide-react';
import api from '../services/api.js';

const DEPTHS = [
  { value: 'quick', label: 'Quick', desc: '3–5 questions · ~3 min', icon: Zap },
  { value: 'standard', label: 'Standard', desc: '5–7 questions · ~8 min', icon: Search },
  { value: 'comprehensive', label: 'Comprehensive', desc: '8–10 questions · ~15 min', icon: Brain },
];

const MODES = [
  { value: 'web', label: 'Web Research', desc: 'Search the internet', icon: Globe },
  { value: 'documents', label: 'Document Research', desc: 'Search uploaded documents', icon: BookOpen },
  { value: 'hybrid', label: 'Hybrid', desc: 'Both web and documents', icon: Search },
];

const EXAMPLE_TOPICS = [
  'Analyze the future of Generative AI engineering jobs in India over the next five years.',
  'What are the most effective strategies for carbon capture and storage technology in 2024?',
  'Compare the adoption of large language models across different industries globally.',
  'What are the key trends in quantum computing and its applications in cryptography?',
];

export default function NewResearchPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    topic: '',
    depth: 'standard',
    mode: 'web',
    language: 'English',
    max_questions: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const payload = {
        topic: formData.topic.trim(),
        depth: formData.depth,
        mode: formData.mode,
        language: formData.language,
        ...(formData.max_questions && { max_questions: parseInt(formData.max_questions) }),
      };

      const response = await api.createResearchPlan(payload);
      const { research_id, plan } = response.data;

      // Navigate to the plan approval page
      navigate(`/research/${research_id}/plan`, { state: { plan, research_id } });
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.message) {
        setError(detail.message);
      } else if (typeof detail === 'string') {
        setError(detail);
      } else if (err.response?.status === 503) {
        setError('Gemini API is not configured. Please add GEMINI_API_KEY to your .env file.');
      } else if (err.response?.status === 422) {
        setError('Please check your input. The topic must be at least 10 characters long.');
      } else {
        setError('Failed to generate research plan. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto animate-slideUp">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-100 mb-2">New Research</h1>
        <p className="text-slate-400">
          Describe your research topic and the AI will generate a structured plan for your review.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">

        {/* Topic Input */}
        <div className="glass-card p-6">
          <label className="block text-sm font-semibold text-slate-200 mb-3">
            Research Topic <span className="text-danger">*</span>
          </label>
          <textarea
            id="research-topic"
            className="input-field resize-none"
            rows={4}
            placeholder="Describe your research topic in detail. The more specific you are, the better the research plan..."
            value={formData.topic}
            onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
            required
            minLength={10}
            maxLength={2000}
          />
          <div className="flex items-center justify-between mt-2">
            <p className="text-xs text-slate-500">Minimum 10 characters</p>
            <p className="text-xs text-slate-500">{formData.topic.length}/2000</p>
          </div>

          {/* Example topics */}
          <div className="mt-3">
            <p className="text-xs text-slate-500 mb-2">Example topics:</p>
            <div className="space-y-1">
              {EXAMPLE_TOPICS.map((topic, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setFormData({ ...formData, topic })}
                  className="text-xs text-primary-400 hover:text-primary-300 text-left
                             transition-colors block w-full truncate"
                >
                  → {topic}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Research Depth */}
        <div className="glass-card p-6">
          <label className="block text-sm font-semibold text-slate-200 mb-4">Research Depth</label>
          <div className="grid grid-cols-3 gap-3">
            {DEPTHS.map(({ value, label, desc, icon: Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => setFormData({ ...formData, depth: value })}
                className={`flex flex-col items-center gap-2 p-4 rounded-xl border transition-all duration-200
                  ${formData.depth === value
                    ? 'bg-primary-600/20 border-primary-500/50 text-primary-300'
                    : 'bg-white/5 border-white/10 text-slate-400 hover:border-white/20 hover:text-slate-300'
                  }`}
              >
                <Icon size={20} />
                <span className="text-sm font-semibold">{label}</span>
                <span className="text-xs text-center opacity-70">{desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Research Mode */}
        <div className="glass-card p-6">
          <label className="block text-sm font-semibold text-slate-200 mb-4">Research Mode</label>
          <div className="grid grid-cols-3 gap-3">
            {MODES.map(({ value, label, desc, icon: Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => setFormData({ ...formData, mode: value })}
                className={`flex flex-col items-center gap-2 p-4 rounded-xl border transition-all duration-200
                  ${formData.mode === value
                    ? 'bg-primary-600/20 border-primary-500/50 text-primary-300'
                    : 'bg-white/5 border-white/10 text-slate-400 hover:border-white/20 hover:text-slate-300'
                  }`}
              >
                <Icon size={20} />
                <span className="text-sm font-semibold">{label}</span>
                <span className="text-xs text-center opacity-70">{desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Advanced Options */}
        <details className="glass-card p-6 group">
          <summary className="flex items-center justify-between cursor-pointer
                              text-sm font-semibold text-slate-200 list-none">
            Advanced Options
            <ChevronRight size={16} className="text-slate-500 group-open:rotate-90 transition-transform" />
          </summary>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Max Questions (3–10)</label>
              <input
                type="number"
                className="input-field"
                placeholder="Auto"
                min="3"
                max="10"
                value={formData.max_questions}
                onChange={(e) => setFormData({ ...formData, max_questions: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Report Language</label>
              <input
                type="text"
                className="input-field"
                placeholder="English"
                value={formData.language}
                onChange={(e) => setFormData({ ...formData, language: e.target.value })}
              />
            </div>
          </div>
        </details>

        {/* Error message */}
        {error && (
          <div className="flex items-start gap-3 p-4 bg-danger/10 border border-danger/30 rounded-xl animate-fadeIn">
            <AlertCircle size={18} className="text-danger flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-300">{error}</p>
              {error.includes('GEMINI_API_KEY') && (
                <p className="text-xs text-slate-400 mt-1">
                  Add your key to <code className="font-mono text-primary-400">.env</code> and restart the backend.
                  Get it at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer"
                                className="text-primary-400 underline">aistudio.google.com</a>
                </p>
              )}
            </div>
          </div>
        )}

        {/* Submit */}
        <div className="flex items-center justify-between pt-2">
          <p className="text-xs text-slate-500">
            The Planner Agent will generate a research plan for your review before research begins.
          </p>
          <button
            id="generate-plan-btn"
            type="submit"
            disabled={isLoading || formData.topic.trim().length < 10}
            className="btn-primary"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Generating Plan...
              </>
            ) : (
              <>
                <Brain size={18} />
                Generate Plan
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
