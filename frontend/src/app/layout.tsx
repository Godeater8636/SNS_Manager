import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/ui/QueryProvider";

export const metadata: Metadata = {
  title: "SNS Manager — X アフィリエイト管理ツール",
  description: "予約投稿・アフィリエイトリンク管理・自動化を一元化",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body className="bg-gray-50 text-gray-900 antialiased">
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
