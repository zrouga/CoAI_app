'use client';

import { useState } from 'react';
import { Search } from 'lucide-react';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { runKeywordPipeline } from '@/services/api';
import { DEFAULT_RUN_CONFIG } from '@/types/api';

interface KeywordFormProps {
  onSubmit: (keyword: string) => void;
}

interface FormData {
  keyword: string;
}

export function KeywordForm({ onSubmit }: KeywordFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { register, handleSubmit, formState: { errors }, reset } = useForm<FormData>({
    defaultValues: {
      keyword: '',
    }
  });

  const processSubmit = async (data: FormData) => {
    if (!data.keyword.trim()) return;
    
    setIsSubmitting(true);
    try {
      // Run pipeline with default config + keyword
      await runKeywordPipeline({ 
        keyword: data.keyword.trim(),
        ...DEFAULT_RUN_CONFIG
      });
      
      // Pass keyword up to parent for tracking
      onSubmit(data.keyword.trim());
      reset();
    } catch (error) {
      console.error('Failed to run pipeline:', error);
      toast.error('Failed to start analysis. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(processSubmit)} className="space-y-4">
      <div>
        <label htmlFor="keyword" className="label">
          Enter a product keyword to research:
        </label>
        
        <div className="relative">
          <input
            id="keyword"
            type="text"
            placeholder="e.g., yoga mat, coffee maker..."
            className={`input w-full pl-10 ${errors.keyword ? 'border-red-500' : ''}`}
            disabled={isSubmitting}
            {...register('keyword', { 
              required: 'Keyword is required',
              minLength: { value: 2, message: 'Keyword must be at least 2 characters' }
            })}
          />
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
        </div>
        
        {errors.keyword && (
          <p className="mt-1 text-sm text-red-500">{errors.keyword.message}</p>
        )}
      </div>

      <button 
        type="submit" 
        className="btn-primary w-full flex items-center justify-center"
        disabled={isSubmitting}
      >
        {isSubmitting ? (
          <>
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Running...
          </>
        ) : (
          <>
            <Search className="mr-2" size={18} />
            Analyze Market
          </>
        )}
      </button>
    </form>
  );
}
