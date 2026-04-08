export type TabType = 
  | 'dashboard' 
  | 'message-center' 
  | 'ai-supervisor' 
  | 'more-functions' 
  | 'agent-detail'
  | 'ad-dashboard' 
  | 'ad-management' 
  | 'all-orders' 
  | 'refund-orders' 
  | 'system-management';

export interface Message {
  role: 'user' | 'model';
  text: string;
  timestamp: Date;
  file?: {
    name: string;
    url: string;
    type: string;
  };
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  icon: any;
  color: string;
  tags: string[];
}
