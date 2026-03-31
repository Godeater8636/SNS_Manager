"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { Plus, Trash2, Edit2, Download } from "lucide-react";
import { api } from "@/lib/api";
import { Post, PostStatus } from "@/types";
import { PostCreateModal } from "@/components/posts/PostCreateModal";

const STATUS_LABELS: Record<PostStatus, string> = {
  draft: "下書き",
  scheduled: "予約済み",
  posting: "投稿中",
  posted: "投稿済み",
  failed: "失敗",
  cancelled: "キャンセル",
};

const STATUS_BADGE: Record<PostStatus, string> = {
  draft: "badge-gray",
  scheduled: "badge-blue",
  posting: "badge-yellow",
  posted: "badge-green",
  failed: "badge-red",
  cancelled: "badge-gray",
};

export default function PostsPage() {
  const qc = useQueryClient();
  const [status, setStatus] = useState<PostStatus | "">("");
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["posts", status],
    queryFn: () => api.listPosts({ status: status || undefined, per_page: 50 }).then((r) => r.data.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deletePost(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["posts"] }),
  });

  const downloadCsv = async () => {
    const res = await api.exportPostsCsv({ status: "posted" });
    const url = URL.createObjectURL(new Blob([res.data]));
    const a = document.createElement("a");
    a.href = url;
    a.download = "posts.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const posts: Post[] = data?.items || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2>投稿管理</h2>
        <div className="flex gap-2">
          <button onClick={downloadCsv} className="btn-secondary flex items-center gap-2">
            <Download size={16} />
            CSV エクスポート
          </button>
          <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
            <Plus size={16} />
            新規投稿
          </button>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {(["", "draft", "scheduled", "posted", "failed"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              status === s ? "bg-blue-600 text-white" : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            {s === "" ? "すべて" : STATUS_LABELS[s]}
          </button>
        ))}
      </div>

      {/* Posts table */}
      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">投稿内容</th>
              <th className="text-left text-xs font-medium text-gray-500 px-4 py-3 w-36">予約日時</th>
              <th className="text-left text-xs font-medium text-gray-500 px-4 py-3 w-24">ステータス</th>
              <th className="w-20 px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-gray-400">読み込み中...</td>
              </tr>
            )}
            {!isLoading && posts.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-gray-400">投稿がありません</td>
              </tr>
            )}
            {posts.map((post) => (
              <tr key={post.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3 text-sm text-gray-800 max-w-xs truncate">{post.content}</td>
                <td className="px-4 py-3 text-xs text-gray-500">
                  {post.scheduled_at
                    ? format(new Date(post.scheduled_at), "M/d HH:mm", { locale: ja })
                    : "—"}
                </td>
                <td className="px-4 py-3">
                  <span className={`badge ${STATUS_BADGE[post.status]}`}>
                    {STATUS_LABELS[post.status]}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2 justify-end">
                    {post.status !== "posted" && post.status !== "posting" && (
                      <button
                        onClick={() => deleteMutation.mutate(post.id)}
                        className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                      >
                        <Trash2 size={15} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && <PostCreateModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
