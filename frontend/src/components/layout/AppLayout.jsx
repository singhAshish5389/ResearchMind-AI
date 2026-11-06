/**
 * ResearchMind AI – App Layout
 * =============================
 * Wraps all authenticated pages with the sidebar + top navbar.
 */

import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import DashboardSidebar from '../DashboardSidebar.jsx';
import Navbar from '../Navbar.jsx';

export default function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-surface overflow-hidden">
      {/* Sidebar */}
      <DashboardSidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((prev) => !prev)}
      />

      {/* Main content area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <Navbar onMenuToggle={() => setSidebarCollapsed((prev) => !prev)} />
        <main className="flex-1 overflow-y-auto p-6 animate-fadeIn">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
