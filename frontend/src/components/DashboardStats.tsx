'use client';

import { useEffect, useState } from 'react';
import { TrendingUp, Database, Globe, Tag } from 'lucide-react';
import { getDashboardStats } from '@/services/api';
import { DashboardStats as DashboardStatsType } from '@/types/api';

export function DashboardStats() {
  const [stats, setStats] = useState<DashboardStatsType>({
    total_products: 0,
    unique_domains: 0,
    enriched_domains: 0,
    total_keywords: 0,
    recent_keywords: []
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await getDashboardStats();
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch dashboard stats:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
    
    // Refresh stats every minute
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, []);

  // Format numbers with commas
  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* Total Products */}
      <div className="card bg-white shadow-sm p-4 flex items-center space-x-4">
        <div className="flex-shrink-0 h-12 w-12 rounded-full bg-primary-50 flex items-center justify-center">
          <Database className="h-6 w-6 text-primary" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-500">Total Products</p>
          {isLoading ? (
            <div className="h-6 w-24 bg-gray-200 animate-pulse rounded"></div>
          ) : (
            <p className="text-2xl font-semibold text-gray-900">{formatNumber(stats.total_products)}</p>
          )}
        </div>
      </div>

      {/* Unique Domains */}
      <div className="card bg-white shadow-sm p-4 flex items-center space-x-4">
        <div className="flex-shrink-0 h-12 w-12 rounded-full bg-accent-50 flex items-center justify-center">
          <Globe className="h-6 w-6 text-accent" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-500">Unique Domains</p>
          {isLoading ? (
            <div className="h-6 w-24 bg-gray-200 animate-pulse rounded"></div>
          ) : (
            <p className="text-2xl font-semibold text-gray-900">{formatNumber(stats.unique_domains)}</p>
          )}
        </div>
      </div>

      {/* Enriched with Traffic */}
      <div className="card bg-white shadow-sm p-4 flex items-center space-x-4">
        <div className="flex-shrink-0 h-12 w-12 rounded-full bg-green-50 flex items-center justify-center">
          <TrendingUp className="h-6 w-6 text-green-500" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-500">Enriched with Traffic</p>
          {isLoading ? (
            <div className="h-6 w-24 bg-gray-200 animate-pulse rounded"></div>
          ) : (
            <p className="text-2xl font-semibold text-gray-900">
              {formatNumber(stats.enriched_domains)}
              <span className="text-sm text-gray-500 ml-1">
                ({stats.unique_domains ? 
                  Math.round((stats.enriched_domains / stats.unique_domains) * 100) : 0}%)
              </span>
            </p>
          )}
        </div>
      </div>

      {/* Keywords Analyzed */}
      <div className="card bg-white shadow-sm p-4 flex items-center space-x-4">
        <div className="flex-shrink-0 h-12 w-12 rounded-full bg-purple-50 flex items-center justify-center">
          <Tag className="h-6 w-6 text-purple-500" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-500">Keywords Analyzed</p>
          {isLoading ? (
            <div className="h-6 w-24 bg-gray-200 animate-pulse rounded"></div>
          ) : (
            <div>
              <p className="text-2xl font-semibold text-gray-900">{formatNumber(stats.total_keywords)}</p>
              {stats.recent_keywords.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {stats.recent_keywords.slice(0, 3).map((keyword) => (
                    <span key={keyword} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                      {keyword}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
