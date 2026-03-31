"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { SocialAccount } from "@/types";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

interface ThreadItem {
  content: string;
}

interface Props {
  onClose: () => void;
}

export function PostCreateModal({ onClose }: Props) {
  const qc = useQueryClient();
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [scheduledAt, setScheduledAt] = useState<Date | null>(null);
  const [thread, setThread] = useState<ThreadItem[]>([{ content: "" }]);
  const [error, setError] = useState<string | null>(null);

  const { data: accountsData } = useQuery({
    queryKey: ["social-accounts"],
    queryFn: () => api.listAccounts().then((r) => r.data.data.items as SocialAccount[]),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.createPost({
        social_account_id: selectedAccountId,
        scheduled_at: scheduledAt?.toISOString() || null,
        thread: thread.filter((t) => t.content.trim()),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      onClose();
    },
    onError: (e: unknown) => {
      const err = e as { response?: { data?: { error?: { message?: string } } } };
      setError(err?.response?.data?.error?.message || "投稿の作成に失敗しました");
    },
  });

  const addThread = () => {
    if (thread.length < 25) setThread([...thread, { content: "" }]);
  };

  const removeThread = (i: number) => {
    if (thread.length > 1) setThread(thread.filter((_, idx) => idx !== i));
  };

  const updateThread = (i: number, content: string) => {
    setThread(thread.map((t, idx) => (idx === i ? { content } : t)));
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold">新規投稿作成</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg">
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
          )}

          <div>
            <label className="form-label">Xアカウント *</label>
            <select
              value={selectedAccountId}
              onChange={(e) => setSelectedAccountId(e.target.value)}
              className="form-input"
            >
              <option value="">アカウントを選択</option>
              {accountsData?.map((a) => (
                <option key={a.id} value={a.id}>@{a.x_username}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label">予約日時（未設定 = 下書き）</label>
            <DatePicker
              selected={scheduledAt}
              onChange={setScheduledAt}
              showTimeSelect
              dateFormat="yyyy/MM/dd HH:mm"
              minDate={new Date()}
              placeholderText="日時を選択"
              className="form-input"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="form-label mb-0">投稿内容（スレッド）</label>
              <span className="text-xs text-gray-400">{thread.length} / 25</span>
            </div>
            <div className="space-y-3">
              {thread.map((item, i) => (
                <div key={i} className="relative">
                  <div className="flex items-start gap-2">
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-gray-400">#{i + 1}</span>
                        <span className={`text-xs ${item.content.length > 260 ? "text-red-500" : "text-gray-400"}`}>
                          {item.content.length} / 280
                        </span>
                      </div>
                      <textarea
                        value={item.content}
                        onChange={(e) => updateThread(i, e.target.value)}
                        className="form-input resize-none"
                        rows={3}
                        maxLength={280}
                        placeholder="投稿テキストを入力..."
                      />
                    </div>
                    {thread.length > 1 && (
                      <button onClick={() => removeThread(i)} className="mt-6 p-1 text-gray-400 hover:text-red-500">
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
            {thread.length < 25 && (
              <button onClick={addThread} className="mt-2 flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700">
                <Plus size={15} />
                スレッドを追加
              </button>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-3 p-6 border-t border-gray-200">
          <button onClick={onClose} className="btn-secondary">キャンセル</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !selectedAccountId || thread.every((t) => !t.content.trim())}
            className="btn-primary"
          >
            {mutation.isPending
              ? "作成中..."
              : scheduledAt
              ? "予約投稿を作成"
              : "下書きとして保存"}
          </button>
        </div>
      </div>
    </div>
  );
}
