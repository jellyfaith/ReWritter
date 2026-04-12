export type TaskStage =
  | "searching"
  | "generating"
  | "pending_review"
  | "publishing"
  | "published";

export interface ContextFact {
  id: string;
  title: string;
  snippet: string;
  source: string;
}

export interface StyleSnippet {
  id: string;
  excerpt: string;
  similarity: number;
}

export interface ReviewTaskData {
  taskId: string;
  stage: TaskStage;
  topic: string;
  facts: ContextFact[];
  styles: StyleSnippet[];
  draftMarkdown: string;
}
