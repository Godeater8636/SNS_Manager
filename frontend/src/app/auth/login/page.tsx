"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { useAuthStore } from "@/lib/auth";

const schema = z.object({
  email: z.string().email("有効なメールアドレスを入力してください"),
  password: z.string().min(1, "パスワードを入力してください"),
  totp_code: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading } = useAuthStore();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setError(null);
    try {
      await login(data.email, data.password, data.totp_code);
      router.push("/dashboard");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: { message?: string } } } };
      setError(err?.response?.data?.error?.message || "ログインに失敗しました");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-blue-700">SNS Manager</h1>
          <p className="text-gray-500 mt-1">X アフィリエイト管理ツール</p>
        </div>
        <div className="card">
          <h2 className="text-xl font-semibold mb-6">ログイン</h2>
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="form-label">メールアドレス</label>
              <input type="email" {...register("email")} className="form-input" placeholder="you@example.com" />
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
            </div>
            <div>
              <label className="form-label">パスワード</label>
              <input type="password" {...register("password")} className="form-input" />
              {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>}
            </div>
            <div>
              <label className="form-label">2段階認証コード（任意）</label>
              <input type="text" {...register("totp_code")} className="form-input" placeholder="6桁のコード" maxLength={6} />
            </div>
            <button type="submit" disabled={isLoading} className="btn-primary w-full mt-2">
              {isLoading ? "ログイン中..." : "ログイン"}
            </button>
          </form>
          <p className="text-center text-sm text-gray-500 mt-4">
            アカウントをお持ちでない方は{" "}
            <Link href="/auth/register" className="text-blue-600 hover:underline">
              新規登録
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
