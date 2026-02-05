/**
 * Types for the case advisor conversation.
 */

export interface ConversationMessage {
  id: string;
  case_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  metadata_?: Record<string, unknown>;
}

export interface ConversationRequest {
  message: string;
  include_context?: boolean;
}

export interface ConversationHistoryResponse {
  messages: ConversationMessage[];
}
