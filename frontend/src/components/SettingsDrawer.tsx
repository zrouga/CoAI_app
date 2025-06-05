'use client';

import { useState, useEffect } from 'react';
import { X, Eye, EyeOff, Save, Settings } from 'lucide-react';
import { useApi, api } from '@/hooks/useApiClient';
import toast from 'react-hot-toast';

interface SettingsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ApiKeys {
  apify_token: string;
  scraper_api_key: string;
}

interface PipelineSettings {
  max_ads: number;
  poll_interval: number;
  actor_concurrency: number;
  min_ad_spend: number;
  timeout: number;
}

export function SettingsDrawer({ isOpen, onClose }: SettingsDrawerProps) {
  const [apiKeys, setApiKeys] = useState<ApiKeys>({
    apify_token: '',
    scraper_api_key: '',
  });
  const [showKeys, setShowKeys] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'api' | 'pipeline'>('api');
  
  // Fetch pipeline settings
  const { data: settings, mutate: mutateSettings } = useApi<PipelineSettings>('/settings');
  const [pipelineSettings, setPipelineSettings] = useState<PipelineSettings>({
    max_ads: 50,
    poll_interval: 15,
    actor_concurrency: 5,
    min_ad_spend: 0,
    timeout: 900
  });
  
  // Update local state when settings are fetched
  useEffect(() => {
    if (settings) {
      setPipelineSettings(settings);
    }
  }, [settings]);
  
  // Load API keys from localStorage on mount
  useEffect(() => {
    const savedKeys = localStorage.getItem('api_keys');
    if (savedKeys) {
      setApiKeys(JSON.parse(savedKeys));
    }
  }, [isOpen]);

  const handleApiKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setApiKeys(prev => ({ ...prev, [name]: value }));
  };

  const handlePipelineChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setPipelineSettings(prev => ({ 
      ...prev, 
      [name]: parseInt(value) || 0 
    }));
  };

  const saveSettings = async () => {
    setIsSaving(true);
    
    try {
      if (activeTab === 'api') {
        // Store API keys in localStorage
        localStorage.setItem('api_keys', JSON.stringify(apiKeys));
        toast.success('API keys saved successfully');
      } else {
        // Save pipeline settings to backend
        await api.put('/settings', pipelineSettings);
        mutateSettings(); // Refresh settings
        toast.success('Pipeline settings saved successfully');
      }
      onClose();
    } catch (error) {
      toast.error(`Failed to save ${activeTab === 'api' ? 'API keys' : 'pipeline settings'}`);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 overflow-hidden z-50">
      <div className="absolute inset-0 overflow-hidden">
        {/* Backdrop */}
        <div 
          className="absolute inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
        ></div>
        
        {/* Drawer container */}
        <section className="absolute inset-y-0 right-0 pl-10 max-w-full flex">
          {/* Drawer panel */}
          <div className="relative w-screen max-w-md">
            <div className="h-full flex flex-col py-6 bg-white shadow-xl overflow-y-auto">
              {/* Header */}
              <div className="px-4 sm:px-6 flex items-center justify-between">
                <h2 className="text-lg font-medium text-gray-900">Settings</h2>
                <button
                  type="button"
                  className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-primary"
                  onClick={onClose}
                >
                  <span className="sr-only">Close panel</span>
                  <X size={24} aria-hidden="true" />
                </button>
              </div>
              
              {/* Body */}
              <div className="mt-6 relative flex-1 px-4 sm:px-6">
                {/* Tabs */}
                <div className="border-b border-gray-200 mb-6">
                  <nav className="-mb-px flex space-x-8">
                    <button
                      onClick={() => setActiveTab('api')}
                      className={`py-2 px-1 border-b-2 font-medium text-sm ${
                        activeTab === 'api'
                          ? 'border-primary text-primary'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      API Keys
                    </button>
                    <button
                      onClick={() => setActiveTab('pipeline')}
                      className={`py-2 px-1 border-b-2 font-medium text-sm ${
                        activeTab === 'pipeline'
                          ? 'border-primary text-primary'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      Pipeline Settings
                    </button>
                  </nav>
                </div>

                {/* Tab content */}
                <div className="space-y-6">
                  {activeTab === 'api' ? (
                    <>
                      <p className="text-sm text-gray-500">
                        Configure your API keys for external services. These are stored locally in your browser.
                      </p>
                  
                  <div>
                    <div className="flex justify-between items-center">
                      <label htmlFor="apify_token" className="block text-sm font-medium text-gray-700">
                        Apify Token
                      </label>
                      <button
                        type="button"
                        onClick={() => setShowKeys(!showKeys)}
                        className="text-xs text-primary flex items-center"
                      >
                        {showKeys ? (
                          <>
                            <EyeOff size={14} className="mr-1" />
                            Hide
                          </>
                        ) : (
                          <>
                            <Eye size={14} className="mr-1" />
                            Show
                          </>
                        )}
                      </button>
                    </div>
                    <div className="mt-1">
                      <input
                        type={showKeys ? "text" : "password"}
                        name="apify_token"
                        id="apify_token"
                        className="input w-full"
                        placeholder="Enter your Apify API token"
                        value={apiKeys.apify_token}
                        onChange={handleApiKeyChange}
                      />
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      Get your key from <a href="https://my.apify.com/account#/integrations" target="_blank" rel="noreferrer" className="text-primary hover:underline">Apify dashboard</a>
                    </p>
                  </div>
                  
                  <div>
                    <label htmlFor="scraper_api_key" className="block text-sm font-medium text-gray-700">
                      ScraperAPI Key
                    </label>
                    <div className="mt-1">
                      <input
                        type={showKeys ? "text" : "password"}
                        name="scraper_api_key"
                        id="scraper_api_key"
                        className="input w-full"
                        placeholder="Enter your ScraperAPI key"
                        value={apiKeys.scraper_api_key}
                        onChange={handleApiKeyChange}
                      />
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      Get your key from <a href="https://www.scraperapi.com/dashboard/" target="_blank" rel="noreferrer" className="text-primary hover:underline">ScraperAPI dashboard</a>
                    </p>
                  </div>
                  
                    </>
                  ) : (
                    <>
                      <p className="text-sm text-gray-500">
                        Configure pipeline behavior and performance settings.
                      </p>
                      
                      <div>
                        <label htmlFor="max_ads" className="block text-sm font-medium text-gray-700">
                          Max Ads per Search
                        </label>
                        <input
                          type="number"
                          name="max_ads"
                          id="max_ads"
                          className="input w-full mt-1"
                          value={pipelineSettings.max_ads}
                          onChange={handlePipelineChange}
                          min="1"
                          max="200"
                        />
                        <p className="mt-1 text-xs text-gray-500">Maximum number of ads to process per keyword</p>
                      </div>
                      
                      <div>
                        <label htmlFor="poll_interval" className="block text-sm font-medium text-gray-700">
                          Poll Interval (seconds)
                        </label>
                        <input
                          type="number"
                          name="poll_interval"
                          id="poll_interval"
                          className="input w-full mt-1"
                          value={pipelineSettings.poll_interval}
                          onChange={handlePipelineChange}
                          min="5"
                          max="60"
                        />
                        <p className="mt-1 text-xs text-gray-500">How often to check Apify job status</p>
                      </div>
                      
                      <div>
                        <label htmlFor="actor_concurrency" className="block text-sm font-medium text-gray-700">
                          Actor Concurrency
                        </label>
                        <input
                          type="number"
                          name="actor_concurrency"
                          id="actor_concurrency"
                          className="input w-full mt-1"
                          value={pipelineSettings.actor_concurrency}
                          onChange={handlePipelineChange}
                          min="1"
                          max="10"
                        />
                        <p className="mt-1 text-xs text-gray-500">Number of concurrent Apify actors</p>
                      </div>
                      
                      <div>
                        <label htmlFor="min_ad_spend" className="block text-sm font-medium text-gray-700">
                          Minimum Ad Spend ($)
                        </label>
                        <input
                          type="number"
                          name="min_ad_spend"
                          id="min_ad_spend"
                          className="input w-full mt-1"
                          value={pipelineSettings.min_ad_spend}
                          onChange={handlePipelineChange}
                          min="0"
                        />
                        <p className="mt-1 text-xs text-gray-500">Filter out ads below this spend threshold</p>
                      </div>
                      
                      <div>
                        <label htmlFor="timeout" className="block text-sm font-medium text-gray-700">
                          Timeout (seconds)
                        </label>
                        <input
                          type="number"
                          name="timeout"
                          id="timeout"
                          className="input w-full mt-1"
                          value={pipelineSettings.timeout}
                          onChange={handlePipelineChange}
                          min="60"
                          max="3600"
                        />
                        <p className="mt-1 text-xs text-gray-500">Maximum time to wait for pipeline completion</p>
                      </div>
                    </>
                  )}
                  
                  <div className="pt-4">
                    <button
                      type="button"
                      className="btn-primary w-full flex items-center justify-center"
                      onClick={saveSettings}
                      disabled={isSaving}
                    >
                      {isSaving ? (
                        <>
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Saving...
                        </>
                      ) : (
                        <>
                          <Save className="mr-2" size={18} />
                          Save {activeTab === 'api' ? 'API Keys' : 'Settings'}
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
