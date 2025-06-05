'use client';

import { useEffect, useState, useRef } from 'react';
import { CheckCircle, XCircle, Clock, AlertTriangle, Activity } from 'lucide-react';
import { getKeywordStatus } from '@/services/api';
import { SSEClient, PipelineProgress } from '@/services/sse';
import { KeywordStatus, PipelineStatus } from '@/types/api';
import toast from 'react-hot-toast';

interface ProgressStep {
  name: string;
  description: string;
  status: 'waiting' | 'in-progress' | 'complete' | 'error';
  count?: number;
  total?: number;
  percentage?: number;
  currentItem?: string;
}

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

interface ProgressMonitorProps {
  keyword: string;
  isRunning: boolean;
  onComplete: () => void;
}

export function ProgressMonitor({ keyword, isRunning, onComplete }: ProgressMonitorProps) {
  const [keywordStatus, setKeywordStatus] = useState<KeywordStatus | null>(null);
  const [steps, setSteps] = useState<ProgressStep[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const sseClientRef = useRef<SSEClient | null>(null);

  // Initialize steps
  useEffect(() => {
    setSteps([
      {
        name: 'Step 1',
        description: 'Facebook Ad Library Scraping',
        status: 'waiting',
      },
      {
        name: 'Step 2',
        description: 'Traffic Data Enrichment',
        status: 'waiting',
      }
    ]);
  }, [keyword]);

  // Fetch initial status
  useEffect(() => {
    if (!keyword) return;
    
    getKeywordStatus(keyword)
      .then(status => {
        setKeywordStatus(status);
        
        // Update steps based on initial status
        if (status.status === PipelineStatus.COMPLETED) {
          setSteps([
            {
              name: 'Step 1',
              description: 'Facebook Ad Library Scraping',
              status: 'complete',
              count: status.step1_products,
            },
            {
              name: 'Step 2',
              description: 'Traffic Data Enrichment',
              status: 'complete',
              count: status.step2_enriched,
              total: status.step1_products,
            }
          ]);
        }
      })
      .catch((error) => {
        console.error('Failed to get status:', error);
        if (error.message.includes('404')) {
          // Status not found - probably a new keyword
          setKeywordStatus({
            keyword,
            status: PipelineStatus.NOT_STARTED,
            step1_products: 0,
            step2_enriched: 0,
            errors: []
          });
        }
      });
  }, [keyword]);

  // Set up SSE connection when pipeline starts
  useEffect(() => {
    if (!keyword || !isRunning) return;
    
    // Clean up previous connection
    if (sseClientRef.current) {
      sseClientRef.current.disconnect();
    }
    
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    const sseClient = new SSEClient(keyword, apiUrl, {
      onConnect: () => {
        setIsConnected(true);
        toast.success('Connected to pipeline stream');
      },
      
      onDisconnect: () => {
        setIsConnected(false);
      },
      
      onPipelineStart: (data) => {
        setLogs(prev => [...prev, {
          timestamp: new Date().toISOString(),
          level: 'info',
          message: data.message
        }]);
      },
      
      onStepStart: (step, data) => {
        setSteps(prev => prev.map((s, idx) => 
          idx === step - 1 ? { ...s, status: 'in-progress', currentItem: data.details } : s
        ));
        
        setLogs(prev => [...prev, {
          timestamp: new Date().toISOString(),
          level: 'info',
          message: data.message
        }]);
      },
      
      onStepProgress: (step, progress: PipelineProgress) => {
        setSteps(prev => prev.map((s, idx) => 
          idx === step - 1 ? { 
            ...s, 
            status: 'in-progress',
            count: progress.progress,
            total: progress.total,
            percentage: progress.percentage,
            currentItem: progress.currentItem
          } : s
        ));
      },
      
      onStepComplete: (step, data) => {
        setSteps(prev => prev.map((s, idx) => {
          if (idx === step - 1) {
            return { 
              ...s, 
              status: 'complete',
              count: step === 1 ? data.results.products_found : data.results.domains_enriched,
              total: step === 2 ? data.results.domains_processed : undefined,
              percentage: 100,
              currentItem: undefined
            };
          }
          return s;
        }));
        
        setLogs(prev => [...prev, {
          timestamp: new Date().toISOString(),
          level: 'info',
          message: data.message
        }]);
      },
      
      onPipelineComplete: (data) => {
        setSteps(prev => prev.map(s => ({ ...s, status: 'complete' })));
        
        setKeywordStatus(prev => prev ? {
          ...prev,
          status: PipelineStatus.COMPLETED,
          step1_products: data.summary.products_discovered,
          step2_enriched: data.summary.traffic_enriched,
          completed_at: new Date().toISOString(),
          duration_seconds: data.total_duration_seconds
        } : null);
        
        toast.success(`Analysis completed for "${keyword}"!`);
        onComplete();
        
        setLogs(prev => [...prev, {
          timestamp: new Date().toISOString(),
          level: 'success',
          message: data.message
        }]);
      },
      
      onPipelineError: (errorData) => {
        setError(errorData.error);
        
        const failedStep = errorData.step || 1;
        setSteps(prev => prev.map((s, idx) => 
          idx === failedStep - 1 ? { ...s, status: 'error' } : s
        ));
        
        toast.error('Analysis failed. Check logs for details.');
        onComplete();
        
        setLogs(prev => [...prev, {
          timestamp: new Date().toISOString(),
          level: 'error',
          message: errorData.message
        }]);
      },
      
      onLog: (log) => {
        setLogs(prev => [...prev, {
          timestamp: log.timestamp,
          level: log.level,
          message: log.message
        }]);
      },
      
      onError: (error) => {
        console.error('SSE error:', error);
        toast.error('Connection error. Retrying...');
      }
    });
    
    sseClient.connect();
    sseClientRef.current = sseClient;
    
    return () => {
      sseClient.disconnect();
    };
  }, [keyword, isRunning, onComplete]);

  if (!keyword) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Clock size={48} className="mx-auto mb-3 opacity-50" />
        <p>Enter a keyword above to start analyzing market data.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-gray-50 rounded-md p-4">
        <div className="flex items-center justify-between">
          <h3 className="font-medium">
            Currently analyzing: <span className="font-bold text-primary">{keyword}</span>
          </h3>
          {isConnected && (
            <div className="flex items-center text-green-600 text-sm">
              <Activity size={16} className="mr-1 animate-pulse" />
              Live
            </div>
          )}
        </div>
        
        {keywordStatus && keywordStatus.status !== PipelineStatus.NOT_STARTED && (
          <div className="text-sm text-gray-600 flex flex-col md:flex-row gap-4 mt-2">
            <div>
              <span className="font-medium">Started:</span>{' '}
              {keywordStatus.started_at ? new Date(keywordStatus.started_at).toLocaleTimeString() : 'Not yet'}
            </div>
            
            {keywordStatus.completed_at && (
              <>
                <div>
                  <span className="font-medium">Completed:</span>{' '}
                  {new Date(keywordStatus.completed_at).toLocaleTimeString()}
                </div>
                <div>
                  <span className="font-medium">Duration:</span>{' '}
                  {keywordStatus.duration_seconds 
                    ? `${Math.floor(keywordStatus.duration_seconds / 60)}m ${Math.round(keywordStatus.duration_seconds % 60)}s` 
                    : 'N/A'}
                </div>
              </>
            )}
          </div>
        )}
      </div>
      
      {/* Steps progress */}
      <ul className="space-y-6">
        {steps.map((step, index) => (
          <li key={step.name} className="relative">
            {/* Step indicator */}
            <div className="flex items-center">
              <div className={`
                flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center
                ${step.status === 'waiting' ? 'bg-gray-200 text-gray-500' :
                  step.status === 'in-progress' ? 'bg-blue-100 text-blue-600 animate-pulse' :
                  step.status === 'complete' ? 'bg-green-100 text-green-500' :
                  'bg-red-100 text-red-500'}
              `}>
                {step.status === 'waiting' && <Clock size={16} />}
                {step.status === 'in-progress' && <Clock size={16} />}
                {step.status === 'complete' && <CheckCircle size={16} />}
                {step.status === 'error' && <XCircle size={16} />}
              </div>
              
              {/* Step content */}
              <div className="ml-4 flex-grow">
                <h4 className="font-medium">{step.name}: {step.description}</h4>
                
                {step.status === 'in-progress' && typeof step.percentage !== 'undefined' && (
                  <div className="mt-2">
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                      <div 
                        className="bg-accent h-2.5 rounded-full transition-all duration-500"
                        style={{ width: `${step.percentage}%` }}
                      ></div>
                    </div>
                    {step.currentItem && (
                      <p className="text-xs text-gray-500 mt-1">
                        Processing: {step.currentItem}
                      </p>
                    )}
                  </div>
                )}
                
                {/* Step metrics */}
                {typeof step.count !== 'undefined' && (
                  <p className="text-sm mt-1">
                    {index === 0 ? (
                      <>Found <span className="font-medium">{step.count}</span> products</>
                    ) : (
                      <>Enriched <span className="font-medium">{step.count}</span> of <span className="font-medium">{step.total || 0}</span> domains</>
                    )}
                  </p>
                )}
              </div>
            </div>
            
            {/* Vertical line connecting steps */}
            {index < steps.length - 1 && (
              <div className="absolute top-8 left-4 -ml-px h-10 w-0.5 bg-gray-200"></div>
            )}
          </li>
        ))}
      </ul>
      
      {/* Real-time logs */}
      {logs.length > 0 && (
        <div className="mt-6">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Live Logs</h4>
          <div className="bg-gray-900 text-gray-100 p-3 rounded-md text-xs font-mono h-32 overflow-y-auto">
            {logs.slice(-20).map((log, idx) => (
              <div key={idx} className={`
                ${log.level === 'error' ? 'text-red-400' : 
                  log.level === 'warning' ? 'text-yellow-400' : 
                  log.level === 'success' ? 'text-green-400' : 'text-gray-300'}
              `}>
                [{new Date(log.timestamp).toLocaleTimeString()}] {log.message}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-start">
            <AlertTriangle className="flex-shrink-0 h-5 w-5 text-red-400" aria-hidden="true" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error occurred</h3>
              <div className="mt-2 text-sm text-red-700">{error}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
