import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Bot,
  CheckSquare,
  ClipboardPenLine,
  FolderKanban,
  Globe,
  ListTodo,
  LogOut,
  MoonStar,
  Settings,
  Sparkles,
  SunMedium,
  UserCircle2
} from "lucide-react";

import { clearAuth, getUserPreferences, updateUserPreferences, getCachedPreferences, cachePreferences, clearCachedPreferences } from "./lib/auth";
import StatusWidget from "./components/StatusWidget";

interface NavItem {
  labelKey: "create" | "tasks" | "review" | "chat" | "creation" | "materials" | "settings";
  to: string;
  icon: React.ComponentType<{ className?: string }>;
}

type Locale = "zh" | "en";
type ThemeMode = "dark" | "light";

export interface LayoutOutletContext {
  locale: Locale;
}

const navItems: NavItem[] = [
  { labelKey: "create", to: "/create", icon: ClipboardPenLine },
  { labelKey: "tasks", to: "/tasks", icon: ListTodo },
  { labelKey: "review", to: "/review", icon: CheckSquare },
  { labelKey: "chat", to: "/chat", icon: Bot },
  { labelKey: "creation", to: "/creation", icon: Sparkles },
  { labelKey: "materials", to: "/materials", icon: FolderKanban },
  { labelKey: "settings", to: "/settings", icon: Settings }
];

const copyMap = {
  zh: {
    appName: "ReWritter 控制台",
    appSubTitle: "创作工作流编排",
    nav: {
      create: "创作中心",
      tasks: "任务大厅",
      review: "审核台",
      chat: "聊天",
      creation: "创作",
      materials: "素材",
      settings: "设置"
    },
    profileName: "内容运营负责人",
    profileRole: "管理员",
    signOut: "退出登录",
    widgetTitle: "状态小部件",
    viewAll: "查看全部",
    emptyState: "暂无数据",
    addData: "添加数据",
    secondaryWidgetTitle: "系统概览",
    quickStats: [
      { label: "今日任务", value: "18" },
      { label: "待审核", value: "5" },
      { label: "已发布", value: "29" }
    ],
    themeButton: "切换日夜",
    localeButton: "中 / EN"
  },
  en: {
    appName: "ReWritter Console",
    appSubTitle: "Workflow Orchestration",
    nav: {
      create: "Create",
      tasks: "Tasks",
      review: "Review",
      chat: "Chat",
      creation: "Creation",
      materials: "Materials",
      settings: "Settings"
    },
    profileName: "Content Operations Lead",
    profileRole: "Administrator",
    signOut: "Sign Out",
    widgetTitle: "Status Widget",
    viewAll: "View all",
    emptyState: "No data yet",
    addData: "Add Data",
    secondaryWidgetTitle: "System Summary",
    quickStats: [
      { label: "Tasks Today", value: "18" },
      { label: "Pending", value: "5" },
      { label: "Published", value: "29" }
    ],
    themeButton: "Toggle Theme",
    localeButton: "ZH / EN"
  }
} as const;

