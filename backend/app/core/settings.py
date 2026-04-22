from __future__ import annotations

import os


def _to_bool(value: str, default: bool = False) -> bool:
	normalized = value.strip().lower()
	if normalized in {"1", "true", "yes", "on"}:
		return True
	if normalized in {"0", "false", "no", "off"}:
		return False
	return default

AUTH_USERNAME = os.getenv("AUTH_ADMIN_USERNAME", "admin")
AUTH_DEFAULT_PASSWORD = os.getenv("AUTH_ADMIN_PASSWORD", "admin123")
AUTH_USERS_COLLECTION = os.getenv("AUTH_USERS_COLLECTION", "auth_users")
AUTH_LIMITS_COLLECTION = os.getenv("AUTH_LIMITS_COLLECTION", "auth_login_limits")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "rewritter")

CHAT_SESSIONS_COLLECTION = os.getenv("CHAT_SESSIONS_COLLECTION", "chat_sessions")
CHAT_MESSAGES_COLLECTION = os.getenv("CHAT_MESSAGES_COLLECTION", "chat_messages")
WRITING_FLOWS_COLLECTION = os.getenv("WRITING_FLOWS_COLLECTION", "writing_flows")
MATERIAL_GROUPS_COLLECTION = os.getenv("MATERIAL_GROUPS_COLLECTION", "material_groups")
MATERIAL_FILES_COLLECTION = os.getenv("MATERIAL_FILES_COLLECTION", "material_files")
MATERIAL_CHUNKS_COLLECTION = os.getenv("MATERIAL_CHUNKS_COLLECTION", "material_chunks")
VENDOR_CONFIGS_COLLECTION = os.getenv("VENDOR_CONFIGS_COLLECTION", "vendor_configs")
ARTICLES_COLLECTION = os.getenv("ARTICLES_COLLECTION", "articles")
ARTICLE_VERSIONS_COLLECTION = os.getenv("ARTICLE_VERSIONS_COLLECTION", "article_versions")
STATISTICS_COLLECTION = os.getenv("STATISTICS_COLLECTION", "statistics")
PUBLISH_TASKS_COLLECTION = os.getenv("PUBLISH_TASKS_COLLECTION", "publish_tasks")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
DEEPSEEK_DEFAULT_MODEL = os.getenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat").strip() or "deepseek-chat"
DEEPSEEK_REASONER_MODEL = os.getenv("DEEPSEEK_REASONER_MODEL", "deepseek-reasoner").strip() or "deepseek-reasoner"
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "").strip()
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1").strip() or "https://api.siliconflow.cn/v1"
SILICONFLOW_EMBEDDING_MODEL = os.getenv("SILICONFLOW_EMBEDDING_MODEL", "BAAI/bge-m3").strip() or "BAAI/bge-m3"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small").strip() or "text-embedding-3-small"
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))
MILVUS_HOST = os.getenv("MILVUS_HOST", "milvus")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_COLLECTION_MATERIALS = os.getenv("MILVUS_COLLECTION_MATERIALS", "material_chunks")

ENABLE_HYBRID_SEARCH = _to_bool(os.getenv("ENABLE_HYBRID_SEARCH", "true"), default=True)
RAG_HYBRID_ALPHA = float(os.getenv("RAG_HYBRID_ALPHA", "0.6"))
RAG_CANDIDATE_POOL = int(os.getenv("RAG_CANDIDATE_POOL", "12"))

# 高德地图配置
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "").strip()
AMAP_BASE_URL = os.getenv("AMAP_BASE_URL", "https://restapi.amap.com/v3").strip()
AMAP_CACHE_TTL = int(os.getenv("AMAP_CACHE_TTL", "86400"))  # 24小时缓存

# 小红书发布配置
XIAOHONGSHU_USERNAME = os.getenv("XIAOHONGSHU_USERNAME", "").strip()
XIAOHONGSHU_PASSWORD = os.getenv("XIAOHONGSHU_PASSWORD", "").strip()
XIAOHONGSHU_HEADLESS = _to_bool(os.getenv("XIAOHONGSHU_HEADLESS", "true"), default=True)
XIAOHONGSHU_TIMEOUT = int(os.getenv("XIAOHONGSHU_TIMEOUT", "30000"))  # 30秒超时

# Playwright配置
PLAYWRIGHT_BROWSER_TYPE = os.getenv("PLAYWRIGHT_BROWSER_TYPE", "chromium").strip()
PLAYWRIGHT_HEADLESS = _to_bool(os.getenv("PLAYWRIGHT_HEADLESS", "true"), default=True)

# Celery配置
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0").strip()
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1").strip()
