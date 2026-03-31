"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar,
} from "recharts";
import { api } from "@/lib/api";
import { DashboardData } from "@/types";
import { TrendingUp, MousePointerClick, Heart, Repeat2, Eye } from "lucide-react";

const PERIOD_OPTIONS = [
  { value: "7d", label: "7日間" },
  { value: "30d", label: "30日間" },
  { value: "90d", label: "90日間" },
];

function StatCard({ label, value, icon: Icon, color }: { label: string; value: string | number; icon: React.ElementType; color: string }) {
  return (
    <div className="card flex items-center gap-4">
      <div className={`p-3 rounded-xl ${color}`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold">{typeof value === "number" ? value.toLocaleString() : value}</p>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [period, setPeriod] = useState("30d");

  const { data, isLoading } = useQuery({
    queryKey: ["dashboard", period],
    queryFn: () => api.getDashboard({ period }).then((r) => r.data.data as DashboardData),
  });

  if (isLoading) return <div className="p-8 text-gray-400">読み込み中...</div>;

  const summary = data?.summary;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2>ダッシュボード</h2>
        <div className="flex gap-2">
          {PERIOD_OPTIONS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                period === p.value
                  ? "bg-blue-600 text-white"
                  : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="インプレッション" value={summary?.total_impressions ?? 0} icon={Eye} color="bg-blue-500" />
        <StatCard label="いいね" value={summary?.total_likes ?? 0} icon={Heart} color="bg-pink-500" />
        <StatCard label="リツイート" value={summary?.total_retweets ?? 0} icon={Repeat2} color="bg-green-500" />
        <StatCard label="リンククリック" value={summary?.total_link_clicks ?? 0} icon={MousePointerClick} color="bg-purple-500" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-base font-semibold mb-4">インプレッション推移</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data?.daily_series || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="impressions" stroke="#3b82f6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3 className="text-base font-semibold mb-4">アフィリエイトクリック推移</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data?.daily_series || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="link_clicks" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Posts & Links */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-base font-semibold mb-4">人気投稿 Top 5</h3>
          {data?.top_posts.length === 0 && <p className="text-gray-400 text-sm">投稿データがありません</p>}
          <ul className="space-y-2">
            {data?.top_posts.map((p) => (
              <li key={p.post_id} className="flex items-start justify-between gap-2">
                <p className="text-sm text-gray-700 truncate flex-1">{p.content}</p>
                <span className="text-xs text-gray-400 whitespace-nowrap">
                  {p.impressions.toLocaleString()} imp / {p.engagement_rate}% ER
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div className="card">
          <h3 className="text-base font-semibold mb-4">クリック数 Top リンク</h3>
          {data?.top_links.length === 0 && <p className="text-gray-400 text-sm">リンクデータがありません</p>}
          <ul className="space-y-2">
            {data?.top_links.map((l) => (
              <li key={l.link_id} className="flex items-center justify-between">
                <span className="text-sm text-gray-700 truncate">{l.name}</span>
                <span className="badge badge-blue">{l.clicks.toLocaleString()} clicks</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
