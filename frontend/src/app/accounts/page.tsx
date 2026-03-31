"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, RefreshCw, Trash2, Shield } from "lucide-react";
import { api } from "@/lib/api";
import { SocialAccount } from "@/types";
import { AccountAddModal } from "@/components/accounts/AccountAddModal";

export default function AccountsPage() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["social-accounts"],
    queryFn: () => api.listAccounts().then((r) => r.data.data.items as SocialAccount[]),
  });

  const refreshMutation = useMutation({
    mutationFn: (id: string) => api.refreshSession(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["social-accounts"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteAccount(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["social-accounts"] }),
  });

  const accounts: SocialAccount[] = data || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2>X アカウント管理</h2>
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} />
          アカウントを追加
        </button>
      </div>

      {isLoading && <p className="text-gray-400">読み込み中...</p>}
      {!isLoading && accounts.length === 0 && (
        <div className="card text-center text-gray-400 py-12">
          Xアカウントが登録されていません。
        </div>
      )}

      <div className="grid grid-cols-1 gap-4">
        {accounts.map((acc) => (
          <div key={acc.id} className="card">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-semibold">@{acc.x_username}</p>
                  <span className={`badge ${acc.is_active ? "badge-green" : "badge-red"}`}>
                    {acc.is_active ? "有効" : "無効"}
                  </span>
                </div>
                <p className="text-sm text-gray-500 mt-0.5">{acc.x_display_name || "—"}</p>
                <div className="flex gap-4 mt-3 text-sm">
                  <div className="text-center">
                    <p className="font-semibold text-blue-600">{acc.daily_likes_count}</p>
                    <p className="text-xs text-gray-400">本日のいいね</p>
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-green-600">{acc.daily_follows_count}</p>
                    <p className="text-xs text-gray-400">本日のフォロー</p>
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-gray-600">{acc.daily_like_limit}</p>
                    <p className="text-xs text-gray-400">いいね上限</p>
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-gray-600">{acc.daily_follow_limit}</p>
                    <p className="text-xs text-gray-400">フォロー上限</p>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 text-xs text-gray-400 bg-gray-50 px-2 py-1 rounded-lg">
                  <Shield size={12} />
                  {acc.action_min_interval_sec}〜{acc.action_max_interval_sec}s間隔
                </div>
                <button
                  onClick={() => refreshMutation.mutate(acc.id)}
                  disabled={refreshMutation.isPending}
                  className="p-1.5 text-gray-400 hover:text-blue-500 border border-gray-200 rounded-lg"
                  title="セッション更新"
                >
                  <RefreshCw size={15} />
                </button>
                <button
                  onClick={() => {
                    if (confirm(`@${acc.x_username}を削除しますか？`)) deleteMutation.mutate(acc.id);
                  }}
                  className="p-1.5 text-gray-400 hover:text-red-500 border border-gray-200 rounded-lg"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {showAdd && <AccountAddModal onClose={() => setShowAdd(false)} />}
    </div>
  );
}
