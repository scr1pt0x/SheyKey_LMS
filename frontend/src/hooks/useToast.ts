import { useState, useCallback } from "react";

interface Toast {
  id: string;
  title: string;
  description?: string;
  variant?: "default" | "destructive";
}

let globalToasts: Toast[] = [];
let listeners: Array<(toasts: Toast[]) => void> = [];

function notify() {
  listeners.forEach((l) => l([...globalToasts]));
}

export function toast(props: Omit<Toast, "id">) {
  const id = Math.random().toString(36).slice(2);
  globalToasts = [...globalToasts, { ...props, id }];
  notify();
  setTimeout(() => {
    globalToasts = globalToasts.filter((t) => t.id !== id);
    notify();
  }, 4000);
}

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>(globalToasts);

  const subscribe = useCallback(() => {
    listeners.push(setToasts);
    return () => {
      listeners = listeners.filter((l) => l !== setToasts);
    };
  }, []);

  // Subscribe on mount
  useState(() => {
    const unsub = subscribe();
    return unsub;
  });

  const dismiss = useCallback((id: string) => {
    globalToasts = globalToasts.filter((t) => t.id !== id);
    notify();
  }, []);

  return { toasts, dismiss, toast };
}
