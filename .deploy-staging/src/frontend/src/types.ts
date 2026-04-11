export type UserRole = 'boss' | 'operator'

export interface User {
  username: string
  role: UserRole
}

export type AgentType =
  | 'core_management'
  | 'brand_planning'
  | 'selection'
  | 'competitor'
  | 'whitepaper'
  | 'listing'
  | 'image_generation'
  | 'product_listing'
  | 'inventory'
  | 'ad_monitor'
  | 'persona'
  | 'keyword_library'
  | 'auditor'

export interface Conversation {
  id: string
  user_id: string
  agent_type: AgentType
  title: string | null
  created_at: string
  updated_at: string | null
  metadata_json: Record<string, unknown> | null
}

export interface ChatMessage {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  metadata_json: Record<string, unknown> | null
  created_at: string
}

export interface AgentRun {
  id: string
  agent_type: AgentType
  status: 'pending' | 'running' | 'success' | 'error'
  params: Record<string, unknown>
  result_json: Record<string, unknown> | null
  output_summary: string | null
  error_message: string | null
  started_at: string | null
  finished_at: string | null
  conversation_id: string | null
  is_chat_mode: boolean
}

export interface ApprovalRequest {
  id: string
  agent_type: AgentType
  action: string
  payload: Record<string, unknown>
  status: 'pending' | 'approved' | 'rejected'
  reviewer_comment: string | null
  created_at: string
  reviewed_at: string | null
}

export interface KBReviewItem {
  id: string
  content: string
  source: string | null
  agent_type: string | null
  summary: string | null
  status: 'pending' | 'approved' | 'rejected'
  reviewer_id: string | null
  review_comment: string | null
  created_at: string
  reviewed_at: string | null
}