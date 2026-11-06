/**
 * ResearchMind AI – Dashboard Sidebar
 * =====================================
 * The main navigation sidebar for authenticated users.
 */

import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  Brain,
  LayoutDashboard,
  PlusCircle,
  History,
  FileText,
  BookOpen,
  BarChart2,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Zap,
} from 'lucide-react';

const navItems = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/research/new', icon: PlusCircle,      label: 'New Research' },
  { to: '/history',     icon: History,          label: 'History' },
  { to: '/documents',   icon: BookOpen,         label: 'Documents' },
  { to: '/analytics',   icon: BarChart2,        label: 'Analytics' },
  { to: '/settings',    icon: Settings,         label: 'Settings' },
];

export default function DashboardSidebar({ collapsed, onToggle }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    navigate('/login');
  };

  return (
    <aside
      className={`
        flex flex-col bg-surface-100 border-r border-white/10
        transition-all duration-300 ease-in-out
        ${collapsed ? 'w-16' : 'w-64'}
      `}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 p-4 border-b border-white/10 min-h-[64px]">
        <div className="flex-shrink-0 w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center shadow-glow-sm">
          <Brain size={18} className="text-white" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <p className="font-bold text-slate-100 text-sm leading-none">ResearchMind</p>
            <p className="text-xs text-primary-400 mt-0.5">AI Platform</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group
              ${isActive
                ? 'bg-primary-600/20 text-primary-300 border border-primary-500/30'
                : 'text-slate-400 hover:text-slate-100 hover:bg-white/5'
              }`
            }
            title={collapsed ? label : ''}
          >
            <Icon size={18} className="flex-shrink-0" />
            {!collapsed && (
              <span className="text-sm font-medium truncate">{label}</span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-white/10 space-y-1">
        {/* Version badge */}
        {!collapsed && (
          <div className="flex items-center gap-2 px-3 py-2">
            <Zap size={14} className="text-primary-400" />
            <span className="text-xs text-slate-500">v0.1.0 – Phase 1+2</span>
          </div>
        )}

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl
                     text-slate-400 hover:text-red-400 hover:bg-red-500/10
                     transition-all duration-200"
          title={collapsed ? 'Logout' : ''}
        >
          <LogOut size={18} className="flex-shrink-0" />
          {!collapsed && <span className="text-sm font-medium">Logout</span>}
        </button>

        {/* Collapse toggle */}
        <button
          onClick={onToggle}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl
                     text-slate-500 hover:text-slate-100 hover:bg-white/5
                     transition-all duration-200"
        >
          {collapsed
            ? <ChevronRight size={18} className="flex-shrink-0" />
            : <><ChevronLeft size={18} className="flex-shrink-0" /><span className="text-sm">Collapse</span></>
          }
        </button>
      </div>
    </aside>
  );
}
