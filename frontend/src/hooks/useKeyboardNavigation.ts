/**
 * Keyboard navigation for lists and menus: arrow keys, Enter, Escape.
 */
import { useCallback, useEffect } from 'react';

export interface UseKeyboardNavigationOptions {
  /** Total number of items */
  itemCount: number;
  /** Currently focused index (-1 for none) */
  focusedIndex: number;
  /** Callback when focus should move */
  onFocusChange: (index: number) => void;
  /** Whether the list is vertical (default true). If false, left/right move. */
  vertical?: boolean;
  /** Whether to wrap at ends */
  wrap?: boolean;
}

export function useKeyboardNavigation({
  itemCount,
  focusedIndex,
  onFocusChange,
  vertical = true,
  wrap = false,
}: UseKeyboardNavigationOptions): void {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (itemCount <= 0) return;
      const next = (current: number, delta: number): number => {
        let n = current + delta;
        if (wrap) {
          if (n < 0) n = itemCount - 1;
          else if (n >= itemCount) n = 0;
        } else {
          n = Math.max(0, Math.min(itemCount - 1, n));
        }
        return n;
      };

      if (vertical) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          onFocusChange(next(focusedIndex, 1));
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          onFocusChange(next(focusedIndex, -1));
        }
      } else {
        if (e.key === 'ArrowRight') {
          e.preventDefault();
          onFocusChange(next(focusedIndex, 1));
        } else if (e.key === 'ArrowLeft') {
          e.preventDefault();
          onFocusChange(next(focusedIndex, -1));
        }
      }
      if (e.key === 'Home') {
        e.preventDefault();
        onFocusChange(0);
      }
      if (e.key === 'End') {
        e.preventDefault();
        onFocusChange(itemCount - 1);
      }
    },
    [itemCount, focusedIndex, onFocusChange, vertical, wrap]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}
