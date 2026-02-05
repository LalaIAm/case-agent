/**
 * Case Advisor tab: conversation history, streaming responses, suggested questions,
 * clear history, and re-analyze actions.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  clearHistory,
  getConversationHistory,
  getSuggestedQuestions,
  sendMessage,
  triggerReanalysis,
} from '../services/conversation';
import type { ConversationMessage } from '../types/conversation';
import { Button } from './Button';
import { Card } from './Card';
import { ChatInput } from './ChatInput';
import { LoadingSpinner } from './LoadingSpinner';
import { MessageBubble } from './MessageBubble';

interface AdvisorTabProps {
  caseId: string;
}

export function AdvisorTab({ caseId }: AdvisorTabProps) {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [streamingContextUsed, setStreamingContextUsed] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const loadHistory = useCallback(async () => {
    if (!caseId) return;
    setHistoryLoading(true);
    setError(null);
    try {
      const list = await getConversationHistory(caseId, 50);
      setMessages(list.reverse());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load history');
    } finally {
      setHistoryLoading(false);
    }
  }, [caseId]);

  const loadSuggestions = useCallback(async () => {
    if (!caseId) return;
    try {
      const list = await getSuggestedQuestions(caseId, 5);
      setSuggestedQuestions(list);
    } catch {
      setSuggestedQuestions([]);
    }
  }, [caseId]);

  useEffect(() => {
    loadHistory();
    loadSuggestions();
  }, [loadHistory, loadSuggestions]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = el;
      setShowScrollToBottom(scrollHeight - scrollTop - clientHeight > 100);
    };
    el.addEventListener('scroll', onScroll);
    return () => el.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  const handleSendMessage = useCallback(() => {
    const trimmed = inputMessage.trim();
    if (!trimmed || isStreaming) return;
    setInputMessage('');
    setError(null);
    setStreamingMessage('');
    setStreamingContextUsed([]);
    setIsStreaming(true);

    sendMessage(
      caseId,
      trimmed,
      {
        onChunk: (chunk) => setStreamingMessage((prev) => prev + chunk),
        onComplete: () => {
          setIsStreaming(false);
          setStreamingMessage('');
          loadHistory();
          loadSuggestions();
        },
        onError: (err) => {
          setError(err.message);
          setIsStreaming(false);
          setStreamingMessage('');
        },
      },
      { includeContext: true }
    );
  }, [caseId, inputMessage, isStreaming, loadHistory, loadSuggestions]);

  const handleReanalyze = useCallback(async () => {
    if (!window.confirm('Re-run the analysis workflow for this case?')) return;
    setError(null);
    try {
      await triggerReanalysis(caseId);
      setError(null);
      alert('Re-analysis started. Check the Agent Status tab for progress.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start re-analysis');
    }
  }, [caseId]);

  const handleClearHistory = useCallback(async () => {
    if (!window.confirm('Clear all conversation history for this case?')) return;
    setError(null);
    try {
      await clearHistory(caseId);
      setMessages([]);
      setStreamingMessage('');
      loadSuggestions();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to clear history');
    }
  }, [caseId, loadSuggestions]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <Card title="Case Advisor" className="flex flex-col">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={handleClearHistory} disabled={historyLoading}>
            Clear History
          </Button>
          <Button variant="secondary" onClick={handleReanalyze}>
            Re-analyze Case
          </Button>
        </div>

        {error && (
          <div className="flex items-center justify-between rounded bg-red-50 px-3 py-2 text-sm text-red-800">
            <span>{error}</span>
            <Button variant="secondary" onClick={() => setError(null)}>
              Dismiss
            </Button>
          </div>
        )}

        {historyLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="lg" />
          </div>
        ) : (
          <>
            <div
              ref={containerRef}
              className="flex max-h-[400px] min-h-[200px] flex-col gap-3 overflow-y-auto rounded border border-gray-200 bg-gray-50/50 p-3"
            >
              {messages.length === 0 && !streamingMessage && (
                <p className="text-center text-sm text-gray-500">
                  No messages yet. Ask a question or use a suggestion below.
                </p>
              )}
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {streamingMessage && (
                <div className="flex w-full justify-start">
                  <div className="max-w-[85%] rounded-lg border border-gray-200 bg-gray-100 px-4 py-2">
                    <div className="prose prose-sm max-w-none break-words dark:prose-invert">
                      {/* Rendered inline so we don't nest MessageBubble */}
                      <MessageBubble
                        message={{
                          id: 'streaming',
                          case_id: caseId,
                          role: 'assistant',
                          content: streamingMessage,
                          created_at: new Date().toISOString(),
                        }}
                        isStreaming
                        contextUsed={streamingContextUsed}
                      />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {showScrollToBottom && (
              <button
                type="button"
                onClick={scrollToBottom}
                className="self-center rounded bg-gray-200 px-2 py-1 text-xs text-gray-700 hover:bg-gray-300"
              >
                Scroll to bottom
              </button>
            )}

            {suggestedQuestions.length > 0 && (
              <div className="flex flex-wrap gap-2">
                <span className="text-xs text-gray-500">Suggestions:</span>
                {suggestedQuestions.map((q, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setInputMessage(q)}
                    className="rounded-full border border-gray-300 bg-white px-3 py-1 text-xs text-gray-700 hover:bg-gray-50"
                  >
                    {q.length > 60 ? q.slice(0, 57) + '…' : q}
                  </button>
                ))}
              </div>
            )}

            <ChatInput
              value={inputMessage}
              onChange={setInputMessage}
              onSend={handleSendMessage}
              disabled={isStreaming}
              placeholder="Ask about your case…"
            />
          </>
        )}
      </div>
    </Card>
  );
}
