import { API_BASE, buildAuthHeaders } from "./auth";

export interface SevenStepTitleOption {
  main_title: string;
  sub_title: string;
}

export interface SevenStepOutlineSection {
  section: number;
  title: string;
  points: string[];
}

export interface SevenStepImagePlanItem {
  placeholder_id: string;
  section_title: string;
  description: string;
  keywords: string;
  status: string;
}

export interface SevenStepAgentTrace {
  agent_id: string;
  agent_name: string;
  stage: number;
  status: string;
  summary: string;
  started_at: number;
  finished_at: number;
}

export interface SevenStepFlow {
  flow_id: string;
  topic: string;
  preferences: string;
  style: string;
  status: string;
  current_step: number;
  title_options: SevenStepTitleOption[];
  selected_title: SevenStepTitleOption | null;
  outline: SevenStepOutlineSection[];
  content: string;
  image_plan: SevenStepImagePlanItem[];
  final_markdown: string;
  agent_traces: SevenStepAgentTrace[];
  created_at: number;
  updated_at: number;
}

async function parseError(response: Response, fallback: string): Promise<Error> {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) {
      return new Error(payload.detail);
    }
  } catch {
    // Ignore non-JSON response.
  }
  return new Error(fallback);
}

export async function createSevenStepFlow(params: {
  topic: string;
  preferences?: string;
  style?: string;
}): Promise<SevenStepFlow> {
  const response = await fetch(`${API_BASE}/api/writing-flow/sessions`, {
    method: "POST",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      topic: params.topic,
      preferences: params.preferences ?? "",
      style: params.style ?? "",
    }),
  });

  if (!response.ok) {
    throw await parseError(response, "创建七步写作会话失败");
  }

  return (await response.json()) as SevenStepFlow;
}

export async function getSevenStepFlow(flowId: string): Promise<SevenStepFlow> {
  const response = await fetch(`${API_BASE}/api/writing-flow/sessions/${flowId}`, {
    method: "GET",
    headers: buildAuthHeaders(),
  });

  if (!response.ok) {
    throw await parseError(response, "获取七步写作会话失败");
  }

  return (await response.json()) as SevenStepFlow;
}

export async function confirmSevenStepTitle(params: {
  flowId: string;
  mainTitle: string;
  subTitle?: string;
}): Promise<SevenStepFlow> {
  const response = await fetch(`${API_BASE}/api/writing-flow/sessions/${params.flowId}/confirm-title`, {
    method: "POST",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      main_title: params.mainTitle,
      sub_title: params.subTitle ?? "",
    }),
  });

  if (!response.ok) {
    throw await parseError(response, "确认标题失败");
  }

  return (await response.json()) as SevenStepFlow;
}

export async function confirmSevenStepOutline(params: {
  flowId: string;
  outline: SevenStepOutlineSection[];
}): Promise<SevenStepFlow> {
  const response = await fetch(`${API_BASE}/api/writing-flow/sessions/${params.flowId}/confirm-outline`, {
    method: "POST",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      outline: params.outline,
    }),
  });

  if (!response.ok) {
    throw await parseError(response, "确认大纲失败");
  }

  return (await response.json()) as SevenStepFlow;
}
