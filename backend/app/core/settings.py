from __future__ import annotations

import os

AUTH_USERNAME = os.getenv("AUTH_ADMIN_USERNAME", "admin")
AUTH_DEFAULT_PASSWORD = os.getenv("AUTH_ADMIN_PASSWORD", "admin123")
AUTH_USERS_COLLECTION = os.getenv("AUTH_USERS_COLLECTION", "auth_users")
AUTH_LIMITS_COLLECTION = os.getenv("AUTH_LIMITS_COLLECTION", "auth_login_limits")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "rewritter")

CHAT_SESSIONS_COLLECTION = os.getenv("CHAT_SESSIONS_COLLECTION", "chat_sessions")
CHAT_MESSAGES_COLLECTION = os.getenv("CHAT_MESSAGES_COLLECTION", "chat_messages")
MATERIAL_GROUPS_COLLECTION = os.getenv("MATERIAL_GROUPS_COLLECTION", "material_groups")
MATERIAL_FILES_COLLECTION = os.getenv("MATERIAL_FILES_COLLECTION", "material_files")
VENDOR_CONFIGS_COLLECTION = os.getenv("VENDOR_CONFIGS_COLLECTION", "vendor_configs")

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
