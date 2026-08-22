import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Providers } from "@/components/providers";
import AuthGuard from "@/components/auth-guard";
import { BRAND } from "@/lib/brand";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: `${BRAND.displayName} — Centro de Comando`,
  description: BRAND.description,
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: BRAND.displayName,
  },
};

export const viewport: Viewport = {
  themeColor: "#00d4ff",
  colorScheme: "dark",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" className="dark">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <link rel="icon" href="/icons/icon-192.svg" type="image/svg+xml" />
        <meta name="theme-color" content="#00d4ff" media="(prefers-color-scheme: dark)" />
        <meta name="theme-color" content="#00d4ff" media="(prefers-color-scheme: light)" />
        <link rel="apple-touch-icon" href="/icons/icon-192.svg" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content={BRAND.displayName} />
      </head>
      <body className={`${inter.variable} ${jetbrains.variable} font-sans`}>
        <Providers>
          <AuthGuard>{children}</AuthGuard>
        </Providers>
      </body>
    </html>
  );
}
