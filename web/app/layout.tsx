import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import Link from "next/link";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "TesterAgent 控制台",
  description: "基于 PhoneAgent 的真机自动化测试平台",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen bg-background`}
      >
        {/* Global Navigation Bar */}
        <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
          <div className="container mx-auto px-4 py-3 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-bold text-lg">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo.png" alt="Logo" className="w-8 h-8 rounded-md shadow-sm" />
              <span>TesterAgent</span>
            </Link>
            <div className="flex items-center gap-4">
              <Link href="/devices" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                设备
              </Link>
              <Link href="/runs" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                任务
              </Link>
              <Link href="/history" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                历史
              </Link>
              <Link href="/settings" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                设置
              </Link>
              <Link href="/runs/new">
                <button className="bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-medium hover:bg-primary/90 transition-colors">
                  新建任务
                </button>
              </Link>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="flex-1">
          {children}
        </main>

        {/* Toast Provider */}
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
