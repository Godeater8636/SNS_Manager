"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Play, Pause, Heart, UserPlus } from "lucide-react";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { api } from "@/lib/api";
import { Task, TaskType } from "@/types";
import { TaskCreateModal } from "@/components/tasks/TaskCreateModal";

const TASK_LABELS: Record<TaskType, string> = {
  auto_like: "自動いいね",
  auto_follow: "自動フォロー",
  auto_unfollow: "自動フォロー解除",
};

const TASK_ICONS: Record<TaskType, React.ReactNode> = {
  auto_like: <Heart size={16} className="text-pink-500" />,
  auto_follow: <UserPlus size={16} className="text-blue-500" />,
  auto_unfollow: <UserPlus size={16} className="text-gray-400" />,
};

export default function TasksPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["tasks"],
    queryFn: () => api.listTasks().then((r) => r.data.data.items as Task[]),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_enabled }: { id: string; is_enabled: boolean }) =>
      api.updateTask(id, { is_enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteTask(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const tasks: Task[] = data || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2>自動タスク管理</h2>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} />
          タスクを追加
        </button>
      </div>

      {isLoading && <p className="text-gray-400">読み込み中...</p>}
      {!isLoading && tasks.length === 0 && (
        <div className="card text-center text-gray-400 py-12">
          自動タスクがありません。Pro以上のプランでご利用いただけます。
        </div>
      )}

      <div className="grid grid-cols-1 gap-4">
        {tasks.map((task) => (
          <div key={task.id} className="card">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  {TASK_ICONS[task.task_type]}
                  <span className="font-semibold text-sm">{TASK_LABELS[task.task_type]}</span>
                  <span className={`badge ${task.is_enabled ? "badge-green" : "badge-gray"}`}>
                    {task.is_enabled ? "有効" : "無効"}
                  </span>
                </div>
                {task.search_keyword && (
                  <p className="text-xs text-gray-500 mb-1">
                    キーワード: <code className="bg-gray-100 px-1 rounded">{task.search_keyword}</code>
                  </p>
                )}
                {task.target_username && (
                  <p className="text-xs text-gray-500 mb-1">
                    対象: <span className="font-medium">@{task.target_username}</span>
                  </p>
                )}
                <p className="text-xs text-gray-400">スケジュール: {task.cron_expression}</p>
                <div className="flex gap-4 mt-3 text-sm">
                  <div>
                    <span className="font-semibold text-gray-800">{task.total_success.toLocaleString()}</span>
                    <span className="text-xs text-gray-400 ml-1">成功</span>
                  </div>
                  <div>
                    <span className="font-semibold text-red-500">{task.total_failed}</span>
                    <span className="text-xs text-gray-400 ml-1">失敗</span>
                  </div>
                  {task.last_executed_at && (
                    <div>
                      <span className="text-xs text-gray-400">
                        最終実行: {format(new Date(task.last_executed_at), "M/d HH:mm", { locale: ja })}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => toggleMutation.mutate({ id: task.id, is_enabled: !task.is_enabled })}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    task.is_enabled
                      ? "border-gray-200 text-gray-600 hover:bg-gray-50"
                      : "border-blue-200 text-blue-600 hover:bg-blue-50"
                  }`}
                >
                  {task.is_enabled ? <Pause size={13} /> : <Play size={13} />}
                  {task.is_enabled ? "停止" : "開始"}
                </button>
                <button
                  onClick={() => {
                    if (confirm("このタスクを削除しますか？")) deleteMutation.mutate(task.id);
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

      {showCreate && <TaskCreateModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
