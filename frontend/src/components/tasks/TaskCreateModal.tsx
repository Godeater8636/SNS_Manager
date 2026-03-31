"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { api } from "@/lib/api";
import { SocialAccount, TaskType } from "@/types";

interface Props {
  onClose: () => void;
}

export function TaskCreateModal({ onClose }: Props) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    social_account_id: "",
    task_type: "auto_like" as TaskType,
    search_keyword: "",
    target_username: "",
    cron_expression: "*/30 * * * *",
    is_enabled: false,
  });
  const [error, setError] = useState<string | null>(null);

  const { data: accountsData } = useQuery({
    queryKey: ["social-accounts"],
    queryFn: () => api.listAccounts().then((r) => r.data.data.items as SocialAccount[]),
  });

  const mutation = useMutation({
    mutationFn: () => api.createTask(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      onClose();
    },
    onError: (e: unknown) => {
      const err = e as { response?: { data?: { error?: { message?: string } } } };
      setError(err?.response?.data?.error?.message || "タスクの作成に失敗しました");
    },
  });

  const update = (key: string, value: unknown) => setForm((f) => ({ ...f, [key]: value }));

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-lg">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold">自動タスクを追加</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg"><X size={20} /></button>
        </div>
        <div className="p-6 space-y-4">
          {error && <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>}

          <div>
            <label className="form-label">Xアカウント *</label>
            <select value={form.social_account_id} onChange={(e) => update("social_account_id", e.target.value)} className="form-input">
              <option value="">アカウントを選択</option>
              {accountsData?.map((a) => (
                <option key={a.id} value={a.id}>@{a.x_username}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label">タスクタイプ *</label>
            <select value={form.task_type} onChange={(e) => update("task_type", e.target.value)} className="form-input">
              <option value="auto_like">自動いいね</option>
              <option value="auto_follow">自動フォロー</option>
            </select>
          </div>

          {form.task_type === "auto_like" && (
            <div>
              <label className="form-label">検索キーワード</label>
              <input type="text" value={form.search_keyword} onChange={(e) => update("search_keyword", e.target.value)} className="form-input" placeholder="#おすすめ商品 -is:retweet lang:ja" />
              <p className="text-xs text-gray-400 mt-1">X 検索クエリ形式で入力</p>
            </div>
          )}

          {form.task_type === "auto_follow" && (
            <div>
              <label className="form-label">フォロワーを取得する対象ユーザー名</label>
              <div className="flex items-center">
                <span className="text-gray-500 mr-1">@</span>
                <input type="text" value={form.target_username} onChange={(e) => update("target_username", e.target.value)} className="form-input" placeholder="target_user" />
              </div>
            </div>
          )}

          <div>
            <label className="form-label">実行スケジュール（Cron式）</label>
            <input type="text" value={form.cron_expression} onChange={(e) => update("cron_expression", e.target.value)} className="form-input font-mono" />
            <p className="text-xs text-gray-400 mt-1">例: */30 * * * * = 30分ごと、0 */2 * * * = 2時間ごと</p>
          </div>

          <div className="flex items-center gap-2">
            <input type="checkbox" id="is_enabled" checked={form.is_enabled} onChange={(e) => update("is_enabled", e.target.checked)} className="w-4 h-4" />
            <label htmlFor="is_enabled" className="text-sm text-gray-700">作成後すぐに有効化する</label>
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t border-gray-200">
          <button onClick={onClose} className="btn-secondary">キャンセル</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.social_account_id} className="btn-primary">
            {mutation.isPending ? "作成中..." : "タスクを作成"}
          </button>
        </div>
      </div>
    </div>
  );
}
