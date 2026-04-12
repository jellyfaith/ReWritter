import type { TaskStage } from "../types/task";
import { useOutletContext } from "react-router-dom";

import type { LayoutOutletContext } from "../Layout";

interface TaskRow {
  id: string;
  topic: string;
  stage: TaskStage;
  updatedAt: string;
}

const rows: TaskRow[] = [
  {
    id: "task_001",
    topic: "多智能体研发体系",
    stage: "pending_review",
    updatedAt: "2026-04-10 10:18"
  },
  {
    id: "task_002",
    topic: "企业知识库 RAG 演进",
    stage: "generating",
    updatedAt: "2026-04-10 10:05"
  }
];

const stageText: Record<TaskStage, string> = {
  searching: "检索中",
  generating: "生成中",
  pending_review: "待审核",
  publishing: "发布中",
  published: "已发布"
};

export default function TaskList() {
  const { locale } = useOutletContext<LayoutOutletContext>();

  const copy =
    locale === "zh"
      ? {
          title: "任务大厅",
          desc: "任务状态流转：检索中 -> 生成中 -> 待审核 -> 发布中 -> 已发布。",
          table: {
            taskId: "Task ID",
            topic: "主题",
            stage: "状态",
            updatedAt: "更新时间"
          },
          stageMap: stageText
        }
      : {
          title: "Task Hall",
          desc: "Flow: Searching -> Generating -> Pending Review -> Publishing -> Published.",
          table: {
            taskId: "Task ID",
            topic: "Topic",
            stage: "Status",
            updatedAt: "Updated At"
          },
          stageMap: {
            searching: "Searching",
            generating: "Generating",
            pending_review: "Pending Review",
            publishing: "Publishing",
            published: "Published"
          } as Record<TaskStage, string>
        };

  return (
    <section className="space-y-5">
      <header>
        <h2 className="text-2xl font-semibold text-[hsl(var(--foreground))]">{copy.title}</h2>
        <p className="mt-2 text-sm text-slate-300">{copy.desc}</p>
      </header>

      <div className="panel overflow-x-auto rounded-3xl">
        <table className="min-w-full divide-y divide-white/10 text-sm">
          <thead className="bg-black/20 text-left text-slate-300">
            <tr>
              <th className="px-4 py-3 font-medium">{copy.table.taskId}</th>
              <th className="px-4 py-3 font-medium">{copy.table.topic}</th>
              <th className="px-4 py-3 font-medium">{copy.table.stage}</th>
              <th className="px-4 py-3 font-medium">{copy.table.updatedAt}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10 text-slate-200">
            {rows.map((row) => (
              <tr key={row.id} className="hover:bg-white/5">
                <td className="px-4 py-3 font-medium text-cyan-300">{row.id}</td>
                <td className="px-4 py-3">{row.topic}</td>
                <td className="px-4 py-3">{copy.stageMap[row.stage]}</td>
                <td className="px-4 py-3 text-slate-400">{row.updatedAt}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
