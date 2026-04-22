import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  BrainCircuit,
  ChevronDown,
  Database,
  Edit3,
  LoaderCircle,
  MessageSquarePlus,
  SendHorizonal,
  Sparkles,
  Trash2,
  UserRound,
} from "lucide-react";
import { useOutletContext } from "react-router-dom";

import type { LayoutOutletContext } from "../Layout";
import MarkdownStream from "../components/MarkdownStream";
import { listMaterialGroups, type MaterialGroup } from "../lib/materials";
import {
  createChatSession,
  deleteChatSession,
  listChatSessions,
  listSessionMessages,
  renameChatSession,
  streamChatMessage,
} from "../lib/chat";
import type { ChatMessage, ChatSession, ChatStreamEvent } from "../lib/chat";

interface CopyPack {
  title: string;
  desc: string;
  newChat: string;
  model: string;
  thinking: string;
  thinkingHint: string;
  ragEnable: string;
  ragGroup: string;
  ragHint: string;
  ragAllGroups: string;
  ragSearchType: string;
  ragSearchTypeHint: string;
  ragAlpha: string;
  ragCandidatePool: string;
  ragStrategyOptions: Array<{ label: string; value: "vector" | "hybrid" | "keyword" }>;
  inputPlaceholder: string;
  send: string;
  loading: string;
  emptyTitle: string;
  emptyDesc: string;
  sessionTitle: string;
  noSession: string;
  syncError: string;
  sendError: string;
  me: string;
  assistant: string;
  thinkingLabel: string;
  thinkingFold: string;
  thinkingExpand: string;
  thinkingInProgress: string;
  thinkingElapsed: string;
  rename: string;
  remove: string;
  renamePrompt: string;
  renameEmpty: string;
  removeConfirm: string;
  modalCancel: string;
  modalConfirm: string;
  modelOptions: Array<{ label: string; value: string }>;
}

interface SessionActionModalState {
  action: "rename" | "delete";
  session: ChatSession;
  titleInput: string;
  loading: boolean;
}

const THINKING_COLLAPSE_KEY = "rewritter.chat.thinking_collapsed";
const RAG_SETTINGS_KEY = "rewritter.chat.rag_settings";

interface RagSettings {
  searchType: "vector" | "hybrid" | "keyword";
  alpha: number;
  candidatePool: number;
}

