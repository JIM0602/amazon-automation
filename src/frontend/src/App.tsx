import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import Login from './pages/Login'
import SchedulesPage from './pages/system/SchedulesPage'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const ApprovalsPage = lazy(() => import('./pages/ApprovalsPage'))
const AgentCatalog = lazy(() => import('./pages/AgentCatalog'))
const AgentChat = lazy(() => import('./pages/AgentChat'))
const KBReview = lazy(() => import('./pages/KBReview'))
const AdDashboard = lazy(() => import('./pages/AdDashboard'))
const AdManagement = lazy(() => import('./pages/AdManagement'))
const SystemManagement = lazy(() => import('./pages/SystemManagement'))
const CostMonitor = lazy(() => import('./pages/CostMonitor'))
const ApiKeysPage = lazy(() => import('./pages/ApiKeysPage'))
const OrdersPage = lazy(() => import('./pages/OrdersPage'))
const ReturnsPage = lazy(() => import('./pages/ReturnsPage'))
const AdAgentPage = lazy(() => import('./pages/AdAgentPage'))
const CampaignDetail = lazy(() => import('./pages/ad-management/CampaignDetail'))
const AdGroupDetail = lazy(() => import('./pages/ad-management/AdGroupDetail'))
const UserManagementPage = lazy(() => import('./pages/system/UserManagementPage'))
const AgentConfigPage = lazy(() => import('./pages/system/AgentConfigPage'))

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Suspense fallback={<div className="p-6 text-sm text-gray-500">页面加载中...</div>}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <Layout />
                  </ProtectedRoute>
                }
              >
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
                <Route
                  path="kb-review"
                  element={
                    <ProtectedRoute requiredRole="boss">
                      <KBReview />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="system"
                  element={
                    <ProtectedRoute requiredRole="boss">
                      <SystemManagement />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="system/users"
                  element={
                    <ProtectedRoute requiredRole="boss">
                      <UserManagementPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="system/agents"
                  element={
                    <ProtectedRoute requiredRole="boss">
                      <AgentConfigPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="system/api-keys"
                  element={
                    <ProtectedRoute requiredRole="boss">
                      <ApiKeysPage />
                    </ProtectedRoute>
                  }
                />
                <Route path="system/schedules" element={
                  <ProtectedRoute requiredRole="boss">
                    <SchedulesPage />
                  </ProtectedRoute>
                } />
                <Route
                  path="system/costs"
                  element={
                    <ProtectedRoute requiredRole="boss">
                      <CostMonitor />
                    </ProtectedRoute>
                  }
                />
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
