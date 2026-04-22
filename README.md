# ReWritter - 自动化内容创作与发布系统

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blue" alt="版本">
  <img src="https://img.shields.io/badge/python-3.11-green" alt="Python">
  <img src="https://img.shields.io/badge/react-18.3.1-blue" alt="React">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="许可证">
</p>

## 📖 项目简介

ReWritter 是一个基于 AI 的自动化内容创作与发布系统，集成了大型语言模型、向量检索和自动化发布工作流。系统能够根据用户需求自动生成高质量文章，并支持一键发布到多个平台。

### 核心能力
- 🤖 **智能内容生成**：基于 DeepSeek-V2 模型，结合 RAG 检索增强生成技术
- 🔍 **多源信息整合**：支持联网搜索、向量数据库检索、本地知识库查询
- 📊 **结构化工作流**：使用 LangGraph 定义可编排的内容创作流程
- 🚀 **自动化发布**：集成 Playwright 实现跨平台内容发布
- 📈 **实时监控**：完整的任务状态跟踪和进度可视化

## ✨ 功能特性

### 内容生成
- **主题规划**：基于用户输入自动生成文章大纲和结构
- **多轮优化**：支持多次迭代修改和风格调整
- **事实核查**：集成联网搜索确保内容准确性
- **风格适配**：支持不同平台（公众号、小红书、知乎等）的内容风格

### 工作流管理
- **可视化编排**：基于 LangGraph 的工作流定义和调试
- **异步处理**：Celery 分布式任务队列，支持高并发
- **状态跟踪**：实时任务进度监控和错误处理
- **历史记录**：完整的任务执行日志和结果存储

### 平台集成
- **多平台发布**：支持微信公众号、小红书、知乎等主流平台
- **自动化操作**：基于 Playwright 的浏览器自动化
- **内容格式化**：自动适配各平台的格式要求
- **发布调度**：支持定时发布和批量操作

### 系统管理
- **用户认证**：JWT 令牌认证和权限管理
- **数据统计**：多维度的使用统计和效果分析
- **系统监控**：健康检查、性能监控和告警
- **配置管理**：灵活的环境配置和功能开关

## 🏗️ 技术架构

### 整体架构图
```
┌─────────────────────────────────────────────────────────────┐
│                       前端界面 (React)                       │
├─────────────────────────────────────────────────────────────┤
│                    REST API + WebSocket                     │
├─────────────────────────────────────────────────────────────┤
│                    FastAPI 后端服务                          │
│        ┌──────────┬──────────┬──────────┬──────────┐       │
│        │  认证服务 │ 任务服务  │ 聊天服务  │ 发布服务  │       │
│        └──────────┴──────────┴──────────┴──────────┘       │
├─────────────────────────────────────────────────────────────┤
│                    Celery 异步任务队列                       │
│        ┌──────────────────────────────────────────┐       │
│        │           LangGraph AI 工作流              │       │
│        │  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐    │       │
│        │  │搜索 │→│检索 │→│生成 │→│优化 │    │       │
│        │  └─────┘  └─────┘  └─────┘  └─────┘    │       │
│        └──────────────────────────────────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                   数据存储层                                │
│  ┌───────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐           │
│  │MongoDB│ │Redis │ │Milvus│ │MinIO │ │etcd │           │
│  └───────┘ └──────┘ └──────┘ └──────┘ └──────┘           │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

#### 前端
- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **样式**: Tailwind CSS + CSS Modules
- **状态管理**: React Query + Context API
- **路由**: React Router 6
- **UI 组件**: 自定义组件 + Lucide React 图标

#### 后端
- **Web 框架**: FastAPI (Python 3.11)
- **异步任务**: Celery + Redis
- **AI 工作流**: LangGraph + LangChain
- **API 客户端**: HTTPX + OpenAI SDK
- **认证**: JWT + bcrypt
- **数据验证**: Pydantic v2

#### 数据存储
- **文档数据库**: MongoDB (主数据存储)
- **缓存/消息队列**: Redis
- **向量数据库**: Milvus (向量检索)
- **对象存储**: MinIO (文件存储)
- **配置存储**: etcd (分布式配置)

#### 基础设施
- **容器化**: Docker + Docker Compose
- **自动化测试**: Playwright (E2E 测试)
- **监控**: 内置健康检查端点
- **部署**: 支持容器化部署

## 🚀 快速开始

### 环境要求
- Docker 20.10+ 和 Docker Compose 2.0+
- Node.js 18+ (仅前端开发需要)
- Python 3.11+ (仅本地开发需要)

### 一键启动（推荐）

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd ReWritter
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，设置必要的 API 密钥
   ```

