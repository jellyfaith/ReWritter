const TOKEN_KEY = "rewritter.auth.token";
const EXPIRES_AT_KEY = "rewritter.auth.expires_at";
const viteMeta = import.meta as ImportMeta & { env?: { VITE_API_BASE?: string } };
export const API_BASE = viteMeta.env?.VITE_API_BASE ?? "http://localhost:8001";

export interface LoginPayload {
  username: string;
  password: string;
  rememberMe: boolean;
}

export interface LoginResult {
  accessToken: string;
  expiresIn: number;
}

interface LoginResponse {
  access_token: string;
  expires_in: number;
}

function readStorageValue(key: string): string | null {
  return localStorage.getItem(key) ?? sessionStorage.getItem(key);
}

function writeStorageValue(key: string, value: string, persistent: boolean): void {
  if (persistent) {
    localStorage.setItem(key, value);
    sessionStorage.removeItem(key);
    return;
  }

  sessionStorage.setItem(key, value);
  localStorage.removeItem(key);
}

export function saveAuth(token: string, expiresIn: number, persistent: boolean): void {
  const expiresAt = Date.now() + expiresIn * 1000;
  writeStorageValue(TOKEN_KEY, token, persistent);
  writeStorageValue(EXPIRES_AT_KEY, String(expiresAt), persistent);
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(EXPIRES_AT_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(EXPIRES_AT_KEY);
}

export function getToken(): string | null {
  return readStorageValue(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  const token = getToken();
  const expiresAtRaw = readStorageValue(EXPIRES_AT_KEY);

  if (!token || !expiresAtRaw) {
    return false;
  }

  const expiresAt = Number(expiresAtRaw);
  if (!Number.isFinite(expiresAt) || Date.now() >= expiresAt) {
    clearAuth();
    return false;
  }

  return true;
}

export function buildAuthHeaders(baseHeaders?: HeadersInit): HeadersInit {
  const token = getToken();
  if (!token) {
    return baseHeaders ?? {};
  }

  return {
    ...(baseHeaders ?? {}),
    Authorization: `Bearer ${token}`,
  };
}

export async function login(payload: LoginPayload): Promise<LoginResult> {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username: payload.username,
      password: payload.password,
      remember_me: payload.rememberMe,
    }),
  });

  if (!response.ok) {
    let message = "登录失败，请检查用户名或密码";
    try {
      const errorData = (await response.json()) as { detail?: string };
      if (errorData.detail) {
        message = errorData.detail;
      }
    } catch {
      // Keep fallback message when backend payload is not JSON.
    }
    throw new Error(message);
  }

  const data = (await response.json()) as LoginResponse;
  return {
    accessToken: data.access_token,
    expiresIn: data.expires_in,
  };
}
