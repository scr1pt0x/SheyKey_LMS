"use client";

import { useEffect, useRef } from "react";
import api from "@/lib/axios";

const HEARTBEAT_INTERVAL_MS = 3 * 60 * 1000;

async function pingPresence() {
  try {
    await api.post("/api/sb/presence");
  } catch {
    // ignore background heartbeat errors
  }
}

export function SbPresenceHeartbeat() {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    void pingPresence();

    const startInterval = () => {
      if (intervalRef.current) return;
      intervalRef.current = setInterval(() => {
        if (document.visibilityState === "visible") {
          void pingPresence();
        }
      }, HEARTBEAT_INTERVAL_MS);
    };

    const stopInterval = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void pingPresence();
        startInterval();
      } else {
        stopInterval();
      }
    };

    startInterval();
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      stopInterval();
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, []);

  return null;
}
