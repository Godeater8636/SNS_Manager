"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

interface Props {
  onClose: () => void;
}

export function AccountAddModal({ onClose }: Props) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    x_username: "",
    password: "",
    daily_like_limit: 200,
    daily_follow_limit: 100,
    action_min_interval_sec: 30,
    action_max_interval_sec: 90,
  });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => api.createAccount(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["social-accounts"] });
      onClose();
    },
    onError: (e: unknown) => {
      const err = e as { response?: { data?: { error?: { message?: string } } } };
      setError(err?.response?.data?.error?.message || "アカウントの追加に失敗しました");
    },
  });

  const update = (key: string, value: string | number) => setForm((f) => ({ ...f, [key]: value }));

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold">Xアカウントを追加</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg"><X size={20} /></button>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs">
            <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
            <p>パスワードはAES-256-GCMで暗号化されサーバーに保存されます。Xの利用規約に従ってご利用ください。</p>
          </div>

          {error && <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>}

          <div>
            <label className="form-label">Xユーザー名（@なし） *</label>
            <input type="text" value={form.x_username} onChange={(e) => update("x_username", e.target.value)} className="form-input" placeholder="yourhandle" />
          </div>
          <div>
            <label className="form-label">パスワード *</label>
            <input type="password" value={form.password} onChange={(e) => update("password", e.target.value)} className="form-input" />
          </div>

          <div className="border-t border-gray-100 pt-4">
            <p className="text-sm font-medium text-gray-700 mb-3">垢BAN回避パラメータ</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="form-label">1日いいね上限</label>
                <input type="number" value={form.daily_like_limit} onChange={(e) => update("daily_like_limit", Number(e.target.value))} className="form-input" min={0} max={500} />
              </div>
              <div>
                <label className="form-label">1日フォロー上限</label>
                <input type="number" value={form.daily_follow_limit} onChange={(e) => update("daily_follow_limit", Number(e.target.value))} className="form-input" min={0} max={400} />
              </div>
              <div>
                <label className="form-label">最小間隔（秒）</label>
                <input type="number" value={form.action_min_interval_sec} onChange={(e) => update("action_min_interval_sec", Number(e.target.value))} className="form-input" min={10} max={300} />
              </div>
              <div>
                <label className="form-label">最大間隔（秒）</label>
                <input type="number" value={form.action_max_interval_sec} onChange={(e) => update("action_max_interval_sec", Number(e.target.value))} className="form-input" min={10} max={600} />
              </div>
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t border-gray-200">
          <button onClick={onClose} className="btn-secondary">キャンセル</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.x_username || !form.password} className="btn-primary">
            {mutation.isPending ? "追加中..." : "アカウントを追加"}
          </button>
        </div>
      </div>
    </div>
  );
}
