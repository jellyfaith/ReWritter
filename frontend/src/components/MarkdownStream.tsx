import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Download } from "lucide-react";

export interface MarkdownStreamProps {
  content: string;
  streaming?: boolean;
  className?: string;
  showDownload?: boolean;
  downloadFileName?: string;
  onDownload?: () => void;
}

const markdownComponents: Components = {
  code({ className, children, ...props }) {
    const match = /language-([\w-]+)/.exec(className ?? "");
    const codeText = String(children).replace(/\n$/, "");
    const isCodeBlock = Boolean(match) || codeText.includes("\n");

    if (isCodeBlock) {
      return (
        <div className="relative">
          <SyntaxHighlighter
            language={match?.[1] ?? "text"}
            style={oneDark}
            PreTag="div"
            customStyle={{
              margin: "0.6rem 0",
              borderRadius: "0.75rem",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              padding: "0.8rem",
              fontSize: "0.82rem",
              overflowX: "auto",
            }}
            showLineNumbers
            lineNumberStyle={{
              minWidth: "2.5em",
              paddingRight: "0.8em",
              textAlign: "right",
              color: "rgba(255, 255, 255, 0.3)",
              userSelect: "none",
            }}
          >
            {codeText}
          </SyntaxHighlighter>
        </div>
      );
    }

    return (
      <code className="rounded bg-black/30 px-1 py-0.5 text-[0.85em]" {...props}>
        {children}
      </code>
    );
  },
  a({ children, ...props }) {
    return (
      <a
        {...props}
        target="_blank"
        rel="noreferrer noopener"
        className="text-cyan-300 underline decoration-cyan-300/60 underline-offset-2 hover:text-cyan-200 hover:decoration-cyan-300"
      >
        {children}
      </a>
    );
  },
  table({ children }) {
    return (
      <div className="overflow-x-auto my-4">
        <table className="min-w-full divide-y divide-white/10 border border-white/10 rounded-lg">
          {children}
        </table>
      </div>
    );
  },
  th({ children }) {
    return (
      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-200 bg-white/5 border-b border-white/10">
        {children}
      </th>
    );
  },
  td({ children }) {
    return (
      <td className="px-4 py-3 text-sm text-slate-300 border-b border-white/5">
        {children}
      </td>
    );
  },
  blockquote({ children }) {
    return (
      <blockquote className="border-l-4 border-cyan-500/50 pl-4 my-4 italic text-slate-300 bg-cyan-500/5 py-2 rounded-r-lg">
        {children}
      </blockquote>
    );
  },
  img({ src, alt }) {
    return (
      <div className="my-4">
        <img
          src={src}
          alt={alt || "图片"}
          className="rounded-lg border border-white/10 max-w-full h-auto"
          loading="lazy"
        />
        {alt && (
          <p className="text-center text-sm text-slate-400 mt-2">{alt}</p>
        )}
      </div>
    );
  },
};

export function MarkdownStream({
  content,
  streaming = false,
  className = "",
  showDownload = false,
  downloadFileName = "document.md",
  onDownload,
}: MarkdownStreamProps) {
  const handleDownload = () => {
    if (onDownload) {
      onDownload();
      return;
    }

    // 默认下载实现
    const blob = new Blob([content], { type: "text/markdown" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = downloadFileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className={className}>
      {showDownload && (
        <div className="mb-4 flex items-center justify-end">
          <button
            onClick={handleDownload}
            className="inline-flex items-center gap-2 rounded-xl border border-emerald-300/30 bg-emerald-500/20 px-3 py-1.5 text-sm text-emerald-100 transition hover:bg-emerald-500/30"
          >
            <Download className="h-4 w-4" />
            下载 Markdown
          </button>
        </div>
      )}

      <div className="prose prose-invert max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {content}
        </ReactMarkdown>
      </div>

      {streaming ? <span className="chat-caret" /> : null}
    </div>
  );
}

export default MarkdownStream;
