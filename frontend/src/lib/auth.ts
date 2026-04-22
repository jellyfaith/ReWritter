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

// 用户偏好相关接口
export interface UserPreferences {
  theme: "light" | "dark";
  locale: "zh" | "en";
  notifications_enabled: boolean;
  default_model: string;
  rag_settings: Record<string, any>;
  created_at: number;
  updated_at: number;
}

export interface UserPreferencesUpdate {
  theme?: "light" | "dark";
  locale?: "zh" | "en";
  notifications_enabled?: boolean;
  default_model?: string;
  rag_settings?: Record<string, any>;
}

export interface UserPreferencesResponse {
  preferences: UserPreferences;
}

// 获取用户偏好
export async function getUserPreferences(): Promise<UserPreferences> {
  const response = await fetch(`${API_BASE}/api/auth/preferences`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...buildAuthHeaders(),
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      clearAuth();
      throw new Error("认证已过期，请重新登录");
    }
    throw new Error(`获取用户偏好失败: ${response.statusText}`);
  }

  const data = (await response.json()) as UserPreferencesResponse;
  return data.preferences;
}

// 更新用户偏好
export async function updateUserPreferences(
  updates: UserPreferencesUpdate
): Promise<UserPreferences> {
  const response = await fetch(`${API_BASE}/api/auth/preferences`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...buildAuthHeaders(),
    },
    body: JSON.stringify(updates),
  });

  if (!response.ok) {
    if (response.status === 401) {
      clearAuth();
      throw new Error("认证已过期，请重新登录");
    }
    throw new Error(`更新用户偏好失败: ${response.statusText}`);
  }

  const data = (await response.json()) as UserPreferencesResponse;
  return data.preferences;
}

// 本地存储偏好缓存键名
const PREFERENCES_CACHE_KEY = "rewritter.user.preferences";

// 从本地存储读取缓存的偏好
export function getCachedPreferences(): UserPreferences | null {
  try {
    const cached = localStorage.getItem(PREFERENCES_CACHE_KEY);
    if (cached) {
      return JSON.parse(cached) as UserPreferences;
    }
  } catch {
    // 忽略解析错误
  }
  return null;
}

// 缓存偏好到本地存储
export function cachePreferences(preferences: UserPreferences): void {
  try {
    localStorage.setItem(PREFERENCES_CACHE_KEY, JSON.stringify(preferences));
  } catch {
    // 忽略存储错误
  }
}

// 清除缓存的偏好
export function clearCachedPreferences(): void {
  localStorage.removeItem(PREFERENCES_CACHE_KEY);
}
