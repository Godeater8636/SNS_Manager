"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Send, Link2, Bot, BarChart2, Settings, LogOut, Twitter } from "lucide-react";
import { clsx } from "clsx";
import { useAuthStore } from "@/lib/auth";

const navItems = [
  { href: "/dashboard", label: "ダッシュボード", icon: LayoutDashboard },
  { href: "/posts", label: "投稿管理", icon: Send },
  { href: "/links", label: "アフィリエイトリンク", icon: Link2 },
  { href: "/accounts", label: "Xアカウント", icon: Twitter },
  { href: "/tasks", label: "自動タスク", icon: Bot },
  { href: "/settings", label: "設定・プラン", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  return (
    <aside className="w-60 min-h-screen bg-white border-r border-gray-200 flex flex-col">
      <div className="px-6 py-5 border-b border-gray-100">
        <h1 className="text-lg font-bold text-blue-700">SNS Manager</h1>
        <p className="text-xs text-gray-400 mt-0.5 truncate">{user?.email}</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
              pathname.startsWith(href)
                ? "bg-blue-50 text-blue-700"
                : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
            )}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
      </nav>

      <div className="px-3 py-4 border-t border-gray-100">
        <div className="px-3 mb-2">
          <span className="badge badge-blue">{user?.plan?.display_name || "Starter"}</span>
          {user?.plan?.expires_at && (
            <p className="text-xs text-gray-400 mt-1">
              有効期限: {new Date(user.plan.expires_at).toLocaleDateString("ja-JP")}
            </p>
          )}
        </div>
        <button
          onClick={() => logout()}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
        >
          <LogOut size={18} />
          ログアウト
        </button>
      </div>
    </aside>
  );
}
