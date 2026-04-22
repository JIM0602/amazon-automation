from pathlib import Path


def test_app_uses_lazy_loaded_routes_for_heavy_pages() -> None:
    content = Path("src/frontend/src/App.tsx").read_text(encoding="utf-8")

    assert "import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'" not in content
    assert "import { lazy, Suspense } from 'react'" in content
    assert "const Dashboard = lazy(() => import('./pages/Dashboard'))" in content
    assert "const AgentChat = lazy(() => import('./pages/AgentChat'))" in content
    assert "const AdDashboard = lazy(() => import('./pages/AdDashboard'))" in content
    assert "const CostMonitor = lazy(() => import('./pages/CostMonitor'))" in content
    assert '<Suspense fallback={<div className="p-6 text-sm text-gray-500">页面加载中...</div>}>' in content
    assert "import SchedulesPage from './pages/system/SchedulesPage'" in content
