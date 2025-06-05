'use client';

import { useState } from 'react';
import { DashboardHeader } from '@/components/DashboardHeader';
import { KeywordForm } from '@/components/KeywordForm';
import { ControlPanel } from '@/components/ControlPanel';
import { ProgressMonitor } from '@/components/ProgressMonitor';
import { ResultsTable } from '@/components/ResultsTable';
import { DashboardStats } from '@/components/DashboardStats';

export default function Home() {
  const [activeKeyword, setActiveKeyword] = useState<string>('');
  const [isRunning, setIsRunning] = useState(false);

  return (
    <main className="min-h-screen bg-background">
      <DashboardHeader />
      
      <div className="container mx-auto py-8 px-4">
        <DashboardStats />
        
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mt-6">
          <div className="lg:col-span-4">
            <div className="card mb-6">
              <h2 className="text-xl font-semibold mb-4 text-primary">Run New Query</h2>
              <KeywordForm 
                onSubmit={(keyword) => {
                  setActiveKeyword(keyword);
                  setIsRunning(true);
                }} 
              />
            </div>
            
            <div className="card">
              <h2 className="text-xl font-semibold mb-4 text-primary">Control Panel</h2>
              <ControlPanel isDisabled={isRunning} />
            </div>
          </div>
          
          <div className="lg:col-span-8">
            <div className="card mb-6">
              <h2 className="text-xl font-semibold mb-4 text-primary">Progress</h2>
              <ProgressMonitor 
                keyword={activeKeyword}
                isRunning={isRunning}
                onComplete={() => setIsRunning(false)}
              />
            </div>
            
            <div className="card">
              <h2 className="text-xl font-semibold mb-4 text-primary">Results</h2>
              <ResultsTable keyword={activeKeyword} />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
