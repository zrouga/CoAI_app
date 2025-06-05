'use client';

import { useState, useEffect } from 'react';
import { 
  ArrowUpDown, Download, Trash2, ExternalLink, 
  AlertCircle, BarChart2, Search 
} from 'lucide-react';
import { Sparklines, SparklinesLine } from 'react-sparklines';
import { ProductResult } from '@/types/api';
import { getKeywordResults, deleteKeywordResults } from '@/services/api';
import { CSVLink } from 'react-csv';
import toast from 'react-hot-toast';

interface ResultsTableProps {
  keyword: string;
}

export function ResultsTable({ keyword }: ResultsTableProps) {
  const [results, setResults] = useState<ProductResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState<keyof ProductResult>('monthly_visits');
  const [sortDesc, setSortDesc] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const pageSize = 20;

  // Fetch results when keyword changes
  useEffect(() => {
    if (!keyword) {
      setResults([]);
      return;
    }

    const fetchResults = async () => {
      setLoading(true);
      try {
        const data = await getKeywordResults(
          keyword,
          1, // Start with first page
          pageSize,
          sortBy as string,
          sortDesc
        );
        setResults(data);
        setHasMore(data.length === pageSize);
        setPage(1);
      } catch (error) {
        console.error('Failed to fetch results:', error);
        setResults([]);
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [keyword, sortBy, sortDesc]);

  // Load more results (pagination)
  const loadMore = async () => {
    if (!keyword || loading) return;
    
    setLoading(true);
    try {
      const nextPage = page + 1;
      const data = await getKeywordResults(
        keyword,
        nextPage,
        pageSize,
        sortBy as string,
        sortDesc
      );
      
      if (data.length > 0) {
        setResults(prev => [...prev, ...data]);
        setPage(nextPage);
        setHasMore(data.length === pageSize);
      } else {
        setHasMore(false);
      }
    } catch (error) {
      console.error('Failed to load more results:', error);
    } finally {
      setLoading(false);
    }
  };

  // Handle sorting
  const handleSort = (column: keyof ProductResult) => {
    if (sortBy === column) {
      setSortDesc(!sortDesc);
    } else {
      setSortBy(column);
      setSortDesc(true);
    }
  };

  // Handle deleting results
  const handleDelete = async () => {
    if (!keyword) return;
    
    if (confirm(`Are you sure you want to delete all results for "${keyword}"?`)) {
      try {
        await deleteKeywordResults(keyword);
        setResults([]);
        toast.success(`Results for "${keyword}" deleted successfully.`);
      } catch (error) {
        console.error('Failed to delete results:', error);
        toast.error('Failed to delete results. Please try again.');
      }
    }
  };

  // Filter results by search term
  const filteredResults = searchTerm 
    ? results.filter(item => 
        item.brand_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.brand_domain?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.product_page_url.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : results;

  // Create CSV data for export
  const exportData = filteredResults.map(item => ({
    'Brand Name': item.brand_name || 'Unknown',
    'Domain': item.brand_domain || 'Unknown',
    'Product URL': item.product_page_url,
    'Keyword': item.discovery_keyword,
    'Monthly Visits': item.monthly_visits || 'N/A',
    'Ads Count': item.ads_count,
    'Source': item.data_source || 'Unknown',
    'Discovered': new Date(item.discovered_at).toLocaleString()
  }));

  // Format numbers with commas
  const formatNumber = (num: number | undefined) => {
    if (num === undefined || num === null) return 'N/A';
    return new Intl.NumberFormat().format(num);
  };

  // Extract domain from URL
  const extractDomain = (url: string) => {
    try {
      return new URL(url).hostname.replace(/^www\./, '');
    } catch {
      return url;
    }
  };

  if (!keyword) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Search size={48} className="mx-auto mb-3 opacity-50" />
        <p>Enter a keyword above to view market research results.</p>
      </div>
    );
  }

  if (loading && results.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
        <p className="mt-4 text-gray-600">Loading results...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Controls bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4">
        <div className="relative flex-1 min-w-[240px]">
          <input
            type="text"
            placeholder="Search results..."
            className="input pl-10 w-full"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
        </div>
        
        <div className="flex items-center gap-2">
          {results.length > 0 && (
            <>
              <CSVLink
                data={exportData}
                filename={`market-research-${keyword}-${new Date().toISOString().slice(0, 10)}.csv`}
                className="btn-outline flex items-center py-1.5"
              >
                <Download size={16} className="mr-1" />
                Export CSV
              </CSVLink>
              
              <button
                onClick={handleDelete}
                className="btn-outline border-red-500 text-red-500 hover:bg-red-500 hover:text-white py-1.5 flex items-center"
              >
                <Trash2 size={16} className="mr-1" />
                Delete Results
              </button>
            </>
          )}
        </div>
      </div>

      {/* Results count */}
      <div className="text-sm text-gray-500">
        {filteredResults.length > 0 ? (
          <p>Showing {filteredResults.length} result{filteredResults.length !== 1 ? 's' : ''}</p>
        ) : results.length > 0 ? (
          <p>No matching results. Try changing your search.</p>
        ) : (
          <div className="text-center py-8">
            <AlertCircle size={48} className="mx-auto mb-3 opacity-50 text-amber-500" />
            <p className="text-base">No results found for this keyword yet.</p>
          </div>
        )}
      </div>

      {/* Results table */}
      {filteredResults.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th 
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer"
                  onClick={() => handleSort('brand_name')}
                >
                  <div className="flex items-center">
                    Brand
                    {sortBy === 'brand_name' && (
                      <ArrowUpDown size={14} className={`ml-1 ${sortDesc ? 'transform rotate-180' : ''}`} />
                    )}
                  </div>
                </th>
                <th 
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer"
                  onClick={() => handleSort('monthly_visits')}
                >
                  <div className="flex items-center">
                    Traffic
                    {sortBy === 'monthly_visits' && (
                      <ArrowUpDown size={14} className={`ml-1 ${sortDesc ? 'transform rotate-180' : ''}`} />
                    )}
                  </div>
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Trends (12mo)
                </th>
                <th 
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer"
                  onClick={() => handleSort('ads_count')}
                >
                  <div className="flex items-center">
                    Ads
                    {sortBy === 'ads_count' && (
                      <ArrowUpDown size={14} className={`ml-1 ${sortDesc ? 'transform rotate-180' : ''}`} />
                    )}
                  </div>
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredResults.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-4 py-4 whitespace-nowrap">
                    <div className="flex flex-col">
                      <div className="text-sm font-medium text-gray-900">
                        {item.brand_name || extractDomain(item.product_page_url)}
                      </div>
                      {item.brand_domain && (
                        <div className="text-sm text-gray-500">{item.brand_domain}</div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {formatNumber(item.monthly_visits)}
                      <span className="text-xs text-gray-500 ml-1">visits/mo</span>
                    </div>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    {item.traffic_sparkline ? (
                      <div className="h-10 w-24">
                        <Sparklines data={item.traffic_sparkline.values.map(v => v || 0)} height={30}>
                          <SparklinesLine color="#50A5FF" />
                        </Sparklines>
                      </div>
                    ) : (
                      <div className="text-sm text-gray-500 flex items-center">
                        <BarChart2 size={14} className="mr-1" />
                        No data
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                    {item.ads_count}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                    <a 
                      href={item.product_page_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-900 inline-flex items-center"
                    >
                      Visit <ExternalLink size={14} className="ml-1" />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Load more button */}
      {hasMore && (
        <div className="text-center mt-6">
          <button
            onClick={loadMore}
            className="btn-outline py-2"
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Load More Results'}
          </button>
        </div>
      )}
    </div>
  );
}
