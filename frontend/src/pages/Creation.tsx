import { Bot, FileSearch, GitBranch, ListChecks, PenLine, Sparkles } from "lucide-react";
import { useMemo } from "react";
import { useOutletContext } from "react-router-dom";

import type { LayoutOutletContext } from "../Layout";
import SevenStepSidebar from "./chat/SevenStepSidebar";

export default function CreationPage() {
  const { locale } = useOutletContext<LayoutOutletContext>();

  const copy = useMemo(
    () =>
      locale === "zh"
        ? {
            title: "创作",
            desc: "将七步写作从聊天区独立为专用工作台，按多 Agent 编排推进标题、大纲、正文、配图与交付。",
            boardTitle: "多 Agent 编排看板",
            boardDesc: "参考 ai-passage-creator 的分工模式，执行链路拆为独立 Agent 节点，便于扩展与排障。",
            ragTitle: "RAG 接入建议",
            ragDesc:
              "优先接在大纲生成与正文生成前：先召回素材，再注入上下文，可显著提升结构准确性与事实一致性。",
            nodes: [
              "Agent-1：标题策划",
              "Agent-2：大纲生成与修正",
              "Agent-3：正文生成",
              "Agent-4：配图需求分析",
              "Agent-5：图文合成与交付",
            ],
            ragPoints: [
              "节点A（大纲前）：按 topic + 偏好召回 TopK 结构化片段",
              "节点B（正文前）：按章节标题二次检索并做 section 级注入",
              "保底策略：检索为空时回退到纯生成，保证流程不中断",
            ],
          }
        : {
            title: "Creation",
            desc: "A dedicated workspace for the former 7-step writing flow, now orchestrated as a multi-agent pipeline.",
            boardTitle: "Multi-Agent Orchestration",
            boardDesc: "Following ai-passage-creator style decomposition, each stage is an explicit agent node for clarity and extensibility.",
            ragTitle: "RAG Placement Suggestion",
            ragDesc:
              "Attach retrieval right before outline generation and draft generation to improve factual accuracy and structural quality.",
            nodes: [
              "Agent-1: Title Planner",
              "Agent-2: Outline Planner & Refiner",
              "Agent-3: Draft Writer",
              "Agent-4: Image Requirement Analyzer",
              "Agent-5: Final Merger & Delivery",
            ],
            ragPoints: [
              "Node A (before outline): retrieve top-k planning evidence",
              "Node B (before drafting): section-level retrieval for each heading",
              "Fallback: continue generation when retrieval is empty",
            ],
          },
    [locale],
  );

  return (
    <section className="space-y-5">
      <header className="rounded-3xl border border-white/10 bg-white/5 p-5">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/25 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-200">
          <Sparkles className="h-3.5 w-3.5" />
          Multi-Agent Creation Workspace
        </div>
        <h2 className="mt-3 text-2xl font-semibold text-[hsl(var(--foreground))]">{copy.title}</h2>
        <p className="mt-2 text-sm text-slate-300">{copy.desc}</p>
      </header>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
        <article className="rounded-3xl border border-white/10 bg-black/20 p-4 md:p-5">
          <SevenStepSidebar locale={locale} mode="page" />
        </article>

        <aside className="space-y-4">
          <article className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="inline-flex items-center gap-2 text-xs font-medium text-cyan-200">
              <GitBranch className="h-3.5 w-3.5" />
              {copy.boardTitle}
            </p>
            <p className="mt-2 text-xs leading-6 text-slate-300">{copy.boardDesc}</p>
            <ul className="mt-3 space-y-2 text-xs text-slate-300">
              {copy.nodes.map((item) => (
                <li key={item} className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">
                  <span className="inline-flex items-center gap-2">
                    <Bot className="h-3.5 w-3.5 text-cyan-200" />
                    {item}
                  </span>
                </li>
              ))}
            </ul>
          </article>

          <article className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="inline-flex items-center gap-2 text-xs font-medium text-cyan-200">
              <FileSearch className="h-3.5 w-3.5" />
              {copy.ragTitle}
            </p>
            <p className="mt-2 text-xs leading-6 text-slate-300">{copy.ragDesc}</p>
            <ul className="mt-3 space-y-2 text-xs text-slate-300">
              {copy.ragPoints.map((item) => (
                <li key={item} className="inline-flex items-start gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2">
                  <ListChecks className="mt-0.5 h-3.5 w-3.5 text-cyan-200" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </article>

          <article className="rounded-2xl border border-white/10 bg-white/5 p-4 text-xs text-slate-400">
            <p className="inline-flex items-center gap-2 font-medium text-slate-200">
              <PenLine className="h-3.5 w-3.5 text-cyan-200" />
              {locale === "zh" ? "人工介入点" : "Human-in-the-loop"}
            </p>
            <p className="mt-2 leading-6">
              {locale === "zh"
                ? "标题确认与大纲确认保持人工可编辑，确保创作可控；其余 Agent 节点保持自动化执行。"
                : "Keep title and outline confirmation editable by users, while other agent nodes remain automated."}
            </p>
          </article>
        </aside>
      </div>
    </section>
  );
}
