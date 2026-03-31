"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { api } from "@/lib/api";
import { setAccessToken } from "@/lib/api";
import { useAuthStore } from "@/lib/auth";

const schema = z
  .object({
    email: z.string().email("有効なメールアドレスを入力してください"),
    display_name: z.string().optional(),
    password: z.string()
      .min(8, "8文字以上で入力してください")
      .regex(/[A-Z]/, "大文字を含めてください")
      .regex(/[0-9]/, "数字を含めてください"),
    confirm_password: z.string(),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "パスワードが一致しません",
    path: ["confirm_password"],
  });

type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const router = useRouter();
  const { fetchMe } = useAuthStore();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setError(null);
    setLoading(true);
    try {
      const res = await api.register(data.email, data.password, data.display_name);
      setAccessToken(res.data.data.access_token);
      await fetchMe();
      router.push("/dashboard");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: { message?: string } } } };
      setError(err?.response?.data?.error?.message || "登録に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-blue-700">SNS Manager</h1>
          <p className="text-gray-500 mt-1">14日間無料トライアル開始</p>
        </div>
        <div className="card">
          <h2 className="text-xl font-semibold mb-6">新規登録</h2>
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
          )}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="form-label">メールアドレス <span className="text-red-500">*</span></label>
              <input type="email" {...register("email")} className="form-input" />
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
            </div>
            <div>
              <label className="form-label">表示名</label>
              <input type="text" {...register("display_name")} className="form-input" />
            </div>
            <div>
              <label className="form-label">パスワード <span className="text-red-500">*</span></label>
              <input type="password" {...register("password")} className="form-input" />
              {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>}
            </div>
            <div>
              <label className="form-label">パスワード確認 <span className="text-red-500">*</span></label>
              <input type="password" {...register("confirm_password")} className="form-input" />
              {errors.confirm_password && <p className="text-red-500 text-xs mt-1">{errors.confirm_password.message}</p>}
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
              {loading ? "登録中..." : "アカウントを作成（無料）"}
            </button>
          </form>
          <p className="text-center text-sm text-gray-500 mt-4">
            既にアカウントをお持ちの方は{" "}
            <Link href="/auth/login" className="text-blue-600 hover:underline">ログイン</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
