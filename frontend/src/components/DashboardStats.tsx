'use client';

import { Package, Globe, Award, Search, RefreshCw } from 'lucide-react';
import { useApi } from '@/hooks/useApiClient';
import { DashboardStats as Stats } from '@/types/api';

export function DashboardStats() {
  const { data: stats, error, mutate } = useApi<Stats>('/dashboard/stats', {
    refreshInterval: 30000, // Auto-refresh every 30 seconds
  });

  const loading = !stats && !error;

  const handleRefresh = () => {
    mutate();
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="card p-4">
            <div className="animate-pulse">
              <div className="h-10 w-10 bg-gray-300 rounded-lg mb-3"></div>
              <div className="h-4 bg-gray-300 rounded w-1/2 mb-2"></div>
              <div className="h-6 bg-gray-300 rounded w-3/4"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-4 text-center text-red-600">
        <p>Failed to load statistics</p>
        <button 
          onClick={handleRefresh}
          className="mt-2 text-sm text-blue-600 hover:text-blue-800"
        >
          Try again
        </button>
      </div>
    );
  }

  const statCards = [
    {
      icon: Package,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      label: 'Total Products',
      value: stats?.total_products || 0,
    },
    {
      icon: Globe,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      label: 'Unique Domains',
      value: stats?.unique_domains || 0,
    },
    {
      icon: Award,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
      label: 'Enriched Domains',
      value: stats?.enriched_domains || 0,
    },
    {
      icon: Search,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
      label: 'Keywords Tracked',
      value: stats?.total_keywords || 0,
    },
  ];

  // Get unique keywords from recent_keywords
  const uniqueKeywords = stats?.recent_keywords 
    ? Array.from(new Set(stats.recent_keywords.filter(k => k)))
    : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-primary">Market Intelligence Overview</h2>
        <button
          onClick={handleRefresh}
          className="text-gray-500 hover:text-gray-700 transition-colors"
          title="Refresh stats"
        >
          <RefreshCw size={20} />
        </button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div key={index} className="card p-4 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <div className={`inline-flex p-2 rounded-lg ${stat.bgColor}`}>
                    <Icon className={stat.color} size={24} />
                  </div>
                  <p className="text-sm text-gray-600 mt-2">{stat.label}</p>
                  <p className="text-2xl font-bold mt-1">
                    {stat.value.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {uniqueKeywords.length > 0 && (
        <div className="card p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Recent Keywords</h3>
          <div className="flex flex-wrap gap-2">
            {uniqueKeywords.slice(0, 8).map((keyword, idx) => (
              <span 
                key={idx} 
                className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
              >
                {keyword}
              </span>
            ))}
            {uniqueKeywords.length > 8 && (
              <span className="px-3 py-1 text-gray-500 text-sm">
                +{uniqueKeywords.length - 8} more
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
