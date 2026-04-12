import { useState } from "react";
import { ArrowRight, Rocket, ScrollText, Sparkles } from "lucide-react";
import { useOutletContext } from "react-router-dom";

import type { LayoutOutletContext } from "../Layout";

export default function CreateTask() {
  const { locale } = useOutletContext<LayoutOutletContext>();
  const [topic, setTopic] = useState<string>("");
  const [requirements, setRequirements] = useState<string>("");

  const copy =
    locale === "zh"
      ? {
          pageTitle: "创作中心",
          pageDesc: "在这里编排任务、注入约束并驱动生成审核流程。",
          heroTitle: "让内容生产像数据管道一样稳定",
          heroDesc: "从选题输入到审核发布，统一管理每一个节点，减少重复沟通成本。",
          primaryAction: "创建新任务",
          secondaryAction: "查看任务大厅",
          featureTitle: "特色功能：风格注入 + 事实约束",
          featureDesc: "通过结构化提示模板将品牌语气与事实来源绑定，确保输出稳定可控。",
          tags: ["RAG 检索", "风格迁移", "人工审核", "可追踪日志", "批量发布"],
          featureAction: "启用高级模板",
          quickTitle: "快捷操作",
          quickActions: [
            {
              id: "qa_1",
              title: "快速创建营销稿",
              desc: "自动填充行业趋势和结构模板"
            },
            {
              id: "qa_2",
              title: "导入知识库摘要",
              desc: "将近期文档要点同步到上下文"
            },
            {
              id: "qa_3",
              title: "进入审核台",
              desc: "查看待审核草稿并进行发布"
            }
          ],
          formTitle: "创建内容任务",
          formDesc: "输入选题和约束条件，任务将进入异步工作流队列。",
          topicLabel: "文章主题",
          topicPlaceholder: "例如：2026 年 AI Agent 生产力工具盘点",
          reqLabel: "额外要求",
          reqPlaceholder: "例如：偏实战风格，包含步骤和工具对比",
          submit: "提交任务（占位）"
        }
      : {
          pageTitle: "Create Center",
          pageDesc: "Orchestrate tasks, apply constraints, and trigger review flow.",
          heroTitle: "Make content delivery as stable as a data pipeline",
          heroDesc: "Manage each stage from topic input to publication in one coherent workspace.",
          primaryAction: "Create Task",
          secondaryAction: "Open Task Hall",
          featureTitle: "Featured: Style Injection + Fact Constraints",
          featureDesc: "Bind brand tone and trusted sources with structured prompts for reliable output.",
          tags: ["RAG Retrieval", "Style Transfer", "Human Review", "Trace Logs", "Batch Publish"],
          featureAction: "Enable Advanced Template",
          quickTitle: "Quick Actions",
          quickActions: [
            {
              id: "qa_1",
              title: "Build marketing draft",
              desc: "Auto-fill trend snapshots and outline"
            },
            {
              id: "qa_2",
              title: "Import knowledge digest",
              desc: "Sync recent docs into context blocks"
            },
            {
              id: "qa_3",
              title: "Open review desk",
              desc: "Inspect pending drafts before publishing"
            }
          ],
          formTitle: "Create Content Task",
          formDesc: "Fill topic and constraints, then dispatch into async workers.",
          topicLabel: "Topic",
          topicPlaceholder: "Example: AI Agent productivity tools in 2026",
          reqLabel: "Requirements",
          reqPlaceholder: "Example: Practical style with tool comparison",
          submit: "Submit Task (placeholder)"
        };

  return (
    <section className="space-y-5">
      <header>
        <h2 className="text-2xl font-semibold text-[hsl(var(--foreground))]">{copy.pageTitle}</h2>
        <p className="mt-2 text-sm text-slate-300">{copy.pageDesc}</p>
      </header>

      <article className="hero-gradient rounded-3xl p-6 text-slate-950 shadow-2xl shadow-cyan-900/30">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div className="max-w-2xl">
            <h3 className="text-3xl font-semibold leading-tight">{copy.heroTitle}</h3>
            <p className="mt-2 text-sm text-slate-900/80">{copy.heroDesc}</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-900"
            >
              <Rocket className="h-4 w-4" />
              {copy.primaryAction}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-950/50 px-4 py-2 text-sm font-medium text-slate-900 transition hover:bg-slate-950/10"
            >
              <ScrollText className="h-4 w-4" />
              {copy.secondaryAction}
            </button>
          </div>
        </div>
      </article>

      <article className="panel rounded-3xl p-5">
        <h3 className="text-lg font-semibold text-[hsl(var(--foreground))]">{copy.featureTitle}</h3>
        <p className="mt-2 text-sm text-slate-300">{copy.featureDesc}</p>

        <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
          {copy.tags.map((tag) => (
            <span
              key={tag}
              className="shrink-0 rounded-full border border-cyan-300/30 bg-cyan-300/10 px-3 py-1 text-xs font-medium text-cyan-200"
            >
              {tag}
            </span>
          ))}
        </div>

        <div className="mt-5 flex justify-end">
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400"
          >
            <Sparkles className="h-4 w-4" />
            {copy.featureAction}
          </button>
        </div>
      </article>

      <section className="panel rounded-3xl p-5">
        <h3 className="text-lg font-semibold text-[hsl(var(--foreground))]">{copy.quickTitle}</h3>
        <div className="mt-4 space-y-3">
          {copy.quickActions.map((action) => (
            <button
              key={action.id}
              type="button"
              className="flex w-full items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-left transition hover:border-cyan-300/40 hover:bg-cyan-400/10"
            >
              <div className="flex items-center gap-3">
                <span className="rounded-lg bg-cyan-300/15 p-2 text-cyan-200">
                  <Sparkles className="h-4 w-4" />
                </span>
                <span>
                  <span className="block text-sm font-medium text-[hsl(var(--foreground))]">{action.title}</span>
                  <span className="block text-xs text-slate-400">{action.desc}</span>
                </span>
              </div>
              <ArrowRight className="h-4 w-4 text-slate-400" />
            </button>
          ))}
        </div>
      </section>

      <form className="panel grid gap-4 rounded-3xl p-5">
        <header>
          <h3 className="text-lg font-semibold text-[hsl(var(--foreground))]">{copy.formTitle}</h3>
          <p className="mt-1 text-sm text-slate-300">{copy.formDesc}</p>
        </header>

        <label className="grid gap-2 text-sm font-medium text-slate-200">
          {copy.topicLabel}
          <input
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder={copy.topicPlaceholder}
            className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
          />
        </label>

        <label className="grid gap-2 text-sm font-medium text-slate-200">
          {copy.reqLabel}
          <textarea
            value={requirements}
            onChange={(event) => setRequirements(event.target.value)}
            placeholder={copy.reqPlaceholder}
            rows={5}
            className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
          />
        </label>

        <button
          type="button"
          className="inline-flex w-fit items-center rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400"
        >
          {copy.submit}
        </button>

        {/* TODO: 接入真实提交接口并追加字段校验。 */}
      </form>
    </section>
  );
}
