import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import Login from './components/Login';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import DataDashboard from './components/DataDashboard';
import AISupervisor from './components/AISupervisor';
import MoreFunctions from './components/MoreFunctions';
import AgentDetail from './components/AgentDetail';
import AllOrders from './components/AllOrders';
import RefundOrders from './components/RefundOrders';
import AdDashboard from './components/AdDashboard';
import AdManagement from './components/AdManagement';
import MessageCenter from './components/MessageCenter';
import SystemManagement from './components/SystemManagement';
import { TabType, Agent } from './types';

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');
  const [isDark, setIsDark] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [username, setUsername] = useState('运营主管-张三');

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  const handleLogin = () => {
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setActiveTab('dashboard');
  };

  const toggleTheme = () => {
    setIsDark(!isDark);
  };

  const handleSelectAgent = (agent: Agent) => {
    setSelectedAgent(agent);
    setActiveTab('agent-detail');
  };

  if (!isLoggedIn) {
    return <Login onLogin={handleLogin} />;
  }

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DataDashboard />;
      case 'message-center':
        return <MessageCenter />;
      case 'ai-supervisor':
        return <AISupervisor />;
      case 'more-functions':
        return <MoreFunctions onSelectAgent={handleSelectAgent} />;
      case 'agent-detail':
        return selectedAgent ? (
          <AgentDetail agent={selectedAgent} onBack={() => setActiveTab('more-functions')} />
        ) : (
          <MoreFunctions onSelectAgent={handleSelectAgent} />
        );
      case 'ad-dashboard':
        return <AdDashboard />;
      case 'ad-management':
        return <AdManagement />;
      case 'all-orders':
        return <AllOrders />;
      case 'refund-orders':
        return <RefundOrders />;
      case 'system-management':
        return <SystemManagement />;
      default:
        return <DataDashboard />;
    }
  };

  return (
    <div className="flex min-h-screen bg-[var(--bg-main)] text-[var(--text-main)] transition-colors duration-300">
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
      />
      
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar 
          isDark={isDark} 
          toggleTheme={toggleTheme} 
          setActiveTab={setActiveTab}
          onLogout={handleLogout}
          username={username}
        />
        
        <main className="flex-1 overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab === 'agent-detail' && selectedAgent ? `agent-${selectedAgent.id}` : activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              {renderContent()}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
