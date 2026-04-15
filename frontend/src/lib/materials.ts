import { API_BASE, buildAuthHeaders } from "./auth";

export interface MaterialGroup {
  group_id: string;
  group_name: string;
  topic: string;
  file_count: number;
  chunk_count: number;
  created_at: number;
  updated_at: number;
}

export interface MaterialFile {
  file_id: string;
  group_id: string;
  file_name: string;
  file_size: number;
  chunk_count: number;
  created_at: number;
}

export interface MaterialUploadResponse {
  group: MaterialGroup;
  file: MaterialFile;
  embedding_provider: string;
  message: string;
}

async function parseError(response: Response, fallback: string): Promise<Error> {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) {
      return new Error(payload.detail);
    }
  } catch {
    // Ignore and fallback.
  }
  return new Error(fallback);
}

export async function listMaterialGroups(): Promise<MaterialGroup[]> {
  const response = await fetch(`${API_BASE}/api/materials/groups`, {
    method: "GET",
    headers: buildAuthHeaders(),
  });

  if (!response.ok) {
    throw await parseError(response, "获取素材组失败");
  }
  return (await response.json()) as MaterialGroup[];
}

export async function listMaterialFiles(groupId: string): Promise<MaterialFile[]> {
  const response = await fetch(`${API_BASE}/api/materials/groups/${groupId}/files`, {
    method: "GET",
    headers: buildAuthHeaders(),
  });

  if (!response.ok) {
    throw await parseError(response, "获取素材文件失败");
  }
  return (await response.json()) as MaterialFile[];
}

export async function uploadMaterial(params: {
  groupName: string;
  topic: string;
  file: File;
}): Promise<MaterialUploadResponse> {
  const formData = new FormData();
  formData.append("group_name", params.groupName);
  formData.append("topic", params.topic);
  formData.append("file", params.file);

  const response = await fetch(`${API_BASE}/api/materials/upload`, {
    method: "POST",
    headers: buildAuthHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw await parseError(response, "素材上传失败");
  }
  return (await response.json()) as MaterialUploadResponse;
}
