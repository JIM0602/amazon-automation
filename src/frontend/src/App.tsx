import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import PlaceholderPage from './pages/PlaceholderPage'
import ApprovalsPage from './pages/ApprovalsPage'
import AgentCatalog from './pages/AgentCatalog'
import AgentChat from './pages/AgentChat'
import KBReview from './pages/KBReview'
import AdDashboard from './pages/AdDashboard'
import AdManagement from './pages/AdManagement'
import SystemManagement from './pages/SystemManagement'
import CostMonitor from './pages/CostMonitor'
import ApiKeysPage from './pages/ApiKeysPage'
import OrdersPage from './pages/OrdersPage'
import ReturnsPage from './pages/ReturnsPage'
import AdAgentPage from './pages/AdAgentPage'
import CampaignDetail from './pages/ad-management/CampaignDetail'
import AdGroupDetail from './pages/ad-management/AdGroupDetail'
import UserManagementPage from './pages/system/UserManagementPage'
import AgentConfigPage from './pages/system/AgentConfigPage'

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }>
            <Route index element={<Dashboard />} />
            <Route path="dashboard" element={<Navigate to="/" replace />} />
            <Route path="agents" element={<AgentCatalog />} />
            <Route path="agents/:type" element={<AgentChat />} />
            <Route path="chat/:agentType" element={<AgentChat />} />
            <Route path="ads" element={<AdDashboard />} />
            <Route path="ads/dashboard" element={<AdDashboard />} />
            <Route path="ads/manage" element={<AdManagement />} />
            <Route path="ads/management" element={<AdManagement />} />
            <Route path="ads/management/campaign/:id" element={<CampaignDetail />} />
            <Route path="ads/management/ad-group/:id" element={<AdGroupDetail />} />
            <Route path="ads/agent" element={<AdAgentPage />} />
            <Route path="orders" element={<OrdersPage />} />
            <Route path="returns" element={<ReturnsPage />} />
            <Route path="refunds" element={<Navigate to="/returns" replace />} />
            <Route path="approvals" element={<ApprovalsPage />} />
            <Route path="kb-review" element={
              <ProtectedRoute requiredRole="boss">
                <KBReview />
              </ProtectedRoute>
            } />
            <Route path="system" element={
              <ProtectedRoute requiredRole="boss">
                <SystemManagement />
              </ProtectedRoute>
            } />
            <Route path="system/users" element={
              <ProtectedRoute requiredRole="boss">
                <UserManagementPage />
              </ProtectedRoute>
            } />
            <Route path="system/agents" element={
              <ProtectedRoute requiredRole="boss">
                <AgentConfigPage />
              </ProtectedRoute>
            } />
            <Route path="system/api-keys" element={
              <ProtectedRoute requiredRole="boss">
                <ApiKeysPage />
              </ProtectedRoute>
            } />
            <Route path="system/schedules" element={
              <ProtectedRoute requiredRole="boss">
                <PlaceholderPage title="计划任务" />
              </ProtectedRoute>
            } />
            <Route path="system/costs" element={
              <ProtectedRoute requiredRole="boss">
                <CostMonitor />
              </ProtectedRoute>
            } />
          </Route>
        </Routes>
      </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
