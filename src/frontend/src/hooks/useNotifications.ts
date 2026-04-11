import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

export interface NotificationCount {
  approvals: number;
  kb_reviews: number;
  agent_failures: number;
  buyer_messages: number;
}

export interface Notification {
  id: string;
  type: 'approval' | 'kb_review' | 'agent_failure';
  title: string;
  message: string;
  created_at: string;
  is_read: boolean;
  link?: string;
}

export function useNotifications() {
  const [totalCount, setTotalCount] = useState<number>(0);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchCount = useCallback(async () => {
    try {
      const { data } = await api.get<NotificationCount>('/notifications/count');
      setTotalCount(
        (data.approvals || 0) + 
        (data.kb_reviews || 0) + 
        (data.agent_failures || 0)
      );
    } catch {
      // Ignore errors silently as requested
    }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<{items?: Notification[], data?: Notification[]}>('/notifications/list?page=1&page_size=10');
      if (Array.isArray(data)) {
        setNotifications(data);
      } else if (data && Array.isArray(data.items)) {
        setNotifications(data.items);
      } else if (data && Array.isArray(data.data)) {
        setNotifications(data.data);
      } else {
        setNotifications([]);
      }
    } catch {
      // Ignore errors silently as requested
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCount();
    const interval = setInterval(fetchCount, 30000);
    return () => clearInterval(interval);
  }, [fetchCount]);

  return { totalCount, notifications, loading, refresh };
}
