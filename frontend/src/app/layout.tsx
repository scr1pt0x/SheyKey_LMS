"use client";

import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/features/shared/Providers";
import { Toaster } from "@/components/ui/toaster";
import { useEffect } from "react";
import { registerPushSubscription } from "@/hooks/useNotifications";

const inter = Inter({ subsets: ["cyrillic", "latin"] });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Register Web Push subscription after page loads.
    // registerPushSubscription is a no-op if service workers / push not supported.
    registerPushSubscription();
  }, []);

  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        <title>Islamic Finance LMS</title>
        <meta name="description" content="Система управления исламскими финансовыми сделками" />
        <meta name="theme-color" content="#1a3a5c" />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icons/icon-192x192.png" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="LMS" />
      </head>
      <body className={inter.className}>
        <Providers>{children}</Providers>
        <Toaster />
      </body>
    </html>
  );
}
