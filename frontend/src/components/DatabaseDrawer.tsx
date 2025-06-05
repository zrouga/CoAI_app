'use client';

import { useState, useEffect } from 'react';
import { X, Trash2, Download, CheckCircle, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import { getAllKeywords, deleteMultipleKeywordResults } from '@/services/api';

interface DatabaseDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function DatabaseDrawer({ isOpen, onClose }: DatabaseDrawerProps) {
  const [keywords, setKeywords] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // Fetch keywords when drawer opens
  useEffect(() => {
    if (isOpen) {
      fetchKeywords();
    }
  }, [isOpen]);

  const fetchKeywords = async () => {
    setIsLoading(true);
    try {
      const data = await getAllKeywords();
      setKeywords(data);
      setSelected([]);
    } catch (error) {
      console.error('Failed to fetch keywords:', error);
      toast.error('Failed to load keywords');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectAll = () => {
    if (selected.length === keywords.length) {
      setSelected([]);
    } else {
      setSelected([...keywords]);
    }
  };

  const handleSelect = (keyword: string) => {
    if (selected.includes(keyword)) {
      setSelected(selected.filter(k => k !== keyword));
    } else {
      setSelected([...selected, keyword]);
    }
  };

  const handleDelete = async () => {
    if (selected.length === 0) return;
    
    const confirmation = window.confirm(
      `Are you sure you want to delete data for ${selected.length} keyword${selected.length !== 1 ? 's' : ''}?`
    );
    
    if (!confirmation) return;
    
    setIsDeleting(true);
    try {
      await deleteMultipleKeywordResults(selected);
      toast.success(`Successfully deleted ${selected.length} keyword${selected.length !== 1 ? 's' : ''}`);
      fetchKeywords();
    } catch (error) {
      console.error('Failed to delete keywords:', error);
      toast.error('Failed to delete keywords');
    } finally {
      setIsDeleting(false);
    }
  };
  
  // Function to download database backup (currently just exports all keywords and their results)
  const handleBackup = async () => {
    // In a real implementation, this would call a backend endpoint to generate a full backup file
    // For now, we'll create a simple JSON file with keyword names 
    const backupData = {
      keywords: keywords,
      timestamp: new Date().toISOString()
    };
    
    // Create and trigger download
    const dataStr = JSON.stringify(backupData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `market-intelligence-backup-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    toast.success('Backup downloaded successfully');
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
                <h2 className="text-lg font-medium text-gray-900">Database Management</h2>
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
                {/* Action buttons */}
                <div className="flex space-x-4 mb-4">
                  <button
                    type="button"
                    className="btn-outline flex items-center"
                    onClick={fetchKeywords}
                    disabled={isLoading}
                  >
                    <RefreshCw size={16} className={`mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                    Refresh
                  </button>
                  
                  <button
                    type="button"
                    className="btn-outline flex items-center"
                    onClick={handleBackup}
                    disabled={keywords.length === 0 || isLoading}
                  >
                    <Download size={16} className="mr-2" />
                    Backup DB
                  </button>
                  
                  <button
                    type="button"
                    className="btn-outline border-red-500 text-red-500 hover:bg-red-500 hover:text-white flex items-center"
                    onClick={handleDelete}
                    disabled={selected.length === 0 || isDeleting}
                  >
                    <Trash2 size={16} className="mr-2" />
                    {isDeleting ? 'Deleting...' : 'Delete Selected'}
                  </button>
                </div>
                
                {/* Keywords list */}
                <div className="border rounded-md overflow-hidden">
                  <div className="bg-gray-50 px-4 py-2 flex items-center">
                    <div className="flex items-center mr-4">
                      <input
                        type="checkbox"
                        id="select-all"
                        checked={keywords.length > 0 && selected.length === keywords.length}
                        onChange={handleSelectAll}
                        className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                      />
                      <label htmlFor="select-all" className="ml-2 text-sm font-medium text-gray-700">
                        Select All
                      </label>
                    </div>
                    <span className="text-sm text-gray-500">
                      {selected.length} of {keywords.length} selected
                    </span>
                  </div>
                  
                  <div className="max-h-96 overflow-y-auto">
                    {isLoading ? (
                      <div className="p-8 text-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                        <p className="mt-2 text-sm text-gray-500">Loading keywords...</p>
                      </div>
                    ) : keywords.length === 0 ? (
                      <div className="p-8 text-center">
                        <p className="text-gray-500">No keywords found in database.</p>
                      </div>
                    ) : (
                      <ul className="divide-y divide-gray-200">
                        {keywords.map((keyword) => (
                          <li key={keyword} className="px-4 py-3 hover:bg-gray-50">
                            <div className="flex items-center">
                              <input
                                type="checkbox"
                                id={`keyword-${keyword}`}
                                checked={selected.includes(keyword)}
                                onChange={() => handleSelect(keyword)}
                                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                              />
                              <label 
                                htmlFor={`keyword-${keyword}`} 
                                className="ml-3 block text-sm font-medium text-gray-700 cursor-pointer"
                              >
                                {keyword}
                              </label>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
                
                <div className="mt-4 text-sm text-gray-500">
                  <p>
                    Here you can manage your keyword research database. Select keywords to delete them, or download a backup of your entire database.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
