"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Copy, ExternalLink, Trash2, ToggleLeft, ToggleRight } from "lucide-react";
import { api } from "@/lib/api";
import { AffiliateLink } from "@/types";
import { LinkCreateModal } from "@/components/links/LinkCreateModal";

export default function LinksPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["links", search],
    queryFn: () => api.listLinks({ search: search || undefined, per_page: 100 }).then((r) => r.data.data),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.updateLink(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["links"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteLink(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["links"] }),
  });

  const copyToClipboard = (url: string) => {
    navigator.clipboard.writeText(url);
  };

  const links: AffiliateLink[] = data?.items || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2>アフィリエイトリンク管理</h2>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} />
          リンクを追加
        </button>
      </div>

      <div>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="リンク名で検索..."
          className="form-input max-w-xs"
        />
      </div>

      <div className="grid grid-cols-1 gap-4">
        {isLoading && <p className="text-gray-400">読み込み中...</p>}
        {!isLoading && links.length === 0 && (
          <div className="card text-center text-gray-400 py-12">
            リンクがありません。最初のアフィリエイトリンクを追加しましょう。
          </div>
        )}
        {links.map((link) => (
          <div key={link.id} className="card">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-sm font-semibold truncate">{link.name}</h3>
                  {!link.is_active && <span className="badge badge-gray">無効</span>}
                  {link.tags.map((tag) => (
                    <span key={tag} className="badge badge-blue">{tag}</span>
                  ))}
                </div>
                <div className="flex items-center gap-2 mb-2">
                  <code className="text-xs bg-gray-100 px-2 py-0.5 rounded text-gray-600 truncate max-w-xs">
                    {link.short_url}
                  </code>
                  <button
                    onClick={() => copyToClipboard(link.short_url)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                    title="コピー"
                  >
                    <Copy size={13} />
                  </button>
                  <a
                    href={link.destination_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1 text-gray-400 hover:text-blue-500"
                    title="リンクを開く"
                  >
                    <ExternalLink size={13} />
                  </a>
                </div>
                <p className="text-xs text-gray-400 truncate">{link.destination_url}</p>
              </div>

              <div className="flex flex-col items-end gap-2">
                <div className="text-right">
                  <p className="text-2xl font-bold text-purple-600">{link.total_clicks.toLocaleString()}</p>
                  <p className="text-xs text-gray-400">総クリック</p>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => toggleMutation.mutate({ id: link.id, is_active: !link.is_active })}
                    className="p-1 text-gray-400 hover:text-blue-500"
                    title={link.is_active ? "無効化" : "有効化"}
                  >
                    {link.is_active ? <ToggleRight size={20} className="text-green-500" /> : <ToggleLeft size={20} />}
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`「${link.name}」を削除しますか？`)) deleteMutation.mutate(link.id);
                    }}
                    className="p-1 text-gray-400 hover:text-red-500"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {showCreate && <LinkCreateModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
