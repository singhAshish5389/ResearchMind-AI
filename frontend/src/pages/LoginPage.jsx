import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Brain, Mail, Lock, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error] = useState(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    // Phase 6: JWT authentication will be implemented here
    navigate("/dashboard");
  };

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-3 justify-center mb-8">
          <div className="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center shadow-glow">
            <Brain size={22} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold gradient-text">ResearchMind AI</h1>
        </div>
        <div className="glass-card p-8">
          <h2 className="text-xl font-bold text-slate-100 mb-1">Welcome back</h2>
          <p className="text-sm text-slate-400 mb-6">Sign in to your account</p>
          {error && (
            <div className="flex items-center gap-2 p-3 bg-danger/10 border border-danger/30 rounded-lg mb-4 text-sm text-red-300">
              <AlertCircle size={14} /> {error}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Email</label>
              <div className="relative">
                <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  id="login-email"
                  type="email"
                  className="input-field pl-9"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={e => setForm({...form, email: e.target.value})}
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Password</label>
              <div className="relative">
                <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  id="login-password"
                  type="password"
                  className="input-field pl-9"
                  placeholder="Password"
                  value={form.password}
                  onChange={e => setForm({...form, password: e.target.value})}
                />
              </div>
            </div>
            <button id="login-btn" type="submit" className="btn-primary w-full justify-center">
              Sign In
            </button>
          </form>
          <p className="text-center text-sm text-slate-500 mt-4">
            No account? <Link to="/register" className="text-primary-400 hover:text-primary-300">Register</Link>
          </p>
          <p className="text-center text-xs text-slate-600 mt-2">
            Authentication coming in Phase 6
          </p>
        </div>
      </div>
    </div>
  );
}
