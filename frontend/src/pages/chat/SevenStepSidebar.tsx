import { useMemo, useState } from "react";
import { Bot, Check, FileText, Image, ListChecks, PenLine, Sparkles } from "lucide-react";

import {
  confirmSevenStepOutline,
  confirmSevenStepTitle,
  createSevenStepFlow,
  type SevenStepFlow,
  type SevenStepAgentTrace,
  type SevenStepOutlineSection,
} from "../../lib/writingFlow";

interface SevenStepSidebarProps {
  locale: "zh" | "en";
  mode?: "sidebar" | "page";
}

function getSteps(locale: "zh" | "en"): string[] {
  if (locale === "zh") {
    return [
      "人提供题目和偏好",
      "Agent-1 标题策划",
      "人确认标题",
      "Agent-2 大纲生成",
      "人修订并确认大纲",
      "Agent-3 正文生成 + Agent-4 配图规划",
      "Agent-5 图文合成交付",
    ];
  }

  return [
    "Human provides topic and preferences",
    "Agent-1 title planner",
    "Human confirms title",
    "Agent-2 outline planner",
    "Human revises and confirms outline",
    "Agent-3 draft writer + Agent-4 image planner",
    "Agent-5 final merger and delivery",
  ];
}

function formatTraceTime(unixSeconds: number): string {
  if (!unixSeconds) {
    return "--:--:--";
  }
  return new Date(unixSeconds * 1000).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function normalizeOutline(outline: SevenStepOutlineSection[]): SevenStepOutlineSection[] {
  return outline.map((item, index) => ({
    section: index + 1,
    title: item.title,
    points: item.points,
  }));
}

export default function SevenStepSidebar({ locale, mode = "sidebar" }: SevenStepSidebarProps) {
  const [topic, setTopic] = useState("");
  const [preferences, setPreferences] = useState("");
  const [style, setStyle] = useState("");

  const [flow, setFlow] = useState<SevenStepFlow | null>(null);
  const [selectedTitleIndex, setSelectedTitleIndex] = useState<number>(0);
  const [editableOutline, setEditableOutline] = useState<SevenStepOutlineSection[]>([]);

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const copy = useMemo(
    () =>
      locale === "zh"
        ? {
            title: "创作流程",
            desc: "基于多 Agent 编排，完成从选题到交付的七步创作链路。",
            topic: "选题",
            preferences: "偏好",
            style: "风格",
            start: "开始七步流程",
            confirmTitle: "确认标题",
            confirmOutline: "确认大纲并生成成品",
            chooseTitle: "标题候选",
            outline: "大纲编辑",
            content: "正文草稿",
            imagePlan: "配图占位计划",
            final: "合成结果",
            traceTitle: "Agent 执行轨迹",
            optional: "可选",
            running: "处理中...",
            restart: "重新开始",
          }
        : {
            title: "Creation Flow",
            desc: "A multi-agent 7-step pipeline from topic to final delivery.",
            topic: "Topic",
            preferences: "Preferences",
            style: "Style",
            start: "Start 7-step flow",
            confirmTitle: "Confirm title",
            confirmOutline: "Confirm outline and generate",
            chooseTitle: "Title candidates",
            outline: "Outline",
            content: "Draft",
            imagePlan: "Image placeholders",
            final: "Final output",
            traceTitle: "Agent Trace",
            optional: "Optional",
            running: "Processing...",
            restart: "Restart",
          },
    [locale],
  );

  const steps = useMemo(() => getSteps(locale), [locale]);

  const currentStep = flow?.current_step ?? 1;
  const containerClass = mode === "page" ? "space-y-4" : "mt-3 space-y-3 overflow-y-auto pr-1";

  const canConfirmOutline = editableOutline.length > 0 && editableOutline.every((section) => section.title.trim());

  const onStart = async () => {
    if (!topic.trim() || loading) {
      return;
    }
    setLoading(true);
    setErrorMessage("");
    try {
      const created = await createSevenStepFlow({
        topic: topic.trim(),
        preferences: preferences.trim(),
        style: style.trim(),
      });
      setFlow(created);
      setSelectedTitleIndex(0);
      setEditableOutline(created.outline ?? []);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "创建失败");
    } finally {
      setLoading(false);
    }
  };

  const onConfirmTitle = async () => {
    if (!flow || loading) {
      return;
    }
    const selected = flow.title_options[selectedTitleIndex];
    if (!selected) {
      return;
    }

    setLoading(true);
    setErrorMessage("");
    try {
      const updated = await confirmSevenStepTitle({
        flowId: flow.flow_id,
        mainTitle: selected.main_title,
        subTitle: selected.sub_title,
      });
      setFlow(updated);
      setEditableOutline(updated.outline ?? []);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "确认标题失败");
    } finally {
      setLoading(false);
    }
  };

  const onConfirmOutline = async () => {
    if (!flow || loading || !canConfirmOutline) {
      return;
    }

    setLoading(true);
    setErrorMessage("");
    try {
      const updated = await confirmSevenStepOutline({
        flowId: flow.flow_id,
        outline: normalizeOutline(editableOutline),
      });
      setFlow(updated);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "确认大纲失败");
    } finally {
      setLoading(false);
    }
  };

  const onUpdateOutlineTitle = (index: number, value: string) => {
    setEditableOutline((prev) => prev.map((item, i) => (i === index ? { ...item, title: value } : item)));
  };

  const onUpdateOutlinePoints = (index: number, value: string) => {
    const points = value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
    setEditableOutline((prev) => prev.map((item, i) => (i === index ? { ...item, points } : item)));
  };

  const onRestart = () => {
    setFlow(null);
    setSelectedTitleIndex(0);
    setEditableOutline([]);
    setErrorMessage("");
  };

  const renderTrace = (trace: SevenStepAgentTrace) => (
    <div key={`${trace.agent_id}_${trace.started_at}`} className="rounded-xl border border-white/10 bg-black/20 p-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-slate-100">
          S{trace.stage} · {trace.agent_name}
        </p>
        <span className="rounded-full border border-cyan-300/30 bg-cyan-300/10 px-2 py-0.5 text-[10px] text-cyan-200">
          {trace.status}
        </span>
      </div>
      <p className="mt-1 text-[11px] leading-5 text-slate-300">{trace.summary}</p>
      <p className="mt-1 text-[10px] text-slate-500">
        {formatTraceTime(trace.started_at)} - {formatTraceTime(trace.finished_at)}
      </p>
    </div>
  );

  return (
    <div className={containerClass}>
      <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
        <h3 className="text-sm font-semibold text-[hsl(var(--foreground))]">{copy.title}</h3>
        <p className="mt-1 text-xs text-slate-400">{copy.desc}</p>
      </div>

      <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
        <ol className="space-y-2">
          {steps.map((item, index) => {
            const stepNo = index + 1;
            const done = currentStep > stepNo;
            const active = currentStep === stepNo;
            return (
              <li key={item} className="flex items-start gap-2 text-xs">
                <span
                  className={[
                    "mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px]",
                    done
                      ? "border-cyan-300/60 bg-cyan-300/20 text-cyan-100"
                      : active
                        ? "border-emerald-300/60 bg-emerald-300/20 text-emerald-100"
                        : "border-white/20 bg-white/5 text-slate-300",
                  ].join(" ")}
                >
                  {done ? <Check className="h-3 w-3" /> : stepNo}
                </span>
                <span className={active ? "text-[hsl(var(--foreground))]" : "text-slate-400"}>{item}</span>
              </li>
            );
          })}
        </ol>
      </div>

      {!flow ? (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
          <div className="grid gap-2">
            <label className="grid gap-1 text-xs text-slate-300">
              {copy.topic}
              <input
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
              />
            </label>
            <label className="grid gap-1 text-xs text-slate-300">
              {copy.preferences} ({copy.optional})
              <textarea
                rows={3}
                value={preferences}
                onChange={(event) => setPreferences(event.target.value)}
                className="resize-none rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
              />
            </label>
            <label className="grid gap-1 text-xs text-slate-300">
              {copy.style} ({copy.optional})
              <input
                value={style}
                onChange={(event) => setStyle(event.target.value)}
                className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
              />
            </label>
            <button
              type="button"
              onClick={() => void onStart()}
              disabled={!topic.trim() || loading}
              className="mt-1 inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-500 px-3 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:opacity-60"
            >
              <Sparkles className="h-4 w-4" />
              {loading ? copy.running : copy.start}
            </button>
          </div>
        </div>
      ) : null}

      {flow && flow.title_options.length > 0 && flow.current_step <= 4 ? (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
          <p className="mb-2 inline-flex items-center gap-2 text-xs font-medium text-slate-200">
            <PenLine className="h-3.5 w-3.5 text-cyan-200" />
            {copy.chooseTitle}
          </p>
          <div className="space-y-2">
            {flow.title_options.map((title, index) => (
              <label key={`${title.main_title}_${index}`} className="block cursor-pointer rounded-xl border border-white/10 bg-black/20 p-2">
                <div className="flex items-start gap-2">
                  <input
                    type="radio"
                    checked={selectedTitleIndex === index}
                    onChange={() => setSelectedTitleIndex(index)}
                    className="mt-1 h-4 w-4 accent-cyan-400"
                  />
                  <div>
                    <p className="text-sm text-[hsl(var(--foreground))]">{title.main_title}</p>
                    {title.sub_title ? <p className="mt-1 text-xs text-slate-400">{title.sub_title}</p> : null}
                  </div>
                </div>
              </label>
            ))}
          </div>
          <button
            type="button"
            onClick={() => void onConfirmTitle()}
            disabled={loading}
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-cyan-300/30 bg-cyan-400/15 px-3 py-2 text-sm text-cyan-100 transition hover:bg-cyan-400/25 disabled:opacity-60"
          >
            <Check className="h-4 w-4" />
            {loading ? copy.running : copy.confirmTitle}
          </button>
        </div>
      ) : null}

      {flow && editableOutline.length > 0 && flow.status === "OUTLINE_READY" ? (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
          <p className="mb-2 inline-flex items-center gap-2 text-xs font-medium text-slate-200">
            <ListChecks className="h-3.5 w-3.5 text-cyan-200" />
            {copy.outline}
          </p>
          <div className="space-y-3">
            {editableOutline.map((section, index) => (
              <div key={`${section.section}_${index}`} className="rounded-xl border border-white/10 bg-black/20 p-2">
                <input
                  value={section.title}
                  onChange={(event) => onUpdateOutlineTitle(index, event.target.value)}
                  className="w-full rounded-lg border border-white/10 bg-black/30 px-2 py-1.5 text-sm text-[hsl(var(--foreground))] outline-none"
                />
                <textarea
                  rows={3}
                  value={section.points.join("\n")}
                  onChange={(event) => onUpdateOutlinePoints(index, event.target.value)}
                  className="mt-2 w-full resize-none rounded-lg border border-white/10 bg-black/30 px-2 py-1.5 text-xs text-slate-200 outline-none"
                />
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={() => void onConfirmOutline()}
            disabled={!canConfirmOutline || loading}
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 px-3 py-2 text-sm font-medium text-slate-950 transition hover:bg-emerald-400 disabled:opacity-60"
          >
            <FileText className="h-4 w-4" />
            {loading ? copy.running : copy.confirmOutline}
          </button>
        </div>
      ) : null}

      {flow?.status === "COMPLETED" ? (
        <>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
            <p className="mb-2 inline-flex items-center gap-2 text-xs font-medium text-slate-200">
              <FileText className="h-3.5 w-3.5 text-cyan-200" />
              {copy.content}
            </p>
            <p className="line-clamp-6 whitespace-pre-wrap text-xs leading-6 text-slate-300">{flow.content}</p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
            <p className="mb-2 inline-flex items-center gap-2 text-xs font-medium text-slate-200">
              <Image className="h-3.5 w-3.5 text-cyan-200" />
              {copy.imagePlan}
            </p>
            <div className="space-y-2">
              {flow.image_plan.map((item) => (
                <div key={item.placeholder_id} className="rounded-xl border border-white/10 bg-black/20 px-2 py-1.5 text-xs text-slate-300">
                  <p className="font-medium text-slate-100">[{item.placeholder_id}] {item.section_title}</p>
                  <p className="mt-1">{item.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
            <p className="mb-2 inline-flex items-center gap-2 text-xs font-medium text-slate-200">
              <Sparkles className="h-3.5 w-3.5 text-cyan-200" />
              {copy.final}
            </p>
            <p className="line-clamp-6 whitespace-pre-wrap text-xs leading-6 text-slate-300">{flow.final_markdown}</p>
          </div>

          <button
            type="button"
            onClick={onRestart}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/5 px-3 py-2 text-sm text-slate-200 transition hover:bg-white/10"
          >
            {copy.restart}
          </button>
        </>
      ) : null}

      {flow?.agent_traces?.length ? (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
          <p className="mb-2 inline-flex items-center gap-2 text-xs font-medium text-slate-200">
            <Bot className="h-3.5 w-3.5 text-cyan-200" />
            {copy.traceTitle}
          </p>
          <div className="space-y-2">{flow.agent_traces.map(renderTrace)}</div>
        </div>
      ) : null}

      {errorMessage ? (
        <p className="rounded-xl border border-rose-300/40 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">{errorMessage}</p>
      ) : null}
    </div>
  );
}