function formatDurationMs(durationMs: number): string {
  const totalSeconds = Math.max(0, Math.floor(durationMs / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes > 0) {
    return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
  }
  return `${seconds}s`;
}

function readThinkingCollapseMap(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(THINKING_COLLAPSE_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as Record<string, boolean>;
    return parsed ?? {};
  } catch {
    return {};
  }
}

function writeThinkingCollapseMap(data: Record<string, boolean>): void {
  localStorage.setItem(THINKING_COLLAPSE_KEY, JSON.stringify(data));
}

function readRagSettings(): RagSettings {
  try {
    const raw = localStorage.getItem(RAG_SETTINGS_KEY);
    if (!raw) {
      return { searchType: "vector", alpha: 0.6, candidatePool: 12 };
    }
    const parsed = JSON.parse(raw) as Partial<RagSettings>;
    const searchType = parsed.searchType === "hybrid" || parsed.searchType === "keyword" ? parsed.searchType : "vector";
    const alphaRaw = Number(parsed.alpha);
    const candidatePoolRaw = Number(parsed.candidatePool);
    return {
      searchType,
      alpha: Number.isFinite(alphaRaw) ? Math.min(1, Math.max(0, alphaRaw)) : 0.6,
      candidatePool: Number.isFinite(candidatePoolRaw) ? Math.min(100, Math.max(1, Math.floor(candidatePoolRaw))) : 12,
    };
  } catch {
    return { searchType: "vector", alpha: 0.6, candidatePool: 12 };
  }
}

function writeRagSettings(settings: RagSettings): void {
  localStorage.setItem(RAG_SETTINGS_KEY, JSON.stringify(settings));
}

function formatTime(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ChatPage() {
  const { locale } = useOutletContext<LayoutOutletContext>();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [model, setModel] = useState<string>("deepseek-chat");
  const [enableThinking, setEnableThinking] = useState<boolean>(false);
  const [useRag, setUseRag] = useState<boolean>(false);
  const [ragGroupId, setRagGroupId] = useState<string>("");
  const [ragSearchType, setRagSearchType] = useState<"vector" | "hybrid" | "keyword">("vector");
  const [ragAlpha, setRagAlpha] = useState<number>(0.6);
  const [ragCandidatePool, setRagCandidatePool] = useState<number>(12);
  const [materialGroups, setMaterialGroups] = useState<MaterialGroup[]>([]);
  const [input, setInput] = useState<string>("");
  const [loadingSessions, setLoadingSessions] = useState<boolean>(true);
  const [loadingMessages, setLoadingMessages] = useState<boolean>(false);
  const [sending, setSending] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [thinkingCollapsed, setThinkingCollapsed] = useState<Record<string, boolean>>({});
  const [streamingAssistantId, setStreamingAssistantId] = useState<string>("");
  const [streamStartedAt, setStreamStartedAt] = useState<number | null>(null);
  const [streamTick, setStreamTick] = useState<number>(0);
  const [sessionActionModal, setSessionActionModal] = useState<SessionActionModalState | null>(null);
  const chatScrollRef = useRef<HTMLDivElement | null>(null);

  const copy = useMemo<CopyPack>(
    () =>
      locale === "zh"
        ? {
            title: "AI 对话实验室",
            desc: "测试模型可用性，切换模型与思考模式，历史会话自动持久化。",
            newChat: "新建对话",
            model: "模型",
            thinking: "思考模式",
            thinkingHint: "开启后在默认模型下自动切到 deepseek-reasoner",
            ragEnable: "启用素材检索",
            ragGroup: "素材组",
            ragHint: "启用后会先从素材组检索，再把命中片段注入对话上下文。",
            ragAllGroups: "全部素材组",
            ragSearchType: "检索策略",
            ragSearchTypeHint: "vector=仅向量；hybrid=向量+关键词；keyword=仅关键词。",
            ragAlpha: "混合权重(向量)",
            ragCandidatePool: "候选池",
            ragStrategyOptions: [
              { label: "仅向量 (Vector)", value: "vector" },
              { label: "混合检索 (Hybrid)", value: "hybrid" },
              { label: "仅关键词 (Keyword)", value: "keyword" },
            ],
            inputPlaceholder: "输入你的问题，Enter 发送，Shift + Enter 换行",
            send: "发送",
            loading: "AI 正在生成回复...",
            emptyTitle: "开始第一条消息",
            emptyDesc: "左侧可以创建多个会话，每个会话会保存历史记录。",
            sessionTitle: "历史会话",
            noSession: "暂无会话",
            syncError: "加载会话失败",
            sendError: "发送失败，请稍后重试",
            me: "我",
            assistant: "AI",
            thinkingLabel: "深度思考",
            thinkingFold: "收起思考",
            thinkingExpand: "展开思考",
            thinkingInProgress: "思考中...",
            thinkingElapsed: "思考耗时",
            rename: "重命名",
            remove: "删除",
            renamePrompt: "请输入新的会话名称",
            renameEmpty: "会话名称不能为空",
            removeConfirm: "确认删除该历史会话吗？删除后不可恢复。",
            modalCancel: "取消",
            modalConfirm: "确认",
            modelOptions: [
              { label: "DeepSeek Chat", value: "deepseek-chat" },
              { label: "DeepSeek Reasoner", value: "deepseek-reasoner" },
            ],
          }
        : {
            title: "AI Chat Lab",
            desc: "Validate model availability with model switching and thinking mode. History is persisted.",
            newChat: "New Chat",
            model: "Model",
            thinking: "Thinking",
            thinkingHint: "When enabled on default model, backend upgrades to deepseek-reasoner",
            ragEnable: "Use RAG",
            ragGroup: "Material Group",
            ragHint: "When enabled, chat retrieves from materials first and injects context.",
            ragAllGroups: "All Groups",
            ragSearchType: "Search Strategy",
            ragSearchTypeHint: "vector=vector only; hybrid=vector+keyword; keyword=keyword only.",
            ragAlpha: "Hybrid Weight (Vector)",
            ragCandidatePool: "Candidate Pool",
            ragStrategyOptions: [
              { label: "Vector Only", value: "vector" },
              { label: "Hybrid", value: "hybrid" },
              { label: "Keyword Only", value: "keyword" },
            ],
            inputPlaceholder: "Type your message, Enter to send, Shift + Enter for newline",
            send: "Send",
            loading: "AI is generating...",
            emptyTitle: "Start your first message",
            emptyDesc: "Create multiple sessions on the left, each with persisted history.",
            sessionTitle: "Session History",
            noSession: "No sessions yet",
            syncError: "Failed to load sessions",
            sendError: "Failed to send message",
            me: "Me",
            assistant: "AI",
            thinkingLabel: "Thinking",
            thinkingFold: "Hide thinking",
            thinkingExpand: "Show thinking",
            thinkingInProgress: "Thinking...",
            thinkingElapsed: "Thinking time",
            rename: "Rename",
            remove: "Delete",
            renamePrompt: "Enter new session title",
            renameEmpty: "Session title cannot be empty",
            removeConfirm: "Delete this session permanently? This cannot be undone.",
            modalCancel: "Cancel",
            modalConfirm: "Confirm",
            modelOptions: [
              { label: "DeepSeek Chat", value: "deepseek-chat" },
              { label: "DeepSeek Reasoner", value: "deepseek-reasoner" },
            ],
          },
    [locale],
  );

  useEffect(() => {
    setThinkingCollapsed(readThinkingCollapseMap());
    const ragSettings = readRagSettings();
    setRagSearchType(ragSettings.searchType);
    setRagAlpha(ragSettings.alpha);
    setRagCandidatePool(ragSettings.candidatePool);
  }, []);

  useEffect(() => {
    writeThinkingCollapseMap(thinkingCollapsed);
  }, [thinkingCollapsed]);

  useEffect(() => {
    writeRagSettings({
      searchType: ragSearchType,
      alpha: ragAlpha,
      candidatePool: ragCandidatePool,
    });
  }, [ragSearchType, ragAlpha, ragCandidatePool]);

  useEffect(() => {
    const loadMaterialGroups = async () => {
      try {
        const groups = await listMaterialGroups();
        setMaterialGroups(groups);
        if (groups.length > 0 && !ragGroupId) {
          setRagGroupId(groups[0].group_id);
        }
      } catch {
        // Keep chat usable when materials are not ready.
      }
    };

    void loadMaterialGroups();
  }, []);

  useEffect(() => {
    const fetchSessions = async () => {
      setLoadingSessions(true);
      setErrorMessage("");
      try {
        const data = await listChatSessions();
        setSessions(data);
        if (data.length > 0) {
          setActiveSessionId((prev) => prev || data[0].session_id);
          setModel(data[0].model || "deepseek-chat");
          setEnableThinking(data[0].enable_thinking);
        }
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : copy.syncError);
      } finally {
        setLoadingSessions(false);
      }
    };

    void fetchSessions();
  }, [copy.syncError]);

  useEffect(() => {
    const loadMessages = async () => {
      if (!activeSessionId) {
        setMessages([]);
        return;
      }
      setLoadingMessages(true);
      setErrorMessage("");
      try {
        const data = await listSessionMessages(activeSessionId);
        setMessages(data);
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : copy.syncError);
      } finally {
        setLoadingMessages(false);
      }
    };

    void loadMessages();
  }, [activeSessionId, copy.syncError]);

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages, loadingMessages, sending]);

  useEffect(() => {
    if (!streamingAssistantId) {
      return;
    }
    const timer = window.setInterval(() => {
      setStreamTick((prev) => prev + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [streamingAssistantId]);

  const activeSession = useMemo(
    () => sessions.find((item) => item.session_id === activeSessionId) ?? null,
    [activeSessionId, sessions],
  );
  const streamingElapsedMs = streamStartedAt ? streamTick * 1000 : 0;

  const onCreateSession = async () => {
    setErrorMessage("");
    try {
      const created = await createChatSession();
      setSessions((prev) => [created, ...prev]);
      setActiveSessionId(created.session_id);
      setModel(created.model);
      setEnableThinking(created.enable_thinking);
      setMessages([]);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : copy.syncError);
    }
  };

  const onPickSession = (session: ChatSession) => {
    setActiveSessionId(session.session_id);
    setModel(session.model || "deepseek-chat");
    setEnableThinking(session.enable_thinking);
  };

  const openRenameModal = (session: ChatSession) => {
    setSessionActionModal({
      action: "rename",
      session,
      titleInput: session.title,
      loading: false,
    });
  };

  const openDeleteModal = (session: ChatSession) => {
    setSessionActionModal({
      action: "delete",
      session,
      titleInput: session.title,
      loading: false,
    });
  };

  const runSessionAction = async () => {
    if (!sessionActionModal) {
      return;
    }

    setSessionActionModal((prev) => (prev ? { ...prev, loading: true } : prev));
    const current = sessionActionModal;

    try {
      if (current.action === "rename") {
        const normalizedTitle = current.titleInput.trim();
        if (!normalizedTitle) {
          setErrorMessage(copy.renameEmpty);
          setSessionActionModal((prev) => (prev ? { ...prev, loading: false } : prev));
          return;
        }
        const renamed = await renameChatSession(current.session.session_id, normalizedTitle);
        setSessions((prev) => prev.map((item) => (item.session_id === renamed.session_id ? renamed : item)));
      }

      if (current.action === "delete") {
        await deleteChatSession(current.session.session_id);
        setSessions((prev) => prev.filter((item) => item.session_id !== current.session.session_id));
        if (activeSessionId === current.session.session_id) {
          setMessages([]);
          setActiveSessionId((prev) => {
            if (prev !== current.session.session_id) {
              return prev;
            }
            const nextSession = sessions.find((item) => item.session_id !== current.session.session_id);
            return nextSession?.session_id ?? "";
          });
        }
      }

      setSessionActionModal(null);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : copy.syncError);
      setSessionActionModal((prev) => (prev ? { ...prev, loading: false } : prev));
    }
  };

  const toggleThinkingCollapsed = (messageId: string) => {
    setThinkingCollapsed((prev) => ({
      ...prev,
      [messageId]: !(prev[messageId] ?? true),
    }));
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!input.trim() || sending) {
      return;
    }

    let targetSessionId = activeSessionId;
    if (!targetSessionId) {
      try {
        const created = await createChatSession();
        setSessions((prev) => [created, ...prev]);
        setActiveSessionId(created.session_id);
        targetSessionId = created.session_id;
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : copy.syncError);
        return;
      }
    }

    setSending(true);
    setErrorMessage("");
    const draft = input;
    setInput("");

    const now = Math.floor(Date.now() / 1000);
    const userMessageId = `local_user_${Date.now()}`;
    const assistantMessageId = `local_assistant_${Date.now()}`;

    const optimisticUserMessage: ChatMessage = {
      message_id: userMessageId,
      role: "user",
      content: draft,
      created_at: now,
    };
    const optimisticAssistantMessage: ChatMessage = {
      message_id: assistantMessageId,
      role: "assistant",
      content: "",
      thinking_content: "",
      model,
      enable_thinking: enableThinking,
      created_at: now,
    };

    setMessages((prev) => [...prev, optimisticUserMessage, optimisticAssistantMessage]);
    setThinkingCollapsed((prev) => ({ ...prev, [assistantMessageId]: false }));
    setStreamingAssistantId(assistantMessageId);
    setStreamStartedAt(Date.now());
    setStreamTick(0);

    try {
      let streamErrorMessage = "";
      await streamChatMessage(
        {
          sessionId: targetSessionId,
          content: draft,
          model,
          enableThinking,
          useRag,
          ragGroupId: ragGroupId || undefined,
          ragTopK: 6,
          ragSearchType,
          ragAlpha,
          ragCandidatePool,
        },
        (eventPayload: ChatStreamEvent) => {
          if (eventPayload.type === "thinking_delta") {
            setMessages((prev) =>
              prev.map((item) =>
                item.message_id === assistantMessageId
                  ? { ...item, thinking_content: `${item.thinking_content ?? ""}${eventPayload.delta}` }
                  : item,
              ),
            );
            return;
          }

          if (eventPayload.type === "content_delta") {
            setMessages((prev) =>
              prev.map((item) =>
                item.message_id === assistantMessageId ? { ...item, content: `${item.content}${eventPayload.delta}` } : item,
              ),
            );
            return;
          }

          if (eventPayload.type === "error") {
            streamErrorMessage = eventPayload.message || copy.sendError;
            return;
          }

          if (eventPayload.type === "done") {
            setMessages((prev) =>
              prev.map((item) => (item.message_id === assistantMessageId ? eventPayload.assistant_message : item)),
            );
            setSessions((prev) => {
              const rest = prev.filter((item) => item.session_id !== eventPayload.session.session_id);
              return [eventPayload.session, ...rest];
            });
            setModel(eventPayload.session.model);
            setEnableThinking(eventPayload.session.enable_thinking);
            setActiveSessionId(eventPayload.session.session_id);
          }
        },
      );

      if (streamErrorMessage) {
        throw new Error(streamErrorMessage);
      }
    } catch (error) {
      setMessages((prev) => prev.filter((item) => item.message_id !== assistantMessageId && item.message_id !== userMessageId));
      setErrorMessage(error instanceof Error ? error.message : copy.sendError);
      setInput(draft);
    } finally {
      setStreamingAssistantId("");
      setStreamStartedAt(null);
      setSending(false);
    }
  };

  return (
    <section className="chat-shell grid gap-4 xl:grid-cols-[280px_1fr]">
      <aside className="chat-sidebar rounded-3xl p-3 md:p-4">
        <header className="flex items-center justify-between gap-2 border-b border-white/10 pb-3">
          <div>
            <h2 className="text-base font-semibold text-[hsl(var(--foreground))]">{copy.sessionTitle}</h2>
            <p className="text-xs text-slate-400">{copy.desc}</p>
          </div>
          <button
            type="button"
            onClick={onCreateSession}
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-white/10 text-cyan-200 transition hover:bg-cyan-300/20"
            aria-label={copy.newChat}
            title={copy.newChat}
          >
            <MessageSquarePlus className="h-4 w-4" />
          </button>
        </header>

        <div className="mt-3 space-y-2 overflow-y-auto pr-1">
          {loadingSessions && <p className="text-sm text-slate-400">Loading...</p>}
          {!loadingSessions && sessions.length === 0 && <p className="text-sm text-slate-400">{copy.noSession}</p>}
          {sessions.map((session) => (
            <div
              key={session.session_id}
              className={[
                "w-full rounded-2xl border px-3 py-3 text-left transition",
                session.session_id === activeSessionId
                  ? "border-cyan-300/60 bg-cyan-400/15"
                  : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10",
              ].join(" ")}
            >
              <button type="button" onClick={() => onPickSession(session)} className="w-full text-left">
                <p className="truncate text-sm font-medium text-[hsl(var(--foreground))]">{session.title}</p>
                <p className="mt-1 truncate text-xs text-slate-400">{formatTime(session.updated_at)}</p>
              </button>

              <div className="mt-2 flex items-center justify-end gap-1">
                <button
                  type="button"
                  onClick={() => {
                    openRenameModal(session);
                  }}
                  className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-slate-300 transition hover:bg-white/10"
                >
                  <Edit3 className="h-3 w-3" />
                  {copy.rename}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    openDeleteModal(session);
                  }}
                  className="inline-flex items-center gap-1 rounded-lg border border-rose-300/30 bg-rose-500/10 px-2 py-1 text-[11px] text-rose-200 transition hover:bg-rose-500/20"
                >
                  <Trash2 className="h-3 w-3" />
                  {copy.remove}
                </button>
              </div>
            </div>
          ))}
        </div>
      </aside>

      <div className="chat-main rounded-3xl p-3 md:p-4">
        <header className="chat-toolbar rounded-2xl p-3 md:p-4">
          <div>
            <h1 className="text-xl font-semibold text-[hsl(var(--foreground))]">{copy.title}</h1>
            <p className="mt-1 text-xs text-slate-400">{activeSession?.title ?? copy.emptyTitle}</p>
          </div>

          <div className="flex flex-wrap items-end gap-2">
            <label className="grid min-w-[220px] flex-1 gap-1 text-xs text-slate-300">
              {copy.model}
              <select
                value={model}
                onChange={(event) => setModel(event.target.value)}
                className="rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-sm text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
              >
                {copy.modelOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="inline-flex h-10 items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-200">
              <input
                type="checkbox"
                checked={enableThinking}
                onChange={(event) => setEnableThinking(event.target.checked)}
                className="h-4 w-4 accent-cyan-400"
              />
              <BrainCircuit className="h-4 w-4 text-cyan-200" />
              <span>{copy.thinking}</span>
            </label>

            <label className="inline-flex h-10 items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-200">
              <input
                type="checkbox"
                checked={useRag}
                onChange={(event) => setUseRag(event.target.checked)}
                className="h-4 w-4 accent-cyan-400"
              />
              <Database className="h-4 w-4 text-cyan-200" />
              <span>{copy.ragEnable}</span>
            </label>
          </div>

          <div
            className={[
              "flex flex-wrap items-end gap-2 overflow-hidden transition-all duration-200",
              useRag ? "max-h-40 opacity-100" : "max-h-0 opacity-0 pointer-events-none",
            ].join(" ")}
          >
            <label className="grid min-w-[220px] flex-1 gap-1 text-xs text-slate-300">
                {copy.ragGroup}
                <select
                  value={ragGroupId}
                  onChange={(event) => setRagGroupId(event.target.value)}
                  className="rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-sm text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
                >
                  <option value="">{copy.ragAllGroups}</option>
                  {materialGroups.map((group) => (
                    <option key={group.group_id} value={group.group_id}>
                      {group.group_name}
                    </option>
                  ))}
                </select>
              </label>
            <label className="grid min-w-[220px] flex-1 gap-1 text-xs text-slate-300">
              {copy.ragSearchType}
              <select
                value={ragSearchType}
                onChange={(event) => setRagSearchType(event.target.value as "vector" | "hybrid" | "keyword")}
                className="rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-sm text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
              >
                {copy.ragStrategyOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid min-w-[180px] gap-1 text-xs text-slate-300">
              {copy.ragCandidatePool}
              <input
                type="number"
                value={ragCandidatePool}
                min={1}
                max={100}
                onChange={(event) => {
                  const value = Number(event.target.value);
                  if (!Number.isFinite(value)) {
                    return;
                  }
                  setRagCandidatePool(Math.max(1, Math.min(100, Math.floor(value))));
                }}
                className="rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-sm text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
              />
            </label>
            {ragSearchType === "hybrid" ? (
              <label className="grid min-w-[220px] flex-1 gap-1 text-xs text-slate-300">
                {copy.ragAlpha}
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={ragAlpha}
                  onChange={(event) => setRagAlpha(Number(event.target.value))}
                  className="accent-cyan-400"
                />
                <span className="text-[11px] text-slate-400">{ragAlpha.toFixed(2)}</span>
              </label>
            ) : null}
            <p className="min-w-[220px] flex-[2] text-[11px] text-slate-400">{copy.ragHint}</p>
            <p className="min-w-[220px] flex-[2] text-[11px] text-slate-400">{copy.ragSearchTypeHint}</p>
          </div>

          <p className="text-[11px] text-slate-400">{copy.thinkingHint}</p>
        </header>

        <div ref={chatScrollRef} className="chat-log mt-3 rounded-2xl p-3 md:p-4">
          {loadingMessages ? (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <LoaderCircle className="h-4 w-4 animate-spin" />
              Loading...
            </div>
          ) : null}

          {!loadingMessages && messages.length === 0 ? (
            <div className="chat-empty flex h-full flex-col items-center justify-center gap-2 text-center">
              <Sparkles className="h-8 w-8 text-cyan-300" />
              <p className="text-base font-medium text-[hsl(var(--foreground))]">{copy.emptyTitle}</p>
              <p className="max-w-md text-sm text-slate-400">{copy.emptyDesc}</p>
            </div>
          ) : null}

          <div className="space-y-4">
            {messages.map((message) => (
              <article
                key={message.message_id}
                className={[
                  "chat-bubble",
                  message.role === "user" ? "chat-bubble-user ml-auto" : "chat-bubble-assistant",
                ].join(" ")}
              >
                <header className="mb-1 flex items-center justify-between gap-2 text-xs text-slate-400">
                  <span className="inline-flex items-center gap-1">
                    {message.role === "user" ? <UserRound className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
                    {message.role === "user" ? copy.me : copy.assistant}
                  </span>
                  <span>{formatTime(message.created_at)}</span>
                </header>
                {message.role === "assistant" ? (
                  <MarkdownStream
                    content={message.content}
                    streaming={streamingAssistantId === message.message_id}
                    className="chat-response-text text-sm leading-7 text-[hsl(var(--foreground))]"
                  />
                ) : (
                  <p className="chat-response-text whitespace-pre-wrap text-sm leading-7 text-[hsl(var(--foreground))]">
                    {message.content}
                  </p>
                )}

                {message.role === "assistant" && message.thinking_content ? (
                  <div className="chat-thinking-panel mt-3 rounded-xl border border-white/10 bg-black/20 p-3">
                    <button
                      type="button"
                      onClick={() => toggleThinkingCollapsed(message.message_id)}
                      className="inline-flex items-center gap-1 text-xs font-medium text-cyan-200"
                    >
                      <ChevronDown
                        className={[
                          "h-3.5 w-3.5 transition-transform",
                          (thinkingCollapsed[message.message_id] ?? true) ? "-rotate-90" : "rotate-0",
                        ].join(" ")}
                      />
                      {copy.thinkingLabel}
                      {streamingAssistantId === message.message_id ? ` · ${copy.thinkingInProgress}` : ""}
                      {message.thinking_duration_ms ? ` · ${copy.thinkingElapsed} ${formatDurationMs(message.thinking_duration_ms)}` : ""}
                      {streamingAssistantId === message.message_id && streamStartedAt
                        ? ` · ${copy.thinkingElapsed} ${formatDurationMs(streamingElapsedMs)}`
                        : ""}
                      <span className="text-slate-400">
                        {(thinkingCollapsed[message.message_id] ?? true) ? copy.thinkingExpand : copy.thinkingFold}
                      </span>
                    </button>

                    {!(thinkingCollapsed[message.message_id] ?? true) ? (
                      <p className="chat-thinking-content mt-2 whitespace-pre-wrap text-xs leading-6 text-slate-300">{message.thinking_content}</p>
                    ) : null}
                  </div>
                ) : null}

                {message.model ? (
                  <p className="mt-2 text-[11px] text-slate-400">
                    {message.model}
                    {typeof message.enable_thinking === "boolean" ? ` · thinking=${message.enable_thinking}` : ""}
                  </p>
                ) : null}
              </article>
            ))}
          </div>

          {sending ? (
            <div className="mt-3 inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-300">
              <LoaderCircle className="h-4 w-4 animate-spin" />
              {copy.loading}
            </div>
          ) : null}
        </div>

        {errorMessage ? (
          <p className="mt-3 rounded-xl border border-rose-300/40 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">{errorMessage}</p>
        ) : null}

        {sessionActionModal ? (
          <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => !sessionActionModal.loading && setSessionActionModal(null)} />
            <div className="panel relative z-10 w-full max-w-md rounded-2xl p-5">
              <h3 className="text-lg font-semibold text-[hsl(var(--foreground))]">
                {sessionActionModal.action === "rename" ? copy.rename : copy.remove}
              </h3>

              {sessionActionModal.action === "rename" ? (
                <div className="mt-3 grid gap-2">
                  <label className="text-sm text-slate-300">{copy.renamePrompt}</label>
                  <input
                    value={sessionActionModal.titleInput}
                    onChange={(event) =>
                      setSessionActionModal((prev) =>
                        prev ? { ...prev, titleInput: event.target.value } : prev,
                      )
                    }
                    className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
                  />
                </div>
              ) : (
                <p className="mt-3 text-sm text-slate-300">{copy.removeConfirm}</p>
              )}

              <div className="mt-5 flex justify-end gap-2">
                <button
                  type="button"
                  disabled={sessionActionModal.loading}
                  onClick={() => setSessionActionModal(null)}
                  className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:bg-white/10 disabled:opacity-60"
                >
                  {copy.modalCancel}
                </button>
                <button
                  type="button"
                  disabled={sessionActionModal.loading}
                  onClick={() => {
                    void runSessionAction();
                  }}
                  className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:opacity-60"
                >
                  {sessionActionModal.loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
                  {copy.modalConfirm}
                </button>
              </div>
            </div>
          </div>
        ) : null}

        <form onSubmit={onSubmit} className="chat-composer mt-3 rounded-2xl p-3 md:p-4">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                const form = event.currentTarget.form;
                if (form) {
                  form.requestSubmit();
                }
              }
            }}
            rows={4}
            placeholder={copy.inputPlaceholder}
            className="w-full resize-none rounded-xl border border-white/15 bg-black/20 px-3 py-3 text-sm leading-6 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
          />

          <div className="mt-3 flex justify-end">
            <button
              type="submit"
              disabled={!input.trim() || sending}
              className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <SendHorizonal className="h-4 w-4" />
              {copy.send}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
