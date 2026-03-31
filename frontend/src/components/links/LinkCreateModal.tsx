"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { api } from "@/lib/api";

interface Props {
  onClose: () => void;
}

export function LinkCreateModal({ onClose }: Props) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ name: "", destination_url: "", tags: "", description: "" });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      api.createLink({
        ...form,
        tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["links"] });
      onClose();
    },
    onError: (e: unknown) => {
      const err = e as { response?: { data?: { error?: { message?: string } } } };
      setError(err?.response?.data?.error?.message || "リンクの作成に失敗しました");
    },
  });

  const update = (key: string, value: string) => setForm((f) => ({ ...f, [key]: value }));

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-lg">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold">アフィリエイトリンクを追加</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg"><X size={20} /></button>
        </div>
        <div className="p-6 space-y-4">
          {error && <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>}
          <div>
            <label className="form-label">リンク名 *</label>
            <input type="text" value={form.name} onChange={(e) => update("name", e.target.value)} className="form-input" placeholder="おすすめ商品A" />
          </div>
          <div>
            <label className="form-label">転送先URL *</label>
            <input type="url" value={form.destination_url} onChange={(e) => update("destination_url", e.target.value)} className="form-input" placeholder="https://affiliate.example.com/..." />
          </div>
          <div>
            <label className="form-label">タグ（カンマ区切り）</label>
            <input type="text" value={form.tags} onChange={(e) => update("tags", e.target.value)} className="form-input" placeholder="物販, 美容" />
          </div>
          <div>
            <label className="form-label">メモ</label>
            <textarea value={form.description} onChange={(e) => update("description", e.target.value)} className="form-input resize-none" rows={2} />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t border-gray-200">
          <button onClick={onClose} className="btn-secondary">キャンセル</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.name || !form.destination_url} className="btn-primary">
            {mutation.isPending ? "作成中..." : "リンクを作成"}
          </button>
        </div>
      </div>
    </div>
  );
}
