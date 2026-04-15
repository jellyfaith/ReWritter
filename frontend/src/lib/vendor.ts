import { API_BASE, buildAuthHeaders } from "./auth";

export type VendorCapability = "chat" | "embedding";

export interface VendorConfig {
  capability: VendorCapability;
  vendor_id: string;
  display_name: string;
  api_base: string;
  model: string;
  enabled: boolean;
  key_configured: boolean;
  api_key_mask: string;
  source: "ui" | "env";
  updated_at: number;
}

export interface VendorConfigUpdatePayload {
  capability: VendorCapability;
  vendor_id: string;
  display_name: string;
  api_base: string;
  model: string;
  enabled: boolean;
  api_key: string;
}

export interface DeepSeekVendorTestResult {
  ok: boolean;
  vendor: string;
  model: string;
  configured: boolean;
  latency_ms?: number;
  message: string;
}

export interface EmbeddingVendorTestResult {
  ok: boolean;
  vendor: string;
  model: string;
  configured: boolean;
  latency_ms?: number;
  message: string;
}

export async function listVendorConfigs(): Promise<VendorConfig[]> {
  const response = await fetch(`${API_BASE}/api/vendors/configs`, {
    method: "GET",
    headers: buildAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error("获取厂家配置失败");
  }

  return (await response.json()) as VendorConfig[];
}

export async function updateVendorConfig(
  capability: VendorCapability,
  payload: VendorConfigUpdatePayload,
): Promise<VendorConfig> {
  const response = await fetch(`${API_BASE}/api/vendors/configs/${capability}`, {
    method: "PUT",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    try {
      const errorPayload = (await response.json()) as { detail?: string };
      throw new Error(errorPayload.detail ?? "保存厂家配置失败");
    } catch {
      throw new Error("保存厂家配置失败");
    }
  }

  return (await response.json()) as VendorConfig;
}

export async function testDeepSeekVendor(params: {
  model: string;
  enableThinking: boolean;
}): Promise<DeepSeekVendorTestResult> {
  const response = await fetch(`${API_BASE}/api/vendors/deepseek/test`, {
    method: "POST",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      model: params.model,
      enable_thinking: params.enableThinking,
    }),
  });

  if (!response.ok) {
    try {
      const errorPayload = (await response.json()) as { detail?: string };
      throw new Error(errorPayload.detail ?? "厂家连通性测试失败");
    } catch {
      throw new Error("厂家连通性测试失败");
    }
  }

  return (await response.json()) as DeepSeekVendorTestResult;
}

export async function testEmbeddingVendor(): Promise<EmbeddingVendorTestResult> {
  const response = await fetch(`${API_BASE}/api/vendors/embedding/test`, {
    method: "POST",
    headers: buildAuthHeaders(),
  });

  if (!response.ok) {
    try {
      const errorPayload = (await response.json()) as { detail?: string };
      throw new Error(errorPayload.detail ?? "Embedding 厂家连通性测试失败");
    } catch {
      throw new Error("Embedding 厂家连通性测试失败");
    }
  }

  return (await response.json()) as EmbeddingVendorTestResult;
}