export default function Layout() {
  const [locale, setLocale] = useState<Locale>("zh");
  const [theme, setTheme] = useState<ThemeMode>("dark");
  const [isLoading, setIsLoading] = useState(true);
  const [preferencesLoaded, setPreferencesLoaded] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const copy = useMemo(() => copyMap[locale], [locale]);
  const isSettingsRoute = location.pathname.startsWith("/settings");
  const currentModule = useMemo(() => {
    if (location.pathname.startsWith("/settings")) {
      return copy.nav.settings;
    }
    if (location.pathname.startsWith("/tasks")) {
      return copy.nav.tasks;
    }
    if (location.pathname.startsWith("/review")) {
      return copy.nav.review;
    }
    if (location.pathname.startsWith("/chat")) {
      return copy.nav.chat;
    }
    if (location.pathname.startsWith("/creation")) {
      return copy.nav.creation;
    }
    if (location.pathname.startsWith("/materials")) {
      return copy.nav.materials;
    }
    return copy.nav.create;
  }, [copy.nav.chat, copy.nav.create, copy.nav.creation, copy.nav.materials, copy.nav.review, copy.nav.settings, copy.nav.tasks, location.pathname]);

  // 加载用户偏好
  useEffect(() => {
    async function loadUserPreferences() {
      try {
        setIsLoading(true);

        // 首先检查本地缓存
        const cached = getCachedPreferences();
        if (cached) {
          setTheme(cached.theme);
          setLocale(cached.locale);
          setPreferencesLoaded(true);
        }

        // 然后从服务器加载最新偏好
        const preferences = await getUserPreferences();
        cachePreferences(preferences);

        // 使用服务器返回的偏好（可能会覆盖缓存）
        setTheme(preferences.theme);
        setLocale(preferences.locale);
        setPreferencesLoaded(true);

      } catch (error) {
        console.error("加载用户偏好失败:", error);
        // 使用默认设置
        setPreferencesLoaded(true);
      } finally {
        setIsLoading(false);
      }
    }

    loadUserPreferences();
  }, []);

  // 保存用户偏好（当主题或语言变化时）
  useEffect(() => {
    if (!preferencesLoaded) return;

    async function savePreferences() {
      try {
        await updateUserPreferences({
          theme,
          locale,
        });
        // 更新缓存
        const currentPrefs = await getUserPreferences();
        cachePreferences(currentPrefs);
      } catch (error) {
        console.error("保存用户偏好失败:", error);
      }
    }

    // 防抖保存，避免频繁请求
    const timeoutId = setTimeout(savePreferences, 500);
    return () => clearTimeout(timeoutId);
  }, [theme, locale, preferencesLoaded]);

  useEffect(() => {
    // 将主题状态同步到 body，便于全局变量切换深浅模式。
    document.body.dataset.theme = theme;
    document.documentElement.dataset.theme = theme;
    return () => {
      document.body.removeAttribute("data-theme");
      document.documentElement.removeAttribute("data-theme");
    };
  }, [theme]);

  const handleThemeToggle = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const handleLocaleToggle = () => {
    setLocale((prev) => (prev === "zh" ? "en" : "zh"));
  };

  const handleSignOut = () => {
    clearAuth();
    clearCachedPreferences();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen px-3 pb-3 pt-3 md:px-4 md:pb-4 md:pt-4">
      <div className="top-viewport-mask" aria-hidden="true" />
      <div className="top-header-mask" aria-hidden="true" />

      <div className="flex flex-col gap-3 md:gap-4">
        <header
          className="panel header-panel sticky top-3 z-40 flex min-h-[72px] items-center justify-between gap-3 rounded-3xl px-4 py-3 md:top-4 md:px-5"
        >
        <div className="flex min-w-0 items-center gap-3 md:gap-4">
          <Link to="/create" className="flex items-center gap-3">
            <span className="hero-gradient inline-flex h-10 w-10 items-center justify-center rounded-xl text-slate-950 shadow-lg shadow-cyan-900/25">
              <Sparkles className="h-5 w-5" />
            </span>
            <span className="hidden sm:block">
              <span className="block text-base font-semibold leading-none text-[hsl(var(--foreground))]">{copy.appName}</span>
              <span className="mt-1 block text-xs text-slate-400">{copy.appSubTitle}</span>
            </span>
          </Link>

          <div className="h-8 w-px bg-white/10" />

          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-[hsl(var(--foreground))]">{currentModule}</p>
            <p className="truncate text-xs text-slate-400">Agent Workspace / {currentModule}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleThemeToggle}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-200 transition hover:bg-white/10"
          >
            {theme === "dark" ? <SunMedium className="h-4 w-4" /> : <MoonStar className="h-4 w-4" />}
            <span className="hidden md:inline">{copy.themeButton}</span>
          </button>

          <button
            type="button"
            onClick={handleLocaleToggle}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-200 transition hover:bg-white/10"
          >
            <Globe className="h-4 w-4" />
            <span className="hidden md:inline">{copy.localeButton}</span>
          </button>
        </div>
        </header>

        <div
          className={[
            "grid w-full items-start gap-3 md:gap-4",
            isSettingsRoute ? "lg:grid-cols-[260px_1fr]" : "lg:grid-cols-[260px_1fr] xl:grid-cols-[260px_1fr_300px]"
          ].join(" ")}
        >
          <aside
            className="panel hidden rounded-3xl p-4 lg:sticky lg:top-[104px] lg:flex lg:h-[calc(100vh-120px)] lg:flex-col lg:overflow-hidden"
          >
          <nav className="flex-1 space-y-2 overflow-y-auto pr-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    [
                      "flex items-center gap-3 rounded-xl border px-3 py-3 text-sm font-medium transition",
                      isActive
                        ? theme === "dark"
                          ? "border-cyan-300/70 bg-cyan-400/20 text-cyan-100 shadow-lg shadow-cyan-800/25"
                          : "border-sky-500/55 bg-sky-100 text-slate-900 shadow-md shadow-sky-300/45"
                        : theme === "dark"
                          ? "border-transparent text-slate-300 hover:border-white/10 hover:bg-white/5 hover:text-white"
                          : "border-transparent text-slate-700 hover:border-slate-300 hover:bg-slate-100 hover:text-slate-900"
                    ].join(" ")
                  }
                >
                  <Icon className="h-4 w-4" />
                  {copy.nav[item.labelKey]}
                </NavLink>
              );
            })}
          </nav>

          <div className="mt-4 shrink-0 space-y-3 border-t border-white/10 pt-4">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
              <div className="flex items-center gap-3">
                <UserCircle2 className="h-9 w-9 text-cyan-200" />
                <div>
                  <p className="text-sm font-medium text-[hsl(var(--foreground))]">{copy.profileName}</p>
                  <p className="text-xs text-slate-400">{copy.profileRole}</p>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={handleSignOut}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 transition hover:bg-white/10"
            >
              <LogOut className="h-4 w-4" />
              {copy.signOut}
            </button>
          </div>
          </aside>

          <main className="panel rounded-3xl p-4 md:p-6">
            <Outlet context={{ locale }} />
          </main>

          {!isSettingsRoute && (
            <aside className="panel hidden rounded-3xl p-4 xl:sticky xl:top-[104px] xl:flex xl:h-[calc(100vh-120px)] xl:flex-col xl:overflow-y-auto">
              <StatusWidget />
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}
