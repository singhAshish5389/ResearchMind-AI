/**
 * ResearchMind AI – App Router
 * =============================
 * Defines all client-side routes and the top-level layout.
 *
 * Route structure:
 *   /                  → Landing page
 *   /login             → Login
 *   /register          → Registration
 *   /dashboard         → Main dashboard (protected)
 *   /research/new      → New research form
 *   /research/:id/plan → Research plan approval
 *   /research/:id      → Live research workspace
 *   /reports/:id       → Report viewer
 *   /history           → Research history
 *   /documents         → Document library
 *   /analytics         → Analytics dashboard
 *   /settings          → User settings
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// Pages
import LandingPage from './pages/LandingPage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import NewResearchPage from './pages/NewResearchPage.jsx';
import ResearchPlanPage from './pages/ResearchPlanPage.jsx';
import ResearchWorkspacePage from './pages/ResearchWorkspacePage.jsx';
import ReportViewerPage from './pages/ReportViewerPage.jsx';
import HistoryPage from './pages/HistoryPage.jsx';
import DocumentLibraryPage from './pages/DocumentLibraryPage.jsx';
import AnalyticsPage from './pages/AnalyticsPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import NotFoundPage from './pages/NotFoundPage.jsx';

// Layout
import AppLayout from './components/layout/AppLayout.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* App routes (with sidebar layout) */}
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/research/new" element={<NewResearchPage />} />
          <Route path="/research/:id/plan" element={<ResearchPlanPage />} />
          <Route path="/research/:id" element={<ResearchWorkspacePage />} />
          <Route path="/reports/:id" element={<ReportViewerPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/documents" element={<DocumentLibraryPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
