import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Download, Edit, Share2, Calendar, Clock, User, MapPin } from "lucide-react";
import MarkdownStream from "../components/MarkdownStream";
import { getToken } from "../lib/auth";

interface Article {
  article_id: string;
  user_id: string;
  title: string;
  content_markdown: string;
  status: "draft" | "published" | "archived";
  version: number;
  metadata: {
    word_count: number;
    read_time: string;
    tags: string[];
    location_info?: {
      city: string;
      pois: string[];
    };
  };
  created_at: string;
  updated_at: string;
}

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8001";

export default function ArticleDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchArticle() {
      if (!id) return;

      try {
        setLoading(true);
        const response = await fetch(`${API_BASE}/api/articles/${id}`, {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getToken()}`,
          },
        });

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error("文章不存在");
          }
          if (response.status === 401) {
            navigate("/login");
            return;
          }
          throw new Error(`获取文章失败: ${response.statusText}`);
        }

        const data = await response.json();
        setArticle(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "未知错误");
      } finally {
        setLoading(false);
      }
    }

    fetchArticle();
  }, [id, navigate]);

  const handleDownload = async () => {
    if (!article) return;

    try {
      const response = await fetch(`${API_BASE}/api/articles/${article.article_id}/download`, {
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error(`下载失败: ${response.statusText}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${article.title}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err instanceof Error ? err.message : "下载失败");
    }
  };

  const handleEdit = () => {
    if (article) {
      navigate(`/creation?edit=${article.article_id}`);
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-cyan-500 border-t-transparent"></div>
          <p className="text-sm text-slate-400">加载文章中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center">
        <div className="rounded-xl border border-red-300/30 bg-red-500/10 p-6 text-center">
          <h3 className="mb-2 text-lg font-semibold text-red-200">加载失败</h3>
          <p className="text-sm text-red-300/80">{error}</p>
          <button
            onClick={() => navigate(-1)}
            className="mt-4 inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:bg-white/10"
          >
            <ArrowLeft className="h-4 w-4" />
            返回
          </button>
        </div>
      </div>
    );
  }

  if (!article) {
    return (
      <div className="flex h-full flex-col items-center justify-center">
        <div className="rounded-xl border border-slate-300/30 bg-white/5 p-6 text-center">
          <h3 className="mb-2 text-lg font-semibold text-slate-200">文章不存在</h3>
          <p className="text-sm text-slate-400">请求的文章可能已被删除或不存在</p>
          <button
            onClick={() => navigate("/creation")}
            className="mt-4 inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:bg-white/10"
          >
            <ArrowLeft className="h-4 w-4" />
            返回创作中心
          </button>
        </div>
      </div>
    );
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="flex h-full flex-col">
      {/* 头部工具栏 */}
      <div className="mb-6 flex items-center justify-between border-b border-white/10 pb-4">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-200 transition hover:bg-white/10"
        >
          <ArrowLeft className="h-4 w-4" />
          返回
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={handleEdit}
            className="inline-flex items-center gap-2 rounded-xl border border-cyan-300/30 bg-cyan-500/20 px-3 py-1.5 text-sm text-cyan-100 transition hover:bg-cyan-500/30"
          >
            <Edit className="h-4 w-4" />
            编辑
          </button>
          <button
            onClick={handleDownload}
            className="inline-flex items-center gap-2 rounded-xl border border-emerald-300/30 bg-emerald-500/20 px-3 py-1.5 text-sm text-emerald-100 transition hover:bg-emerald-500/30"
          >
            <Download className="h-4 w-4" />
            下载
          </button>
          <button
            onClick={() => alert("分享功能开发中")}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-200 transition hover:bg-white/10"
          >
            <Share2 className="h-4 w-4" />
            分享
          </button>
        </div>
      </div>

      {/* 文章元信息 */}
      <div className="mb-8 rounded-2xl border border-white/10 bg-black/20 p-5">
        <h1 className="mb-4 text-2xl font-bold text-[hsl(var(--foreground))]">{article.title}</h1>

        <div className="mb-4 flex flex-wrap items-center gap-4 text-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <User className="h-4 w-4" />
            <span>内容运营负责人</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <Calendar className="h-4 w-4" />
            <span>创建时间: {formatDate(article.created_at)}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <Clock className="h-4 w-4" />
            <span>更新时间: {formatDate(article.updated_at)}</span>
          </div>
          {article.metadata.location_info && (
            <div className="flex items-center gap-2 text-slate-400">
              <MapPin className="h-4 w-4" />
              <span>{article.metadata.location_info.city}</span>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-cyan-300/30 bg-cyan-500/20 px-3 py-1 text-xs font-medium text-cyan-100">
            {article.status === "draft" ? "草稿" : article.status === "published" ? "已发布" : "已归档"}
          </span>
          <span className="rounded-full border border-slate-300/30 bg-slate-500/20 px-3 py-1 text-xs font-medium text-slate-300">
            版本 {article.version}
          </span>
          <span className="rounded-full border border-emerald-300/30 bg-emerald-500/20 px-3 py-1 text-xs font-medium text-emerald-100">
            {article.metadata.word_count} 字
          </span>
          <span className="rounded-full border border-purple-300/30 bg-purple-500/20 px-3 py-1 text-xs font-medium text-purple-100">
            {article.metadata.read_time} 阅读
          </span>
          {article.metadata.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full border border-slate-300/30 bg-white/5 px-3 py-1 text-xs font-medium text-slate-300"
            >
              {tag}
            </span>
          ))}
        </div>

        {article.metadata.location_info && article.metadata.location_info.pois.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-sm font-medium text-slate-300">相关地点:</p>
            <div className="flex flex-wrap gap-2">
              {article.metadata.location_info.pois.map((poi) => (
                <span
                  key={poi}
                  className="rounded-full border border-amber-300/30 bg-amber-500/20 px-3 py-1 text-xs font-medium text-amber-100"
                >
                  {poi}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 文章内容 */}
      <div className="flex-1 overflow-y-auto">
        <div className="prose prose-invert max-w-none rounded-2xl border border-white/10 bg-black/20 p-6">
          <MarkdownStream content={article.content_markdown} showDownload={false} />
        </div>
      </div>
    </div>
  );
}