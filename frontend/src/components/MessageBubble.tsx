/**
 * Single message bubble with role-based styling and optional markdown.
 */
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ConversationMessage } from '../types/conversation';
import { ContextIndicator } from './ContextIndicator';

interface MessageBubbleProps {
  message: ConversationMessage;
  isStreaming?: boolean;
  contextUsed?: string[];
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
  return d.toLocaleDateString(undefined, { dateStyle: 'short', timeStyle: 'short' });
}

export function MessageBubble({ message, isStreaming, contextUsed }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
  };

  return (
    <div
      className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}
      data-role={message.role}
    >
      <div
        className={`max-w-[85%] rounded-lg px-4 py-2 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-900 border border-gray-200'
        }`}
      >
        <div className="break-words text-sm">
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
        <div className="mt-1 flex items-center justify-between gap-2">
          <span className="text-xs opacity-70">{formatTime(message.created_at)}</span>
          {!isUser && (
            <button
              type="button"
              onClick={handleCopy}
              className="text-xs opacity-70 hover:opacity-100"
              aria-label="Copy to clipboard"
            >
              Copy
            </button>
          )}
        </div>
        {!isUser && (() => {
          const used = (contextUsed ?? (message.metadata_?.context_used as string[] | undefined) ?? []);
          return used.length > 0 ? <ContextIndicator contextUsed={used} /> : null;
        })()}
        {isStreaming && (
          <span
            className="inline-block h-2 w-2 animate-pulse rounded-full bg-gray-500 mt-1"
            aria-hidden
          />
        )}
      </div>
    </div>
  );
}
