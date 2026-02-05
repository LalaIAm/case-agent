/**
 * Chat input: textarea with send button, Enter to send, Shift+Enter newline.
 */
import { useRef, useEffect } from 'react';

const MAX_LINES = 5;
const MAX_CHARS = 2000;

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled: boolean;
  placeholder?: string;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  disabled,
  placeholder = 'Type your question…',
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    const lineHeight = 24;
    const lines = Math.min(MAX_LINES, (ta.value.match(/\n/g)?.length ?? 0) + 1);
    ta.style.height = `${lines * lineHeight}px`;
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim()) onSend();
    }
  };

  const canSend = value.trim().length > 0 && !disabled;

  return (
    <div className="flex flex-col gap-1 rounded-lg border border-gray-200 bg-white p-2">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => {
          const v = e.target.value;
          if (v.length <= MAX_CHARS) onChange(v);
        }}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="min-h-[24px] max-h-[120px] w-full resize-none rounded border-0 bg-transparent px-2 py-1 text-sm focus:outline-none focus:ring-0 disabled:opacity-60"
        aria-label="Message"
      />
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400">
          {value.length}/{MAX_CHARS}
        </span>
        <button
          type="button"
          onClick={() => canSend && onSend()}
          disabled={!canSend}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </div>
    </div>
  );
}