3. **启动所有服务**
   ```bash
   # 启动所有依赖服务和后端
   docker compose up -d redis etcd minio milvus backend
   ```

4. **启动 Celery Worker**
   ```bash
   # Worker 服务需要在 backend 服务启动后单独运行
   docker compose exec backend sh -lc "celery -A app.worker.tasks.celery_app worker --loglevel=info"
   ```

5. **启动前端开发服务器**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

6. **访问应用**
   - 前端界面: http://localhost:5173
   - 后端 API: http://localhost:8001
   - API 文档: http://localhost:8001/docs

### 环境变量配置

关键环境变量说明：

```bash
# AI 服务配置
DEEPSEEK_API_KEY=your_deepseek_api_key          # DeepSeek API 密钥
SILICONFLOW_API_KEY=your_siliconflow_api_key    # 硅基流动 API 密钥（用于 embedding）

# 数据库配置
MONGODB_URI=mongodb://mongodb:27017            # MongoDB 连接地址
MILVUS_HOST=milvus                             # Milvus 向量数据库地址
MILVUS_PORT=19530                              # Milvus 端口

# 第三方服务
AMAP_API_KEY=your_amap_api_key                 # 高德地图 API 密钥
XIAOHONGSHU_USERNAME=your_username             # 小红书账号
XIAOHONGSHU_PASSWORD=your_password             # 小红书密码

# 功能开关
ENABLE_HYBRID_SEARCH=true                      # 启用混合搜索
PLAYWRIGHT_HEADLESS=true                       # 无头浏览器模式
```

完整的环境变量列表请参考 `docker-compose.yml` 文件。

## 📚 API 文档

### 主要接口

#### 认证相关
- `POST /auth/login` - 用户登录
- `POST /auth/register` - 用户注册
- `GET /auth/me` - 获取当前用户信息

#### 任务管理
- `POST /tasks` - 创建新任务
- `GET /tasks` - 获取任务列表
- `GET /tasks/{task_id}` - 获取任务详情
- `PUT /tasks/{task_id}` - 更新任务
- `DELETE /tasks/{task_id}` - 删除任务

#### 内容生成
- `POST /articles` - 创建文章生成任务
- `GET /articles/{article_id}` - 获取文章详情
- `POST /articles/{article_id}/publish` - 发布文章

#### 聊天交互
- `POST /chat/completions` - 发送聊天消息
- `GET /chat/history` - 获取聊天历史

#### 系统管理
- `GET /health` - 健康检查
- `GET /stats` - 系统统计信息

### WebSocket 接口
- `ws://localhost:8001/ws/tasks/{task_id}` - 任务进度实时推送

详细的 API 文档可通过访问 `http://localhost:8001/docs` 查看交互式 Swagger UI。

## 🔧 开发指南

### 项目结构

```
ReWritter/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── agent/             # AI 工作流定义
│   │   │   ├── graph.py       # 基础工作流
│   │   │   └── advanced_graph.py # 高级工作流
│   │   ├── api/               # API 依赖项
│   │   ├── core/              # 核心配置和工具
│   │   ├── repositories/      # 数据访问层
│   │   ├── routers/           # API 路由
│   │   ├── services/          # 业务逻辑层
│   │   ├── worker/            # Celery 任务定义
│   │   └── main.py            # FastAPI 应用入口
│   └── requirements.txt       # Python 依赖
├── frontend/                  # 前端应用
│   ├── src/
│   │   ├── components/        # React 组件
│   │   ├── pages/             # 页面组件
│   │   ├── hooks/             # 自定义 Hooks
│   │   ├── utils/             # 工具函数
│   │   ├── types/             # TypeScript 类型定义
│   │   └── main.tsx           # 应用入口
│   ├── package.json           # 前端依赖
│   └── vite.config.ts         # Vite 配置
├── docker-compose.yml         # Docker Compose 配置
├── .env.example               # 环境变量示例
├── CLAUDE.md                  # Claude Code 开发指南
└── README.md                  # 项目说明文档
```

