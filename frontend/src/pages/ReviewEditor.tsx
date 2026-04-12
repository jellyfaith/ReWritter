import { useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";

import type { LayoutOutletContext } from "../Layout";
import type { ContextFact, StyleSnippet } from "../types/task";

const mockFacts: ContextFact[] = [
  {
    id: "fact_1",
    title: "行业动态",
    snippet: "2026 年企业内容自动化从单模型生成升级到多阶段审核流。",
    source: "行业观察日报"
  },
  {
    id: "fact_2",
    title: "平台策略",
    snippet: "内容平台对事实引用和原创风格稳定性权重持续提升。",
    source: "平台公告汇总"
  }
];

const mockStyles: StyleSnippet[] = [
  {
    id: "style_1",
    excerpt: "开篇先抛出关键判断，再用案例拆解，让读者快速进入语境。",
    similarity: 0.89
  },
  {
    id: "style_2",
    excerpt: "结尾强调行动建议，形成“观点 -> 方法 -> 落地”的闭环。",
    similarity: 0.84
  }
];

const initialDraft = `# 2026 企业内容自动化趋势\n\n- 观点：内容生产从“单点生成”走向“系统协作”。\n- 方法：检索事实、注入风格、人工审核三段式闭环。\n`;

export default function ReviewEditor() {
  const { locale } = useOutletContext<LayoutOutletContext>();
  const [draftMarkdown, setDraftMarkdown] = useState<string>(initialDraft);

  const copy =
    locale === "zh"
      ? {
          title: "审核台",
          desc: "左侧只读上下文，右侧编辑生成草稿，确认后一键发布。",
          contextTitle: "RAG Context（只读）",
          editorTitle: "Draft Editor",
          approve: "Approve & Publish"
        }
      : {
          title: "Review Desk",
          desc: "Use context on the left and edit draft on the right before publishing.",
          contextTitle: "RAG Context (Read-only)",
          editorTitle: "Draft Editor",
          approve: "Approve & Publish"
        };

  // 将事实和风格统一为可渲染上下文，便于后续接入真实 API 数据。
  const contextBlocks = useMemo(
    () => [
      ...mockFacts.map((fact) => ({
        id: fact.id,
        title: fact.title,
        body: `${fact.snippet}\n来源：${fact.source}`
      })),
      ...mockStyles.map((style) => ({
        id: style.id,
        title: `风格片段（相似度 ${Math.round(style.similarity * 100)}%）`,
        body: style.excerpt
      }))
    ],
    []
  );

  return (
    <section className="flex h-full min-h-[70vh] flex-col">
      <header className="mb-4">
        <h2 className="text-2xl font-semibold text-[hsl(var(--foreground))]">{copy.title}</h2>
        <p className="mt-1 text-sm text-slate-300">{copy.desc}</p>
      </header>

      <div className="grid flex-1 gap-4 lg:grid-cols-2">
        <aside className="panel rounded-3xl p-4">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-cyan-300">{copy.contextTitle}</h3>
          <div className="space-y-3 overflow-y-auto pr-1">
            {contextBlocks.map((block) => (
              <article key={block.id} className="rounded-xl border border-white/10 bg-white/5 p-3">
                <h4 className="text-sm font-medium text-[hsl(var(--foreground))]">{block.title}</h4>
                <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-300">{block.body}</p>
              </article>
            ))}
          </div>
        </aside>

        <section className="panel rounded-3xl p-4">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-cyan-300">{copy.editorTitle}</h3>
          <textarea
            value={draftMarkdown}
            onChange={(event) => setDraftMarkdown(event.target.value)}
            className="h-[52vh] w-full resize-none rounded-xl border border-white/10 bg-black/20 p-3 text-sm leading-6 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
          />
        </section>
      </div>

      <footer className="mt-4 flex justify-end">
        <button
          type="button"
          className="inline-flex items-center rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-medium text-emerald-950 transition hover:bg-emerald-400"
        >
          {copy.approve}
        </button>
      </footer>

      {/* TODO: 接入服务端审核确认接口并补充失败提示。 */}
    </section>
  );
}
