import { useState, useRef, useCallback } from 'react';

export interface UseSSEOptions {
  onMessage?: (content: string) => void;
  onDone?: (conversationId: string | null) => void;
  onError?: (error: string) => void;
  onThinking?: (content: string) => void;
}

export function useSSE() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const abort = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  const sendSSE = useCallback(
    async (url: string, body: object, options: UseSSEOptions) => {
      // Cancel any ongoing stream
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;
      setIsStreaming(true);
      setError(null);

      try {
        const token = localStorage.getItem('token');
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        };
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(url, {
          method: 'POST',
          headers,
          body: JSON.stringify(body),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        if (!response.body) {
          throw new Error('ReadableStream not supported.');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          if (value) {
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            // Keep the last partial line in the buffer
            buffer = lines.pop() || '';

            for (let i = 0; i < lines.length; i++) {
              const line = lines[i].trim();
              if (!line) continue;

              if (line.startsWith('data:')) {
                const dataStr = line.slice(5).trim();
                
                // Keep reading if empty data
                if (!dataStr) continue;

                try {
                  const data = JSON.parse(dataStr);
                  switch (data.type) {
                    case 'message':
                      if (options.onMessage) options.onMessage(data.content || '');
                      break;
                    case 'thinking':
                      if (options.onThinking) options.onThinking(data.content || '');
                      break;
                    case 'done':
                      if (options.onDone) options.onDone(data.conversation_id || null);
                      break;
                    case 'error':
                      if (options.onError) options.onError(data.content || 'Unknown error');
                      setError(data.content || 'Unknown error');
                      break;
                  }
                } catch (e) {
                  console.error('Failed to parse SSE line:', dataStr, e);
                }
              }
            }
          }
        }
      } catch (err: any) {
        if (err.name === 'AbortError') {
          console.log('Stream aborted');
        } else {
          setError(err.message || 'Stream connection failed');
          if (options.onError) options.onError(err.message || 'Stream connection failed');
        }
      } finally {
        if (abortControllerRef.current === controller) {
          setIsStreaming(false);
          abortControllerRef.current = null;
        }
      }
    },
    []
  );

  return { sendSSE, isStreaming, error, abort };
}
