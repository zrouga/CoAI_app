'use client';

import { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';
import { subscribeToStatusUpdates, getKeywordStatus } from '@/services/api';
import { KeywordStatus, PipelineStatus } from '@/types/api';
import toast from 'react-hot-toast';

interface ProgressStep {
  name: string;
  description: string;
  status: 'waiting' | 'in-progress' | 'complete' | 'error';
  count?: number;
  total?: number;
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

  // Map the API status to the UI steps
  useEffect(() => {
    if (!keyword) {
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
      return;
    }

    if (!keywordStatus) {
      return;
    }

    const newSteps: ProgressStep[] = [
      {
        name: 'Step 1',
        description: 'Facebook Ad Library Scraping',
        status: 'waiting',
        count: keywordStatus.step1_products,
      },
      {
        name: 'Step 2',
        description: 'Traffic Data Enrichment',
        status: 'waiting',
        count: keywordStatus.step2_enriched,
        total: keywordStatus.step1_products,
      }
    ];

    // Update steps based on pipeline status
    switch (keywordStatus.status) {
      case PipelineStatus.RUNNING_STEP1:
        newSteps[0].status = 'in-progress';
        break;
      case PipelineStatus.COMPLETED_STEP1:
        newSteps[0].status = 'complete';
        newSteps[1].status = 'waiting';
        break;
      case PipelineStatus.RUNNING_STEP2:
        newSteps[0].status = 'complete';
        newSteps[1].status = 'in-progress';
        break;
      case PipelineStatus.COMPLETED_STEP2:
      case PipelineStatus.COMPLETED:
        newSteps[0].status = 'complete';
        newSteps[1].status = 'complete';
        
        // Notify parent that pipeline has completed
        if (isRunning) {
          onComplete();
          toast.success(`Analysis completed for "${keyword}"!`);
        }
        break;
      case PipelineStatus.FAILED:
        // Mark the appropriate step as failed
        if (keywordStatus.step1_products === 0) {
          newSteps[0].status = 'error';
        } else {
          newSteps[0].status = 'complete';
          newSteps[1].status = 'error';
        }
        
        // Show error toast
        if (isRunning && keywordStatus.errors.length > 0) {
          onComplete();
          toast.error('Analysis failed. Check logs for details.');
          setError(keywordStatus.errors[0]);
        }
        break;
      default:
        break;
    }

    setSteps(newSteps);
  }, [keyword, keywordStatus, isRunning, onComplete]);

  // Fetch initial status and set up SSE subscription
  useEffect(() => {
    let cleanup: (() => void) | undefined;
    
    if (keyword) {
      // Get initial status
      getKeywordStatus(keyword)
        .then(status => {
          setKeywordStatus(status);
          
          // If still running, subscribe to updates
          if (
            [
              PipelineStatus.RUNNING_STEP1,
              PipelineStatus.COMPLETED_STEP1,
              PipelineStatus.RUNNING_STEP2
            ].includes(status.status)
          ) {
            cleanup = subscribeToStatusUpdates(
              keyword,
              (newStatus) => setKeywordStatus(newStatus),
              (error) => console.error('SSE error:', error)
            );
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
    }

    return () => {
      if (cleanup) cleanup();
    };
  }, [keyword]);

  // Subscribe to SSE updates when pipeline starts running
  useEffect(() => {
    let cleanup: (() => void) | undefined;
    
    if (keyword && isRunning) {
      cleanup = subscribeToStatusUpdates(
        keyword,
        (newStatus) => setKeywordStatus(newStatus),
        (error) => console.error('SSE error:', error)
      );
    }

    return () => {
      if (cleanup) cleanup();
    };
  }, [keyword, isRunning]);

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
        <h3 className="font-medium mb-2">Currently analyzing: <span className="font-bold text-primary">{keyword}</span></h3>
        
        {keywordStatus && keywordStatus.status !== PipelineStatus.NOT_STARTED && (
          <div className="text-sm text-gray-600 flex flex-col md:flex-row gap-4">
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
                    ? `${Math.floor(keywordStatus.duration_seconds / 60)}m ${keywordStatus.duration_seconds % 60}s` 
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
                
                {step.status === 'in-progress' && (
                  <div className="mt-2">
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                      <div className="bg-accent h-2.5 rounded-full animate-pulse w-[90%]"></div>
                    </div>
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
