import { useState, useCallback, useRef } from 'react';
import type { ChatMessage, AgentType } from '../types';
import { useSSE } from './useSSE';
import api from '../api/client';

export interface UseChatReturn {
  messages: ChatMessage[];
  sendMessage: (text: string) => Promise<void>;
  isTyping: boolean;
  error: string | null;
  conversationId: string | null;
  setConversationId: (id: string | null) => void;
  loadHistory: (convId: string) => Promise<void>;
  createConversation: (agentType: AgentType) => Promise<string>;
}

export function useChat(agentType: AgentType): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const { sendSSE, isStreaming, error: sseError } = useSSE();
  
  // Use ref to keep track of the accumulated assistant message
  const assistantMsgRef = useRef<string>('');

  const loadHistory = useCallback(async (convId: string) => {
    try {
      const response = await api.get(`/chat/conversations/${convId}/history`);
      if (Array.isArray(response.data)) {
        setMessages(response.data);
      }
      setConversationId(convId);
    } catch (err) {
      console.error('Failed to load history', err);
    }
  }, []);

  const createConversation = useCallback(async (type: AgentType) => {
    try {
      const response = await api.post('/chat/conversations', { agent_type: type });
      return response.data.id;
    } catch (err) {
      console.error('Failed to create conversation', err);
      throw err;
    }
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      // 1. Optimistic user message update
      const userMessage: ChatMessage = {
        id: `local-user-${Date.now()}`,
        conversation_id: conversationId || '',
        role: 'user',
        content: text,
        metadata_json: null,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);

      // 2. Prepare conversation ID
      let currentConvId = conversationId;
      if (!currentConvId) {
        try {
          currentConvId = await createConversation(agentType);
          setConversationId(currentConvId);
        } catch (err) {
          console.error(err);
          return;
        }
      }

      // Add optimistic assistant placeholder
      const tempAssistantId = `local-assistant-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        {
          id: tempAssistantId,
          conversation_id: currentConvId as string,
          role: 'assistant',
          content: '',
          metadata_json: null,
          created_at: new Date().toISOString(),
        },
      ]);

      assistantMsgRef.current = '';

      // 3. Send SSE POST request
      await sendSSE(`/api/chat/${agentType}/stream`, {
        message: text,
        conversation_id: currentConvId,
      }, {
        onMessage: (content) => {
          assistantMsgRef.current += content;
          setMessages((prev) => 
            prev.map((msg) =>
              msg.id === tempAssistantId
                ? { ...msg, content: assistantMsgRef.current }
                : msg
            )
          );
        },
        onThinking: (_content) => {
          // If we want to show thinking, we can store it in metadata
          // For now, we ignore or append slightly differently
        },
        onDone: (returnedConvId) => {
          if (returnedConvId && returnedConvId !== currentConvId) {
             setConversationId(returnedConvId);
          }
          // Note: you could trigger a refresh here to get the real DB IDs
        },
        onError: (err) => {
          console.error('SSE Error:', err);
        }
      });
    },
    [agentType, conversationId, createConversation, sendSSE]
  );

  return {
    messages,
    sendMessage,
    isTyping: isStreaming,
    error: sseError,
    conversationId,
    setConversationId,
    loadHistory,
    createConversation,
  };
}
