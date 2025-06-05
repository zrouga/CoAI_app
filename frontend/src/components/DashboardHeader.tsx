import { Search, Settings, Database } from 'lucide-react';
import { useState } from 'react';
import { SettingsDrawer } from './SettingsDrawer';
import { DatabaseDrawer } from './DatabaseDrawer';

export function DashboardHeader() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [databaseOpen, setDatabaseOpen] = useState(false);

  return (
    <header className="bg-primary text-white shadow-md">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Search size={24} />
          <h1 className="text-xl font-bold">Market Intelligence Dashboard</h1>
        </div>

        <div className="flex items-center space-x-4">
          <button 
            onClick={() => setDatabaseOpen(true)}
            className="p-2 hover:bg-primary-600 rounded-full transition-colors flex items-center"
            aria-label="Database Management"
          >
            <Database size={20} />
          </button>
          
          <button 
            onClick={() => setSettingsOpen(true)}
            className="p-2 hover:bg-primary-600 rounded-full transition-colors flex items-center"
            aria-label="Settings"
          >
            <Settings size={20} />
          </button>
        </div>

        <SettingsDrawer isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
        <DatabaseDrawer isOpen={databaseOpen} onClose={() => setDatabaseOpen(false)} />
      </div>
    </header>
  );
}
