'use client';

import { useState, useEffect } from 'react';
import { 
  ArrowUpDown, Download, Trash2, ExternalLink, 
  AlertCircle, BarChart2, Search, ChevronDown, X 
} from 'lucide-react';
import { Sparklines, SparklinesLine } from 'react-sparklines';
import { usePaginatedApi, api } from '@/hooks/useApiClient';
import { CSVLink } from 'react-csv';
import toast from 'react-hot-toast';

interface ProductResult {
  id: number;
  brand_name?: string;
  brand_domain?: string;
  product_page_url: string;
  keyword?: string;
  monthly_visits?: number;
  traffic_data?: {
    monthly_visits?: number;
    data_source?: string;
  };
  traffic_sparkline?: {
    months: string[];
    values: number[];
  };
  ads_count?: number;
  first_discovered?: string;
  discovered_at?: string;
}

interface ResultsViewProps {
  keyword?: string;
}

export function ResultsView({ keyword }: ResultsViewProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState('first_discovered');
  const [sortDesc, setSortDesc] = useState(true);
  const [selectedKeyword, setSelectedKeyword] = useState(keyword || '');
  const [showKeywordDropdown, setShowKeywordDropdown] = useState(false);
  
  // Fetch available keywords
  const { data: keywordsData } = usePaginatedApi<{ items: string[] }>(
    '/results/keywords',
    1,
    100
  );
  const availableKeywords = keywordsData?.items || [];

  // Fetch products based on selected keyword
  const endpoint = selectedKeyword 
    ? `/results/products?keyword=${encodeURIComponent(selectedKeyword)}`
    : '/results/products';
    
  const { data, error, mutate } = usePaginatedApi<{
    items: ProductResult[];
    total: number;
    page: number;
    pages: number;
  }>(endpoint, page, 20, { sort_by: sortBy, sort_desc: sortDesc });

  const results = data?.items || [];
  const totalCount = data?.total || 0;
  const totalPages = data?.pages || 0;
  const loading = !data && !error;

  // Update selected keyword when prop changes
  useEffect(() => {
    if (keyword && keyword !== selectedKeyword) {
      setSelectedKeyword(keyword);
      setPage(1);
    }
  }, [keyword]);

  // Handle sorting
  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortDesc(!sortDesc);
    } else {
      setSortBy(column);
      setSortDesc(true);
    }
    setPage(1);
  };

  // Handle keyword selection
  const handleKeywordSelect = (kw: string) => {
    setSelectedKeyword(kw);
    setShowKeywordDropdown(false);
    setPage(1);
  };

  // Handle delete single product
  const handleDeleteProduct = async (productId: number) => {
    if (confirm('Are you sure you want to delete this product?')) {
      try {
        await api.delete(`/products/${productId}`);
        toast.success('Product deleted successfully');
        mutate(); // Refresh the data
      } catch (error) {
        toast.error('Failed to delete product');
      }
    }
  };

  // Handle delete all results for keyword
  const handleDeleteKeywordResults = async () => {
    if (!selectedKeyword) return;
    
    if (confirm(`Are you sure you want to delete all results for "${selectedKeyword}"?`)) {
      try {
        await api.delete(`/results/${encodeURIComponent(selectedKeyword)}`);
        toast.success(`Results for "${selectedKeyword}" deleted successfully`);
        setSelectedKeyword('');
        mutate();
      } catch (error) {
        toast.error('Failed to delete results');
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
    'Keyword': item.keyword || selectedKeyword || 'N/A',
    'Monthly Visits': item.monthly_visits || item.traffic_data?.monthly_visits || 'N/A',
    'Source': item.traffic_data?.data_source || 'Unknown',
    'Discovered': new Date(item.first_discovered || item.discovered_at || '').toLocaleString()
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

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
        <p className="mt-4 text-gray-600">Loading results...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Keyword selector */}
      <div className="flex items-center gap-4 pb-2">
        <div className="relative">
          <button
            onClick={() => setShowKeywordDropdown(!showKeywordDropdown)}
            className="btn-outline flex items-center gap-2 min-w-[200px] justify-between"
          >
            <span>{selectedKeyword || 'All Products'}</span>
            <ChevronDown size={16} className={`transition-transform ${showKeywordDropdown ? 'rotate-180' : ''}`} />
          </button>
          
          {showKeywordDropdown && (
            <div className="absolute top-full mt-1 w-full bg-white rounded-md shadow-lg border border-gray-200 z-10 max-h-60 overflow-y-auto">
              <button
                onClick={() => handleKeywordSelect('')}
                className="w-full text-left px-3 py-2 hover:bg-gray-50 border-b border-gray-100"
              >
                All Products
              </button>
              {availableKeywords.map((kw) => (
                <button
                  key={kw}
                  onClick={() => handleKeywordSelect(kw)}
                  className="w-full text-left px-3 py-2 hover:bg-gray-50"
                >
                  {kw}
                </button>
              ))}
            </div>
          )}
        </div>
        
        <span className="text-sm text-gray-500">
          {!selectedKeyword ? `Showing all products (${totalCount} total)` : 
           selectedKeyword ? `Results for "${selectedKeyword}" (${totalCount} total)` : ''}
        </span>
      </div>

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
                filename={`market-research-${selectedKeyword || 'all'}-${new Date().toISOString().slice(0, 10)}.csv`}
                className="btn-outline flex items-center py-1.5"
              >
                <Download size={16} className="mr-1" />
                Export CSV
              </CSVLink>
              
              {selectedKeyword && (
                <button
                  onClick={handleDeleteKeywordResults}
                  className="btn-outline border-red-500 text-red-500 hover:bg-red-500 hover:text-white py-1.5 flex items-center"
                >
                  <Trash2 size={16} className="mr-1" />
                  Delete All
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Results table */}
      {filteredResults.length > 0 ? (
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
                  onClick={() => handleSort('estimated_monthly_website_visits')}
                >
                  <div className="flex items-center">
                    Traffic
                    {sortBy === 'estimated_monthly_website_visits' && (
                      <ArrowUpDown size={14} className={`ml-1 ${sortDesc ? 'transform rotate-180' : ''}`} />
                    )}
                  </div>
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Trends
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
                      {formatNumber(item.monthly_visits || item.traffic_data?.monthly_visits)}
                      {(item.monthly_visits || item.traffic_data?.monthly_visits) && (
                        <span className="text-xs text-gray-500 ml-1">visits/mo</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    {item.traffic_sparkline ? (
                      <div className="h-10 w-24">
                        <Sparklines data={item.traffic_sparkline.values} height={30}>
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
                  <td className="px-4 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <a 
                        href={item.product_page_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-900 inline-flex items-center"
                      >
                        <ExternalLink size={16} />
                      </a>
                      <button
                        onClick={() => handleDeleteProduct(item.id)}
                        className="text-red-500 hover:text-red-700"
                        title="Delete product"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : results.length > 0 ? (
        <p className="text-center py-8 text-gray-500">
          No matching results. Try changing your search.
        </p>
      ) : (
        <div className="text-center py-8">
          <AlertCircle size={48} className="mx-auto mb-3 opacity-50 text-amber-500" />
          <p className="text-base text-gray-600">
            {selectedKeyword 
              ? `No results found for keyword "${selectedKeyword}".`
              : 'No products found.'
            }
          </p>
          <p className="text-sm mt-2 text-gray-500">
            Run the pipeline to discover products.
          </p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
} 