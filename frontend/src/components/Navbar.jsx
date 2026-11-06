/**
 * ResearchMind AI – Top Navigation Bar
 * ======================================
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, Bell, User, ChevronRight } from 'lucide-react';

// Build breadcrumb from current path
function useBreadcrumbs() {
  const { pathname } = useLocation();
  const parts = pathname.split('/').filter(Boolean);
  return parts.map((part, i) => ({
    label: part.charAt(0).toUpperCase() + part.slice(1).replace(/-/g, ' '),
    to: '/' + parts.slice(0, i + 1).join('/'),
  }));
}

export default function Navbar({ onMenuToggle }) {
  const breadcrumbs = useBreadcrumbs();

  return (
    <header className="flex items-center gap-4 px-6 py-4 border-b border-white/10 bg-surface-100 min-h-[64px]">
      {/* Menu toggle (mobile) */}
      <button
        onClick={onMenuToggle}
        className="btn-ghost p-2 lg:hidden"
        aria-label="Toggle menu"
      >
        <Menu size={20} />
      </button>

      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1 text-sm flex-1">
        <Link to="/dashboard" className="text-slate-500 hover:text-slate-300 transition-colors">
          Home
        </Link>
        {breadcrumbs.map((crumb, i) => (
          <React.Fragment key={crumb.to}>
            <ChevronRight size={14} className="text-slate-600" />
            {i === breadcrumbs.length - 1 ? (
              <span className="text-slate-200 font-medium">{crumb.label}</span>
            ) : (
              <Link to={crumb.to} className="text-slate-500 hover:text-slate-300 transition-colors">
                {crumb.label}
              </Link>
            )}
          </React.Fragment>
        ))}
      </nav>

      {/* Right actions */}
      <div className="flex items-center gap-2">
        <button className="btn-ghost p-2 relative" aria-label="Notifications">
          <Bell size={18} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary-500 rounded-full" />
        </button>
        <button className="btn-ghost p-2" aria-label="User profile">
          <div className="w-7 h-7 rounded-full bg-primary-600/30 border border-primary-500/50 flex items-center justify-center">
            <User size={14} className="text-primary-300" />
          </div>
        </button>
      </div>
    </header>
  );
}
