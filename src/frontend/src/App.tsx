import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import Placeholder from './pages/Placeholder'
import Approvals from './pages/Approvals'
import AgentCatalog from './pages/AgentCatalog'
import AgentChat from './pages/AgentChat'
import KBReview from './pages/KBReview'
import AdDashboard from './pages/AdDashboard'
import AdManagement from './pages/AdManagement'
import MessageCenter from './pages/MessageCenter'
import SystemManagement from './pages/SystemManagement'
import CostMonitor from './pages/CostMonitor'

function App() {
  return (
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
            <Route path="agents" element={<AgentCatalog />} />
            <Route path="agents/:type" element={<AgentChat />} />
            <Route path="ads" element={<AdDashboard />} />
            <Route path="ads/manage" element={<AdManagement />} />
            <Route path="orders" element={<Placeholder />} />
            <Route path="refunds" element={<Placeholder />} />
            <Route path="messages" element={<MessageCenter />} />
            <Route path="approvals" element={<Approvals />} />
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
            <Route path="system/costs" element={
              <ProtectedRoute requiredRole="boss">
                <CostMonitor />
              </ProtectedRoute>
            } />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
