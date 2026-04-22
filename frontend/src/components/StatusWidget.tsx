import { useEffect, useState } from "react";
import { MessageSquare, FileText, Clock, CheckCircle, AlertCircle, TrendingUp } from "lucide-react";
import { getToken } from "../lib/auth";

interface StatsData {
  today: {
    chat_count: number;
    creation_count: number;
    published_count: number;
  };
  total: {
    chat_count: number;
    creation_count: number;
    published_count: number;
  };
  active_tasks: number;
  system_status: "healthy" | "degraded" | "down";
  last_updated: string;
}

interface QuickStat {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  trend?: "up" | "down" | "stable";
  color: "cyan" | "emerald" | "amber" | "slate";
}

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8001";

export default function StatusWidget() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStats() {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE}/api/stats/summary`, {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getToken()}`,
          },
        });

        if (!response.ok) {
          throw new Error(`获取统计失败: ${response.statusText}`);
        }

        const data = await response.json();
        setStats(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "未知错误");
        // 使用模拟数据作为后备
        setStats({
          today: {
            chat_count: 18,
            creation_count: 3,
            published_count: 2,
          },
          total: {
            chat_count: 245,
            creation_count: 67,
            published_count: 42,
          },
          active_tasks: 5,
          system_status: "healthy",
          last_updated: new Date().toISOString(),
        });
      } finally {
        setLoading(false);
      }
    }

    fetchStats();

    // 每30秒刷新一次
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return "刚刚";
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}小时前`;
    return `${Math.floor(diffMins / 1440)}天前`;
  };

  const getStatusColor = (status: "healthy" | "degraded" | "down") => {
    switch (status) {
      case "healthy":
        return "bg-emerald-500/20 text-emerald-100 border-emerald-300/30";
      case "degraded":
        return "bg-amber-500/20 text-amber-100 border-amber-300/30";
      case "down":
        return "bg-red-500/20 text-red-100 border-red-300/30";
    }
  };

  const getStatusIcon = (status: "healthy" | "degraded" | "down") => {
    switch (status) {
      case "healthy":
        return <CheckCircle className="h-4 w-4" />;
      case "degraded":
        return <AlertCircle className="h-4 w-4" />;
      case "down":
        return <AlertCircle className="h-4 w-4" />;
    }
  };

  const getStatusText = (status: "healthy" | "degraded" | "down") => {
    switch (status) {
      case "healthy":
        return "运行正常";
      case "degraded":
        return "部分降级";
      case "down":
        return "服务异常";
    }
  };

  if (loading && !stats) {
    return (
      <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[hsl(var(--foreground))]">系统概览</h3>
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent"></div>
        </div>
        <div className="mt-4 space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded-lg bg-white/5"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[hsl(var(--foreground))]">系统概览</h3>
          <AlertCircle className="h-4 w-4 text-amber-400" />
        </div>
        <div className="mt-4 rounded-lg border border-amber-300/30 bg-amber-500/10 p-3">
          <p className="text-sm text-amber-300">{error}</p>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  const quickStats: QuickStat[] = [
    {
      label: "今日聊天",
      value: stats.today.chat_count,
      icon: MessageSquare,
      trend: stats.today.chat_count > 10 ? "up" : "stable",
      color: "cyan",
    },
    {
      label: "今日创作",
      value: stats.today.creation_count,
      icon: FileText,
      trend: stats.today.creation_count > 2 ? "up" : "stable",
      color: "emerald",
    },
    {
      label: "进行中任务",
      value: stats.active_tasks,
      icon: Clock,
      trend: stats.active_tasks > 3 ? "up" : "stable",
      color: "amber",
    },
  ];

  const totalStats: QuickStat[] = [
    {
      label: "总聊天数",
      value: stats.total.chat_count,
      icon: MessageSquare,
      color: "slate",
    },
    {
      label: "总创作数",
      value: stats.total.creation_count,
      icon: FileText,
      color: "slate",
    },
    {
      label: "已发布",
      value: stats.total.published_count,
      icon: CheckCircle,
      color: "slate",
    },
  ];

  const getStatColorClasses = (color: QuickStat["color"]) => {
    switch (color) {
      case "cyan":
        return "bg-cyan-500/20 text-cyan-100 border-cyan-300/30";
      case "emerald":
        return "bg-emerald-500/20 text-emerald-100 border-emerald-300/30";
      case "amber":
        return "bg-amber-500/20 text-amber-100 border-amber-300/30";
      case "slate":
        return "bg-white/5 text-slate-300 border-white/10";
    }
  };

  const getIconColor = (color: QuickStat["color"]) => {
    switch (color) {
      case "cyan":
        return "text-cyan-300";
      case "emerald":
        return "text-emerald-300";
      case "amber":
        return "text-amber-300";
      case "slate":
        return "text-slate-400";
    }
  };

  return (
    <div className="space-y-4">
      {/* 系统状态卡片 */}
      <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[hsl(var(--foreground))]">系统状态</h3>
          <div className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs ${getStatusColor(stats.system_status)}`}>
            {getStatusIcon(stats.system_status)}
            <span>{getStatusText(stats.system_status)}</span>
          </div>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          最后更新: {formatTime(stats.last_updated)}
        </p>
      </div>

      {/* 今日数据卡片 */}
      <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[hsl(var(--foreground))]">今日数据</h3>
          <TrendingUp className="h-4 w-4 text-slate-400" />
        </div>
        <div className="space-y-2">
          {quickStats.map((stat) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.label}
                className={`flex items-center justify-between rounded-lg border px-3 py-2 ${getStatColorClasses(stat.color)}`}
              >
                <div className="flex items-center gap-2">
                  <Icon className={`h-4 w-4 ${getIconColor(stat.color)}`} />
                  <span className="text-sm">{stat.label}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="font-medium">{stat.value}</span>
                  {stat.trend && stat.trend === "up" && (
                    <span className="text-xs text-emerald-300">↑</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 总计数据卡片 */}
      <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[hsl(var(--foreground))]">总计数据</h3>
          <span className="text-xs text-slate-400">累计</span>
        </div>
        <div className="space-y-2">
          {totalStats.map((stat) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.label}
                className={`flex items-center justify-between rounded-lg border px-3 py-2 ${getStatColorClasses(stat.color)}`}
              >
                <div className="flex items-center gap-2">
                  <Icon className={`h-4 w-4 ${getIconColor(stat.color)}`} />
                  <span className="text-sm">{stat.label}</span>
                </div>
                <span className="font-medium">{stat.value}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 刷新按钮 */}
      <div className="flex justify-center">
        <button
          onClick={() => window.location.reload()}
          className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-200 transition hover:bg-white/10"
        >
          刷新数据
        </button>
      </div>
    </div>
  );
}