### 本地开发

#### 后端开发
1. **安装 Python 依赖**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **启动开发服务器**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **启动 Celery Worker**
   ```bash
   celery -A app.worker.tasks.celery_app worker --loglevel=info
   ```

#### 前端开发
1. **安装 Node.js 依赖**
   ```bash
   cd frontend
   npm install
   ```

2. **启动开发服务器**
   ```bash
   npm run dev
   ```

### 添加新的 AI 工作流

1. 在 `backend/app/agent/` 目录下创建新的工作流文件
2. 使用 LangGraph 定义工作流节点和边
3. 在 `backend/app/worker/tasks.py` 中添加对应的 Celery 任务
4. 在 `backend/app/routers/` 中添加 API 路由

示例工作流定义：
```python
from langgraph.graph import StateGraph

def search_node(state):
    # 实现搜索逻辑
    return {"search_results": [...]}

def generate_node(state):
    # 实现生成逻辑
    return {"content": "..."}

# 构建工作流
workflow = StateGraph(...)
workflow.add_node("search", search_node)
workflow.add_node("generate", generate_node)
workflow.add_edge("search", "generate")
```

## 🐳 部署指南

### 生产环境部署

1. **构建 Docker 镜像**
   ```bash
   docker build -t rewritter-backend ./backend
   docker build -t rewritter-frontend ./frontend
   ```

2. **配置生产环境变量**
   ```bash
   # 创建 .env.production 文件
   cp .env.example .env.production
   # 修改为生产环境配置
   ```

3. **使用 Docker Compose 部署**
   ```bash
   # 默认使用 .env 文件，如需使用其他环境文件可添加 --env-file 参数
   docker compose up -d
   ```

4. **配置反向代理（Nginx）**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:5173;
           proxy_set_header Host $host;
       }
       
       location /api {
           proxy_pass http://localhost:8001;
           proxy_set_header Host $host;
       }
   }
   ```

### 监控和维护

- **健康检查**: `GET http://localhost:8001/health`
- **日志查看**: `docker compose logs -f backend`
- **数据库备份**: 定期备份 MongoDB 和 Milvus 数据
- **性能监控**: 集成 Prometheus + Grafana（计划中）

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 开发流程

1. **Fork 项目仓库**
2. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **提交代码变更**
   ```bash
   git commit -m "feat: add your feature"
   ```
4. **推送到分支**
   ```bash
   git push origin feature/your-feature-name
   ```
5. **创建 Pull Request**

### 代码规范

- **Python**: 遵循 PEP 8，使用 Black 格式化
- **TypeScript**: 使用 ESLint + Prettier
- **提交信息**: 遵循 Conventional Commits 规范
- **文档**: 所有公共 API 必须有文档字符串

### 测试要求
- 新增功能必须包含单元测试
- API 变更必须更新 API 文档
- 重大变更需要更新迁移指南

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持与反馈

- **问题反馈**: [GitHub Issues](https://github.com/your-username/rewritter/issues)
- **功能建议**: [GitHub Discussions](https://github.com/your-username/rewritter/discussions)
- **紧急问题**: 通过 Issues 标签 `urgent`

## 🙏 致谢

感谢以下开源项目和服务的支持：

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的 Web 框架
- [LangChain](https://www.langchain.com/) - LLM 应用开发框架
- [DeepSeek](https://www.deepseek.com/) - 深度求索 AI 模型
- [Milvus](https://milvus.io/) - 向量数据库
- [React](https://reactjs.org/) - 前端 UI 库

---

<p align="center">
  Made with ❤️ by the ReWritter Team
</p>
