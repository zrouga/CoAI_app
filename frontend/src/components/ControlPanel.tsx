'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Save, Sliders } from 'lucide-react';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { DEFAULT_RUN_CONFIG } from '@/types/api';
import toast from 'react-hot-toast';

interface ControlPanelProps {
  isDisabled?: boolean;
}

// Zod schema for control panel validation
const controlPanelSchema = z.object({
  // Apify settings
  max_ads: z.number().int().min(1).max(500),
  poll_interval_seconds: z.number().int().min(5).max(60),
  apify_concurrency: z.number().int().min(1).max(20),
  apify_timeout_seconds: z.number().int().min(60).max(3600),
  min_ad_spend_usd: z.number().int().min(0),
  
  // Traffic/ScraperAPI settings
  max_domains_per_minute: z.number().int().min(1).max(100),
  domain_batch_size: z.number().int().min(1).max(50),
  retry_attempts: z.number().int().min(0).max(5),
  cache_ttl_days: z.number().int().min(1).max(90),
  html_fallback_enabled: z.boolean(),
  
  // General settings
  log_level: z.enum(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
  dry_run_mode: z.boolean(),
});

type ControlPanelFormData = z.infer<typeof controlPanelSchema>;

const LOG_LEVEL_OPTIONS = ['DEBUG', 'INFO', 'WARNING', 'ERROR'];

const LOCAL_STORAGE_KEY = 'market_intelligence_control_panel';

export function ControlPanel({ isDisabled = false }: ControlPanelProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    apify: true,
    traffic: false,
    general: false
  });
  
  // Initialize form with default values from localStorage or defaults
  const savedConfig = typeof window !== 'undefined' 
    ? JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || '{}')
    : {};
    
  const defaultValues: ControlPanelFormData = {
    ...DEFAULT_RUN_CONFIG,
    ...savedConfig
  } as ControlPanelFormData;

  const { register, handleSubmit, formState: { errors }, reset } = useForm<ControlPanelFormData>({
    resolver: zodResolver(controlPanelSchema),
    defaultValues
  });

  // Load saved config on mount
  useEffect(() => {
    const savedConfig = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (savedConfig) {
      reset(JSON.parse(savedConfig));
    }
  }, [reset]);

  const saveSettings = (data: ControlPanelFormData) => {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(data));
    toast.success('Settings saved successfully');
  };

  const toggleSection = (section: string) => {
    setExpanded(prev => ({ ...prev, [section]: !prev[section] }));
  };

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit(saveSettings)} className="space-y-6">
        {/* Apify Settings Section */}
        <div className="border border-gray-200 rounded-md overflow-hidden">
          <button
            type="button"
            className="w-full px-4 py-2 flex justify-between items-center bg-gray-50 hover:bg-gray-100"
            onClick={() => toggleSection('apify')}
          >
            <span className="font-medium">Apify (Facebook Ad Library)</span>
            <Sliders className={`transition-transform ${expanded.apify ? 'rotate-180' : ''}`} size={18} />
          </button>
          
          {expanded.apify && (
            <div className="p-4 space-y-4 bg-white">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="max_ads" className="label">Max Ads / Keyword</label>
                  <input
                    type="number"
                    id="max_ads"
                    className={`input w-full ${errors.max_ads ? 'border-red-500' : ''}`}
                    disabled={isDisabled}
                    {...register('max_ads', { valueAsNumber: true })}
                  />
                  {errors.max_ads && (
                    <p className="text-red-500 text-sm mt-1">{errors.max_ads.message?.toString()}</p>
                  )}
                </div>
                
                <div>
                  <label htmlFor="apify_actor" className="label">Actor Name</label>
                  <input
                    type="text"
                    id="apify_actor"
                    className="input w-full bg-gray-100"
                    value={DEFAULT_RUN_CONFIG.apify_actor}
                    disabled
                  />
                  <p className="text-xs text-gray-500 mt-1">Fixed value, cannot be changed</p>
                </div>
                
                <div>
                  <label htmlFor="poll_interval_seconds" className="label">Poll Interval (seconds)</label>
                  <input
                    type="number"
                    id="poll_interval_seconds"
                    className={`input w-full ${errors.poll_interval_seconds ? 'border-red-500' : ''}`}
                    disabled={isDisabled}
                    {...register('poll_interval_seconds', { valueAsNumber: true })}
                  />
                  {errors.poll_interval_seconds && (
                    <p className="text-red-500 text-sm mt-1">{errors.poll_interval_seconds.message?.toString()}</p>
                  )}
                </div>
                
                <div>
                  <label htmlFor="apify_concurrency" className="label">Actor Concurrency</label>
                  <input
                    type="number"
                    id="apify_concurrency"
                    className={`input w-full ${errors.apify_concurrency ? 'border-red-500' : ''}`}
                    disabled={isDisabled}
                    {...register('apify_concurrency', { valueAsNumber: true })}
                  />
                  {errors.apify_concurrency && (
                    <p className="text-red-500 text-sm mt-1">{errors.apify_concurrency.message?.toString()}</p>
                  )}
                </div>
                
                <div>
                  <label htmlFor="apify_timeout_seconds" className="label">Timeout (seconds)</label>
                  <input
                    type="number"
                    id="apify_timeout_seconds"
                    className={`input w-full ${errors.apify_timeout_seconds ? 'border-red-500' : ''}`}
                    disabled={isDisabled}
                    {...register('apify_timeout_seconds', { valueAsNumber: true })}
                  />
                  {errors.apify_timeout_seconds && (
                    <p className="text-red-500 text-sm mt-1">{errors.apify_timeout_seconds.message?.toString()}</p>
                  )}
                </div>
                
                <div>
                  <label htmlFor="min_ad_spend_usd" className="label">Min Ad Spend USD</label>
                  <input
                    type="number"
                    id="min_ad_spend_usd"
                    className={`input w-full ${errors.min_ad_spend_usd ? 'border-red-500' : ''}`}
                    disabled={isDisabled}
                    {...register('min_ad_spend_usd', { valueAsNumber: true })}
                  />
                  {errors.min_ad_spend_usd && (
                    <p className="text-red-500 text-sm mt-1">{errors.min_ad_spend_usd.message?.toString()}</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Traffic/ScraperAPI Settings */}
        <div className="border border-gray-200 rounded-md overflow-hidden">
          <button
            type="button"
            className="w-full px-4 py-2 flex justify-between items-center bg-gray-50 hover:bg-gray-100"
            onClick={() => toggleSection('traffic')}
          >
            <span className="font-medium">Traffic / ScraperAPI</span>
            <Sliders className={`transition-transform ${expanded.traffic ? 'rotate-180' : ''}`} size={18} />
          </button>
          
          {expanded.traffic && (
            <div className="p-4 space-y-4 bg-white">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="max_domains_per_minute" className="label">Max Domains / Min</label>
                  <input
                    type="number"
                    id="max_domains_per_minute"
                    className={`input w-full ${errors.max_domains_per_minute ? 'border-red-500' : ''}`}
                    disabled={isDisabled}
                    {...register('max_domains_per_minute', { valueAsNumber: true })}
                  />
                  {errors.max_domains_per_minute && (
                    <p className="text-red-500 text-sm mt-1">{errors.max_domains_per_minute.message?.toString()}</p>
                  )}
                </div>
                
                <div>
                  <label htmlFor="domain_batch_size" className="label">Batch Size</label>
                  <input
                    type="number"
                    id="domain_batch_size"
                    className={`input w-full ${errors.domain_batch_size ? 'border-red-500' : ''}`}
                    disabled={isDisabled}
                    {...register('domain_batch_size', { valueAsNumber: true })}
                  />
                  {errors.domain_batch_size && (
                    <p className="text-red-500 text-sm mt-1">{errors.domain_batch_size.message?.toString()}</p>
                  )}
                </div>
                
                <div>
                  <label htmlFor="retry_attempts" className="label">Retry Attempts</label>
                  <input
                    type="number"
                    id="retry_attempts"
                    className={`input w-full ${errors.retry_attempts ? 'border-red-500' : ''}`}
                    disabled={isDisabled}
                    {...register('retry_attempts', { valueAsNumber: true })}
                  />
                  {errors.retry_attempts && (
                    <p className="text-red-500 text-sm mt-1">{errors.retry_attempts.message?.toString()}</p>
                  )}
                </div>
                
                <div>
                  <label htmlFor="cache_ttl_days" className="label">Cache TTL (days)</label>
                  <input
                    type="number"
                    id="cache_ttl_days"
                    className={`input w-full ${errors.cache_ttl_days ? 'border-red-500' : ''}`}
                    disabled={isDisabled}
                    {...register('cache_ttl_days', { valueAsNumber: true })}
                  />
                  {errors.cache_ttl_days && (
                    <p className="text-red-500 text-sm mt-1">{errors.cache_ttl_days.message?.toString()}</p>
                  )}
                </div>
                
                <div className="col-span-2">
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="html_fallback_enabled"
                      className="h-5 w-5 rounded border-gray-300 text-primary focus:ring-primary"
                      disabled={isDisabled}
                      {...register('html_fallback_enabled')}
                    />
                    <label htmlFor="html_fallback_enabled" className="ml-2 label">HTML Fallback Enabled</label>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* General Settings */}
        <div className="border border-gray-200 rounded-md overflow-hidden">
          <button
            type="button"
            className="w-full px-4 py-2 flex justify-between items-center bg-gray-50 hover:bg-gray-100"
            onClick={() => toggleSection('general')}
          >
            <span className="font-medium">General Settings</span>
            <Sliders className={`transition-transform ${expanded.general ? 'rotate-180' : ''}`} size={18} />
          </button>
          
          {expanded.general && (
            <div className="p-4 space-y-4 bg-white">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="log_level" className="label">Log Level</label>
                  <select
                    id="log_level"
                    className={`input w-full ${errors.log_level ? 'border-red-500' : ''}`}
                    disabled={isDisabled}
                    {...register('log_level')}
                  >
                    {LOG_LEVEL_OPTIONS.map(level => (
                      <option key={level} value={level}>{level}</option>
                    ))}
                  </select>
                  {errors.log_level && (
                    <p className="text-red-500 text-sm mt-1">{errors.log_level.message?.toString()}</p>
                  )}
                </div>
                
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="dry_run_mode"
                    className="h-5 w-5 rounded border-gray-300 text-primary focus:ring-primary"
                    disabled={isDisabled}
                    {...register('dry_run_mode')}
                  />
                  <label htmlFor="dry_run_mode" className="ml-2 label">Dry Run Mode (Skip DB Writes)</label>
                </div>
              </div>
            </div>
          )}
        </div>

        <button
          type="submit"
          className="btn-outline flex items-center justify-center w-full"
          disabled={isDisabled}
        >
          <Save className="mr-2" size={18} />
          Save Settings
        </button>
      </form>

      <p className="text-xs text-gray-500 italic">
        Settings are persisted in your browser and applied to all future analysis runs.
      </p>
    </div>
  );
}
