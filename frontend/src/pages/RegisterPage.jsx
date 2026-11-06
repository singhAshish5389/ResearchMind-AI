import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Brain, Mail, Lock, User } from "lucide-react";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });

  const handleSubmit = (e) => {
    e.preventDefault();
    // Phase 6: User registration will be implemented here
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
          <h2 className="text-xl font-bold text-slate-100 mb-1">Create account</h2>
          <p className="text-sm text-slate-400 mb-6">Start researching with AI</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Full Name</label>
              <div className="relative">
                <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  id="reg-name"
                  type="text"
                  className="input-field pl-9"
                  placeholder="Your name"
                  value={form.name}
                  onChange={e => setForm({...form, name: e.target.value})}
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Email</label>
              <div className="relative">
                <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  id="reg-email"
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
                  id="reg-password"
                  type="password"
                  className="input-field pl-9"
                  placeholder="Minimum 8 characters"
                  value={form.password}
                  onChange={e => setForm({...form, password: e.target.value})}
                />
              </div>
            </div>
            <button id="register-btn" type="submit" className="btn-primary w-full justify-center">
              Create Account
            </button>
          </form>
          <p className="text-center text-sm text-slate-500 mt-4">
            Have an account? <Link to="/login" className="text-primary-400 hover:text-primary-300">Sign in</Link>
          </p>
          <p className="text-center text-xs text-slate-600 mt-2">
            Authentication coming in Phase 6
          </p>
        </div>
      </div>
    </div>
  );
}
