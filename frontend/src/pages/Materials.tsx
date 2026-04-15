import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { Database, FileUp, FolderKanban, LoaderCircle } from "lucide-react";

import { listMaterialFiles, listMaterialGroups, uploadMaterial, type MaterialFile, type MaterialGroup } from "../lib/materials";

function formatTime(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatSize(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / 1024 / 1024).toFixed(2)} MB`;
}

export default function MaterialsPage() {
  const [groups, setGroups] = useState<MaterialGroup[]>([]);
  const [activeGroupId, setActiveGroupId] = useState<string>("");
  const [files, setFiles] = useState<MaterialFile[]>([]);
  const [groupName, setGroupName] = useState<string>("");
  const [topic, setTopic] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [loadingGroups, setLoadingGroups] = useState<boolean>(true);
  const [loadingFiles, setLoadingFiles] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [success, setSuccess] = useState<string>("");

  useEffect(() => {
    const load = async () => {
      setLoadingGroups(true);
      setError("");
      try {
        const data = await listMaterialGroups();
        setGroups(data);
        if (data.length > 0) {
          setActiveGroupId((prev) => prev || data[0].group_id);
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "加载素材组失败");
      } finally {
        setLoadingGroups(false);
      }
    };
    void load();
  }, []);

  useEffect(() => {
    const loadFiles = async () => {
      if (!activeGroupId) {
        setFiles([]);
        return;
      }
      setLoadingFiles(true);
      setError("");
      try {
        const data = await listMaterialFiles(activeGroupId);
        setFiles(data);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "加载素材文件失败");
      } finally {
        setLoadingFiles(false);
      }
    };
    void loadFiles();
  }, [activeGroupId]);

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedFile || !groupName.trim()) {
      setError("请先填写素材组并选择文件");
      return;
    }

    setSubmitting(true);
    setError("");
    setSuccess("");

    try {
      const result = await uploadMaterial({
        groupName: groupName.trim(),
        topic: topic.trim(),
        file: selectedFile,
      });
      setSuccess(`${result.message}（embedding=${result.embedding_provider}）`);
      const groupList = await listMaterialGroups();
      setGroups(groupList);
      setActiveGroupId(result.group.group_id);
      setFiles(await listMaterialFiles(result.group.group_id));
      setSelectedFile(null);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "上传失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="grid gap-4 xl:grid-cols-[340px_1fr]">
      <article className="panel rounded-3xl p-5">
        <header className="flex items-center gap-2">
          <FileUp className="h-5 w-5 text-cyan-300" />
          <h2 className="text-xl font-semibold text-[hsl(var(--foreground))]">添加素材</h2>
        </header>
        <p className="mt-2 text-sm text-slate-300">上传 txt / md 文件，自动切块并 embedding 入向量数据库（Milvus）。</p>

        <form onSubmit={onSubmit} className="mt-4 space-y-3">
          <label className="grid gap-1 text-sm text-slate-300">
            素材组名称
            <input
              value={groupName}
              onChange={(event) => setGroupName(event.target.value)}
              placeholder="例如：鲁迅文章"
              className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
            />
          </label>

          <label className="grid gap-1 text-sm text-slate-300">
            主题（可选）
            <input
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              placeholder="例如：现代文学"
              className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
            />
          </label>

          <label className="grid gap-1 text-sm text-slate-300">
            文件
            <input
              type="file"
              accept=".txt,.md,.markdown"
              onChange={onFileChange}
              className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-cyan-500 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-slate-950"
            />
          </label>

          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:opacity-60"
          >
            {submitting ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}
            {submitting ? "向量化中..." : "上传并向量化"}
          </button>
        </form>

        {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}
        {success ? <p className="mt-3 text-sm text-emerald-300">{success}</p> : null}
      </article>

      <article className="panel rounded-3xl p-5">
        <header className="flex items-center gap-2">
          <FolderKanban className="h-5 w-5 text-cyan-300" />
          <h2 className="text-xl font-semibold text-[hsl(var(--foreground))]">素材组</h2>
        </header>

        <div className="mt-4 grid gap-3 lg:grid-cols-[280px_1fr]">
          <div className="space-y-2">
            {loadingGroups ? <p className="text-sm text-slate-400">加载中...</p> : null}
            {!loadingGroups && groups.length === 0 ? <p className="text-sm text-slate-400">暂无素材组</p> : null}
            {groups.map((group) => (
              <button
                key={group.group_id}
                type="button"
                onClick={() => setActiveGroupId(group.group_id)}
                className={[
                  "w-full rounded-2xl border px-3 py-3 text-left transition",
                  group.group_id === activeGroupId
                    ? "border-cyan-300/60 bg-cyan-400/15"
                    : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10",
                ].join(" ")}
              >
                <p className="truncate text-sm font-medium text-[hsl(var(--foreground))]">{group.group_name}</p>
                <p className="mt-1 text-xs text-slate-400">{group.topic}</p>
                <p className="mt-1 text-[11px] text-slate-500">文件 {group.file_count} · 切片 {group.chunk_count}</p>
              </button>
            ))}
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
            <h3 className="text-sm font-medium text-[hsl(var(--foreground))]">组内文件</h3>
            {loadingFiles ? <p className="mt-2 text-sm text-slate-400">加载文件中...</p> : null}
            {!loadingFiles && files.length === 0 ? <p className="mt-2 text-sm text-slate-400">该组暂无文件</p> : null}
            <div className="mt-3 space-y-2">
              {files.map((file) => (
                <div key={file.file_id} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
                  <p className="text-sm font-medium text-[hsl(var(--foreground))]">{file.file_name}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    {formatSize(file.file_size)} · 切片 {file.chunk_count} · {formatTime(file.created_at)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </article>
    </section>
  );
}
