/**
 * Server-Sent Events (SSE) client for real-time pipeline progress
 */

export interface SSEEvent {
  type: string;
  data: {
    type: string;
    data: any;
    timestamp: string;
  };
}

export interface PipelineProgress {
  step: number;
  progress: number;
  total: number;
  percentage: number;
  currentItem?: string;
  message: string;
}

export class SSEClient {
  private eventSource: EventSource | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  
  constructor(
    private keyword: string,
    private apiUrl: string,
    private handlers: {
      onConnect?: () => void;
      onDisconnect?: () => void;
      onPipelineStart?: (data: any) => void;
      onStepStart?: (step: number, data: any) => void;
      onStepProgress?: (step: number, progress: PipelineProgress) => void;
      onStepComplete?: (step: number, data: any) => void;
      onPipelineComplete?: (data: any) => void;
      onPipelineError?: (error: any) => void;
      onLog?: (log: any) => void;
      onError?: (error: Error) => void;
    }
  ) {}
  
  connect(): void {
    if (this.eventSource) {
      this.disconnect();
    }
    
    const url = `${this.apiUrl}/pipeline/stream/${encodeURIComponent(this.keyword)}`;
    
    try {
      this.eventSource = new EventSource(url);
      
      this.eventSource.onopen = () => {
        console.log(`SSE connected for keyword: ${this.keyword}`);
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.handlers.onConnect?.();
      };
      
      this.eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        this.handlers.onError?.(new Error('SSE connection error'));
        
        // Attempt reconnection with exponential backoff
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          setTimeout(() => {
            console.log(`Attempting SSE reconnection (${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);
            this.reconnectAttempts++;
            this.reconnectDelay *= 2; // Exponential backoff
            this.connect();
          }, this.reconnectDelay);
        } else {
          this.handlers.onDisconnect?.();
        }
      };
      
      // Handle specific event types
      this.eventSource.addEventListener('connected', (event) => {
        console.log('SSE connected event:', event.data);
      });
      
      this.eventSource.addEventListener('pipeline_start', (event) => {
        const data = JSON.parse(event.data);
        this.handlers.onPipelineStart?.(data.data);
      });
      
      this.eventSource.addEventListener('step1_start', (event) => {
        const data = JSON.parse(event.data);
        this.handlers.onStepStart?.(1, data.data);
      });
      
      this.eventSource.addEventListener('step1_progress', (event) => {
        const data = JSON.parse(event.data);
        this.handlers.onStepProgress?.(1, data.data as PipelineProgress);
      });
      
      this.eventSource.addEventListener('step1_complete', (event) => {
        const data = JSON.parse(event.data);
        this.handlers.onStepComplete?.(1, data.data);
      });
      
      this.eventSource.addEventListener('step2_start', (event) => {
        const data = JSON.parse(event.data);
        this.handlers.onStepStart?.(2, data.data);
      });
      
      this.eventSource.addEventListener('step2_progress', (event) => {
        const data = JSON.parse(event.data);
        this.handlers.onStepProgress?.(2, data.data as PipelineProgress);
      });
      
      this.eventSource.addEventListener('step2_complete', (event) => {
        const data = JSON.parse(event.data);
        this.handlers.onStepComplete?.(2, data.data);
      });
      
      this.eventSource.addEventListener('pipeline_complete', (event) => {
        const data = JSON.parse(event.data);
        this.handlers.onPipelineComplete?.(data.data);
        this.disconnect();
      });
      
      this.eventSource.addEventListener('pipeline_error', (event) => {
        const data = JSON.parse(event.data);
        this.handlers.onPipelineError?.(data.data);
        this.disconnect();
      });
      
      this.eventSource.addEventListener('log', (event) => {
        const data = JSON.parse(event.data);
        this.handlers.onLog?.(data.data);
      });
      
      this.eventSource.addEventListener('ping', () => {
        // Keep-alive ping, no action needed
      });
      
    } catch (error) {
      console.error('Failed to create EventSource:', error);
      this.handlers.onError?.(error as Error);
    }
  }
  
  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.handlers.onDisconnect?.();
      console.log(`SSE disconnected for keyword: ${this.keyword}`);
    }
  }
  
  isConnected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN;
  }
} 