import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";

export interface StaffNotification {
  id: string;
  title: string;
  body: string;
  is_read: boolean;
  entity_type: string | null;
  entity_id: string | null;
  action_url: string | null;
  created_at: string;
}

/** Poll unread count every 30 seconds. Used for the bell badge. */
export function useUnreadCount() {
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: async () => {
      const { data } = await api.get("/api/notifications/inbox/unread-count");
      return data as { count: number };
    },
    refetchInterval: 30_000,
    staleTime: 29_000,
  });
}

/** Fetch inbox (first 30, unread first). Refetches when count changes. */
export function useNotificationInbox() {
  return useQuery({
    queryKey: ["notifications", "inbox"],
    queryFn: async () => {
      const { data } = await api.get("/api/notifications/inbox", {
        params: { limit: 30, offset: 0 },
      });
      return data as { items: StaffNotification[]; total: number };
    },
    staleTime: 15_000,
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/api/notifications/inbox/${id}/read`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.post("/api/notifications/inbox/read-all");
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

/** Register this browser for Web Push. Call once after login. */
export async function registerPushSubscription(): Promise<void> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;

  try {
    const { data } = await api.get("/api/notifications/vapid-public-key");
    const vapidPublicKey: string = data.publicKey;
    if (!vapidPublicKey) return;

    const registration = await navigator.serviceWorker.ready;
    const existing = await registration.pushManager.getSubscription();
    if (existing) return; // already subscribed

    const permission = await Notification.requestPermission();
    if (permission !== "granted") return;

    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
    });

    const subJson = subscription.toJSON();
    await api.post("/api/notifications/push-subscribe", {
      endpoint: subJson.endpoint,
      keys: subJson.keys,
    });
  } catch {
    // Non-critical — silently skip
  }
}

function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const buffer = new ArrayBuffer(rawData.length);
  const outputArray = new Uint8Array(buffer);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}
