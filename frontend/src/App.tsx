import { useState } from 'react';
import './App.css';
import { ThemeProvider } from './context/ThemeContext';
import { AutomataMaker } from './components/maker/AutomataMaker';
import { AuditorDashboard } from './components/auditor/AuditorDashboard';

type Tab = 'maker' | 'auditor';

function AppContent() {
  const [activeTab, setActiveTab] = useState<Tab>('maker');

  return (
    <div className="app-shell">
      {/* Top nav bar */}
      <nav className="app-nav">
        <div className="app-nav-left">
          <span className="app-logo">AutoVerify</span>
          <div className="nav-links">
            <button
              className={`nav-link ${activeTab === 'maker' ? 'active' : ''}`}
              onClick={() => setActiveTab('maker')}
            >
              Maker
            </button>
            <button
              className={`nav-link ${activeTab === 'auditor' ? 'active' : ''}`}
              onClick={() => setActiveTab('auditor')}
            >
              Auditor
            </button>
          </div>
        </div>
      </nav>

      {/* Content fills remaining viewport */}
      <main className="app-main">
        {activeTab === 'maker' && <AutomataMaker />}
        {activeTab === 'auditor' && <AuditorDashboard />}
      </main>
    </div>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
