"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Plan } from "@/types";
import { useAuthStore } from "@/lib/auth";
import { Check } from "lucide-react";

const PLAN_FEATURES: Record<string, string[]> = {
  starter: ["Xアカウント 1件", "月100投稿", "アフィリエイトリンク管理", "基本分析"],
  pro: ["Xアカウント 5件", "月1,000投稿", "自動いいね / フォロー", "詳細分析", "CSV エクスポート"],
  business: ["Xアカウント 20件", "無制限投稿", "自動いいね / フォロー", "詳細分析", "CSV エクスポート", "優先サポート"],
};

export default function SettingsPage() {
  const { user } = useAuthStore();

  const { data: plans } = useQuery({
    queryKey: ["plans"],
    queryFn: () => api.listPlans().then((r) => r.data.data as Plan[]),
  });

  const { data: paymentsData } = useQuery({
    queryKey: ["payments"],
    queryFn: () => api.paymentHistory().then((r) => r.data.data),
  });

  return (
    <div className="space-y-8 max-w-4xl">
      <h2>設定・プラン管理</h2>

      {/* Current plan */}
      <div className="card">
        <h3 className="text-base font-semibold mb-3">現在のプラン</h3>
        <div className="flex items-center gap-4">
          <div>
            <p className="text-lg font-bold">{user?.plan?.display_name || "Starter"}</p>
            {user?.plan?.expires_at && (
              <p className="text-sm text-gray-500">
                有効期限: {new Date(user.plan.expires_at).toLocaleDateString("ja-JP")}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Plan comparison */}
      <div>
        <h3 className="text-base font-semibold mb-4">プラン比較</h3>
        <div className="grid grid-cols-3 gap-4">
          {plans?.map((plan) => (
            <div
              key={plan.id}
              className={`card relative ${
                user?.plan?.name === plan.name ? "border-blue-500 border-2" : ""
              }`}
            >
              {user?.plan?.name === plan.name && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-500 text-white text-xs px-2 py-0.5 rounded-full">
                  現在のプラン
                </div>
              )}
              <p className="font-bold text-lg">{plan.display_name}</p>
              <p className="text-2xl font-bold mt-1">
                ¥{plan.price_jpy.toLocaleString()}
                <span className="text-sm font-normal text-gray-500">/月</span>
              </p>
              <ul className="mt-4 space-y-2">
                {(PLAN_FEATURES[plan.name] || []).map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-gray-700">
                    <Check size={14} className="text-green-500 flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              {user?.plan?.name !== plan.name && (
                <button
                  onClick={() => {
                    if (confirm(`${plan.display_name}プランに変更しますか？`)) {
                      api.changePlan(plan.name).then(() => window.location.reload());
                    }
                  }}
                  className="btn-secondary w-full mt-4 text-sm"
                >
                  このプランに変更
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Payment history */}
      <div className="card">
        <h3 className="text-base font-semibold mb-4">決済履歴</h3>
        {(!paymentsData?.items || paymentsData.items.length === 0) && (
          <p className="text-sm text-gray-400">決済履歴がありません</p>
        )}
        <div className="space-y-2">
          {paymentsData?.items?.map((p: { id: string; created_at: string; status: string; amount_jpy: number }) => (
            <div key={p.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
              <div>
                <p className="text-sm font-medium">{new Date(p.created_at).toLocaleDateString("ja-JP")}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className={`badge ${p.status === "succeeded" ? "badge-green" : "badge-red"}`}>
                  {p.status === "succeeded" ? "成功" : "失敗"}
                </span>
                <span className="text-sm font-semibold">¥{p.amount_jpy.toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Cancel subscription */}
      <div className="card border-red-100">
        <h3 className="text-base font-semibold mb-2 text-red-700">解約</h3>
        <p className="text-sm text-gray-500 mb-4">解約後も次回更新日までサービスをご利用いただけます。</p>
        <button
          onClick={() => {
            if (confirm("サブスクリプションを解約しますか？")) {
              api.cancelSubscription().then(() => alert("解約手続きが完了しました"));
            }
          }}
          className="btn-danger text-sm"
        >
          解約する
        </button>
      </div>
    </div>
  );
}
