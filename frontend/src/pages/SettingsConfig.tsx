import { useEffect, useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  AlertTriangle,
  ArrowUpDown,
  BadgeCheck,
  Bot,
  Building2,
  CircleAlert,
  CircleCheck,
  Cog,
  Database,
  EyeOff,
  FileText,
  FolderTree,
  KeyRound,
  Network,
  Pencil,
  Plus,
  RefreshCw,
  Server,
  Trash2,
  X
} from "lucide-react";

import type { LayoutOutletContext } from "../Layout";
import {
  listVendorConfigs,
  testDeepSeekVendor,
  testEmbeddingVendor,
  updateVendorConfig,
  type VendorConfig,
} from "../lib/vendor";

type ConfigSectionId =
  | "config-validation"
  | "vendor-management"
  | "embedding-vendor-management"
  | "model-catalog"
  | "llm-config"
  | "datasource-config"
  | "database-config"
  | "system-settings"
  | "api-key-status"
  | "import-export";

interface ConfigSection {
  id: ConfigSectionId;
  label: string;
  hint: string;
  icon: React.ComponentType<{ className?: string }>;
}

type VendorStatus = "enabled" | "disabled";
type VendorActionType = "test" | "enable" | "disable" | "delete";

interface ToastState {
  tone: "success" | "warning" | "danger";
  message: string;
}

interface ConfirmDialogState {
  action: VendorActionType;
  title: string;
  description: string;
  confirmLabel: string;
}

interface VendorInfo {
  vendorId: string;
  displayName: string;
  description: string;
  website: string;
  docsUrl: string;
  apiBase: string;
  apiKeyMask: string;
  keyConfigured: boolean;
  features: {
    chat: boolean;
    completion: boolean;
    embedding: boolean;
    image: boolean;
    vision: boolean;
    functionCalling: boolean;
    streaming: boolean;
  };
  status: VendorStatus;
}

interface EmbeddingVendorForm {
  vendorId: string;
  displayName: string;
  apiBase: string;
  model: string;
  apiKey: string;
  apiKeyMask: string;
  keyConfigured: boolean;
  source: "ui" | "env";
  enabled: boolean;
}

const initialDeepSeekVendor: VendorInfo = {
  vendorId: "deepseek",
  displayName: "DeepSeek",
  description: "DeepSeek 提供高性能的 AI 推理服务",
  website: "https://www.deepseek.com",
  docsUrl: "https://platform.deepseek.com/api-docs",
  apiBase: "https://api.deepseek.com",
  apiKeyMask: "****************",
  keyConfigured: true,
  features: {
    chat: true,
    completion: true,
    embedding: false,
    image: false,
    vision: false,
    functionCalling: true,
    streaming: true
  },
  status: "enabled"
};

const initialEmbeddingVendor: EmbeddingVendorForm = {
  vendorId: "siliconflow",
  displayName: "硅基流动",
  apiBase: "https://api.siliconflow.cn/v1",
  model: "BAAI/bge-m3",
  apiKey: "",
  apiKeyMask: "",
  keyConfigured: false,
  source: "env",
  enabled: true,
};

function cloneVendor(vendor: VendorInfo): VendorInfo {
  return {
    ...vendor,
    features: { ...vendor.features }
  };
}

export default function SettingsConfig() {
  const { locale } = useOutletContext<LayoutOutletContext>();
  const [activeSection, setActiveSection] = useState<ConfigSectionId>("config-validation");
  const [vendor, setVendor] = useState<VendorInfo | null>(initialDeepSeekVendor);
  const [isEditingVendor, setIsEditingVendor] = useState<boolean>(false);
  const [draftVendor, setDraftVendor] = useState<VendorInfo>(cloneVendor(initialDeepSeekVendor));
  const [embeddingVendor, setEmbeddingVendor] = useState<EmbeddingVendorForm>(initialEmbeddingVendor);
  const [testingEmbeddingVendor, setTestingEmbeddingVendor] = useState<boolean>(false);
  const [savingEmbeddingVendor, setSavingEmbeddingVendor] = useState<boolean>(false);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState | null>(null);
  const [testingVendor, setTestingVendor] = useState<boolean>(false);

  const copy =
    locale === "zh"
      ? {
          title: "配置管理",
          subtitle: "管理系统配置、大模型、数据源等设置",
          reload: "重载配置",
          validate: "重新验证",
          save: "更新",
          cancel: "取消",
          requiredTitle: "必需配置",
          optionalTitle: "推荐配置",
          featureLabels: {
            chat: "对话",
            completion: "文本补全",
            embedding: "向量化",
            image: "图像生成",
            vision: "图像理解",
            functionCalling: "函数调用",
            streaming: "流式输出"
          },
          vendorSection: {
            addVendor: "添加厂家",
            editVendor: "编辑厂家信息",
            deleteConfirm: "确认删除",
            confirmTitle: "操作确认",
            confirmCancel: "取消",
            emptyVendorTitle: "当前暂无厂家配置",
            emptyVendorDesc: "你可以先添加 deepseek 厂家配置。",
            listTitle: "大模型厂家管理",
            listDesc: "当前仅接入 DeepSeek，可在此查看状态并编辑厂家基础信息。",
            headers: {
              info: "厂家信息",
              apiKey: "API 密钥",
              description: "描述",
              status: "状态",
              features: "支持功能",
              actions: "操作"
            },
            configured: "已配置",
            missing: "未配置",
            statusEnabled: "启用",
            statusDisabled: "禁用",
            actions: {
              edit: "编辑",
              test: "测试",
              disable: "禁用",
              enable: "启用",
              delete: "删除"
            },
            fields: {
              vendorId: "厂家 ID",
              displayName: "显示名称",
              description: "描述",
              website: "官网",
              docsUrl: "API 文档",
              apiBase: "默认 API 地址",
              apiKey: "API Key",
              status: "状态",
              keyStatus: "密钥状态"
            },
            vendorIdHint: "厂家的唯一标识符，创建后不可修改",
            securityTitle: "安全提示",
            securityDesc: "敏感密钥建议通过环境变量或运维配置注入，此处仅展示掩码。",
            pageHint: "仅支持 deepseek 厂家，后续可扩展多厂家。"
          },
          embeddingSection: {
            title: "Embedding 厂家管理",
            desc: "前端填写优先，未填写则自动回退到 .env 中的硅基流动配置。",
            vendorId: "厂家 ID",
            displayName: "显示名称",
            apiBase: "API 地址",
            model: "Embedding 模型",
            apiKey: "API Key",
            keyHint: "留空表示使用 .env 中的 SILICONFLOW_API_KEY",
            sourceUi: "来源：前端配置",
            sourceEnv: "来源：.env",
            save: "保存配置",
            test: "测试连接",
            testing: "测试中...",
            saving: "保存中..."
          },
          sections: [
            {
              id: "config-validation",
              label: "配置验证",
              hint: "检查当前配置完整性",
              icon: BadgeCheck
            },
            {
              id: "vendor-management",
              label: "厂家管理",
              hint: "配置模型厂商接入",
              icon: Building2
            },
            {
              id: "embedding-vendor-management",
              label: "Embedding 厂家",
              hint: "管理向量化厂家密钥",
              icon: Database
            },
            {
              id: "model-catalog",
              label: "模型目录",
              hint: "查看与管理模型清单",
              icon: FolderTree
            },
            {
              id: "llm-config",
              label: "大模型配置",
              hint: "设置推理参数与策略",
              icon: Bot
            },
            {
              id: "datasource-config",
              label: "数据源配置",
              hint: "连接检索与外部数据",
              icon: Network
            },
            {
              id: "database-config",
              label: "数据库配置",
              hint: "设置数据库连接项",
              icon: Database
            },
            {
              id: "system-settings",
              label: "系统设置",
              hint: "全局策略与运行设置",
              icon: Cog
            },
            {
              id: "api-key-status",
              label: "API 密钥状态",
              hint: "查看密钥可用性",
              icon: KeyRound
            },
            {
              id: "import-export",
              label: "导入导出",
              hint: "配置项迁移与备份",
              icon: ArrowUpDown
            }
          ] as ConfigSection[],
          statusBannerTitle: "配置验证通过（有推荐配置未设置）",
          statusLines: ["缺少 2 个推荐配置", "9 个 MongoDB 配置警告"],
          requiredItems: [
            { title: "MongoDB 主机", desc: "MongoDB 数据库主机地址", status: "已配置" },
            { title: "MongoDB 端口", desc: "MongoDB 数据库端口", status: "已配置" },
            { title: "MongoDB 数据库", desc: "MongoDB 数据库名", status: "已配置" }
          ],
          optionalItems: [
            { title: "MongoDB 用户名", desc: "建议配置鉴权用户名", status: "未配置" },
            { title: "MongoDB 密码", desc: "建议配置鉴权密码", status: "未配置" }
          ],
          placeholderTitle: "功能建设中",
          placeholderDesc: "该模块已完成框架搭建，下一步可接入后端真实配置接口。"
        }
      : {
          title: "Configuration Manager",
          subtitle: "Manage system settings, LLMs, and data source configuration",
          reload: "Reload Config",
          validate: "Revalidate",
          save: "Update",
          cancel: "Cancel",
          requiredTitle: "Required Configuration",
          optionalTitle: "Recommended Configuration",
          featureLabels: {
            chat: "Chat",
            completion: "Completion",
            embedding: "Embedding",
            image: "Image",
            vision: "Vision",
            functionCalling: "Function Calling",
            streaming: "Streaming"
          },
          vendorSection: {
            addVendor: "Add Vendor",
            editVendor: "Edit Vendor",
            deleteConfirm: "Confirm Delete",
            confirmTitle: "Action Confirmation",
            confirmCancel: "Cancel",
            emptyVendorTitle: "No vendor configured",
            emptyVendorDesc: "You can add deepseek vendor first.",
            listTitle: "LLM Vendor Management",
            listDesc: "Only DeepSeek is configured for now. You can inspect and edit vendor metadata here.",
            headers: {
              info: "Vendor",
              apiKey: "API Key",
              description: "Description",
              status: "Status",
              features: "Features",
              actions: "Actions"
            },
            configured: "Configured",
            missing: "Missing",
            statusEnabled: "Enabled",
            statusDisabled: "Disabled",
            actions: {
              edit: "Edit",
              test: "Test",
              disable: "Disable",
              enable: "Enable",
              delete: "Delete"
            },
            fields: {
              vendorId: "Vendor ID",
              displayName: "Display Name",
              description: "Description",
              website: "Website",
              docsUrl: "API Docs",
              apiBase: "Default API Base",
              apiKey: "API Key",
              status: "Status",
              keyStatus: "Key Status"
            },
            vendorIdHint: "Unique vendor key, immutable after creation",
            securityTitle: "Security Note",
            securityDesc: "Sensitive keys should come from environment or ops config; masked only here.",
            pageHint: "Currently only deepseek is supported; multi-vendor can be added later."
          },
          embeddingSection: {
            title: "Embedding Vendor Management",
            desc: "Frontend value has priority; fallback to .env SiliconFlow config if missing.",
            vendorId: "Vendor ID",
            displayName: "Display Name",
            apiBase: "API Base",
            model: "Embedding Model",
            apiKey: "API Key",
            keyHint: "Leave blank to fallback to SILICONFLOW_API_KEY in .env",
            sourceUi: "Source: frontend config",
            sourceEnv: "Source: .env",
            save: "Save",
            test: "Test",
            testing: "Testing...",
            saving: "Saving..."
          },
          sections: [
            {
              id: "config-validation",
              label: "Configuration Validation",
              hint: "Check current setup completeness",
              icon: BadgeCheck
            },
            {
              id: "vendor-management",
              label: "Vendor Management",
              hint: "Configure provider integrations",
              icon: Building2
            },
            {
              id: "embedding-vendor-management",
              label: "Embedding Vendor",
              hint: "Manage embedding keys",
              icon: Database
            },
            {
              id: "model-catalog",
              label: "Model Catalog",
              hint: "Browse and maintain model list",
              icon: FolderTree
            },
            {
              id: "llm-config",
              label: "LLM Configuration",
              hint: "Tune inference settings",
              icon: Bot
            },
            {
              id: "datasource-config",
              label: "Data Source Configuration",
              hint: "Connect retrieval and external data",
              icon: Network
            },
            {
              id: "database-config",
              label: "Database Configuration",
              hint: "Configure database connection fields",
              icon: Database
            },
            {
              id: "system-settings",
              label: "System Settings",
              hint: "Global strategy and runtime behavior",
              icon: Cog
            },
            {
              id: "api-key-status",
              label: "API Key Status",
              hint: "Track key availability",
              icon: KeyRound
            },
            {
              id: "import-export",
              label: "Import / Export",
              hint: "Migration and backup",
              icon: ArrowUpDown
            }
          ] as ConfigSection[],
          statusBannerTitle: "Validation succeeded (recommended config missing)",
          statusLines: ["2 recommended items are missing", "9 MongoDB warnings"],
          requiredItems: [
            { title: "MongoDB Host", desc: "MongoDB database host", status: "Configured" },
            { title: "MongoDB Port", desc: "MongoDB database port", status: "Configured" },
            { title: "MongoDB Database", desc: "MongoDB database name", status: "Configured" }
          ],
          optionalItems: [
            { title: "MongoDB Username", desc: "Recommended for authentication", status: "Missing" },
            { title: "MongoDB Password", desc: "Recommended for authentication", status: "Missing" }
          ],
          placeholderTitle: "Coming Soon",
          placeholderDesc: "The module shell is ready. Next step is backend API integration."
        };

  const activeSectionMeta = useMemo(
    () => copy.sections.find((section) => section.id === activeSection) ?? copy.sections[0],
    [activeSection, copy.sections]
  );

  const hydrateVendorsFromConfig = (items: VendorConfig[]) => {
    const chat = items.find((item) => item.capability === "chat");
    const embedding = items.find((item) => item.capability === "embedding");

    if (chat) {
      const hydratedChat: VendorInfo = {
        ...initialDeepSeekVendor,
        vendorId: chat.vendor_id,
        displayName: chat.display_name,
        apiBase: chat.api_base,
        keyConfigured: chat.key_configured,
        apiKeyMask: chat.api_key_mask || "",
        status: chat.enabled ? "enabled" : "disabled",
      };
      setVendor(hydratedChat);
      setDraftVendor(cloneVendor(hydratedChat));
    }

    if (embedding) {
      setEmbeddingVendor({
        vendorId: embedding.vendor_id,
        displayName: embedding.display_name,
        apiBase: embedding.api_base,
        model: embedding.model,
        apiKey: "",
        apiKeyMask: embedding.api_key_mask || "",
        keyConfigured: embedding.key_configured,
        source: embedding.source,
        enabled: embedding.enabled,
      });
    }
  };

  useEffect(() => {
    const loadConfigs = async () => {
      try {
        const configs = await listVendorConfigs();
        hydrateVendorsFromConfig(configs);
      } catch {
        setToast({ tone: "warning", message: locale === "zh" ? "加载厂家配置失败，使用默认值" : "Failed to load vendor config" });
      }
    };
    void loadConfigs();
  }, [locale]);

  useEffect(() => {
    if (!toast) {
      return;
    }
    const timer = window.setTimeout(() => setToast(null), 2200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const vendorFeatureKeys = useMemo(
    () => Object.keys(copy.featureLabels) as Array<keyof VendorInfo["features"]>,
    [copy.featureLabels]
  );

  const openVendorEditor = () => {
    if (!vendor) {
      return;
    }
    setDraftVendor(cloneVendor(vendor));
    setIsEditingVendor(true);
  };

  const closeVendorEditor = () => {
    if (vendor) {
      setDraftVendor(cloneVendor(vendor));
    }
    setIsEditingVendor(false);
  };

  const saveVendorEditor = async () => {
    try {
      const saved = await updateVendorConfig("chat", {
        capability: "chat",
        vendor_id: draftVendor.vendorId,
        display_name: draftVendor.displayName,
        api_base: draftVendor.apiBase,
        model: "deepseek-chat",
        enabled: draftVendor.status === "enabled",
        api_key: "",
      });

      const nextVendor = {
        ...cloneVendor(draftVendor),
        keyConfigured: saved.key_configured,
        apiKeyMask: saved.api_key_mask || draftVendor.apiKeyMask,
        status: saved.enabled ? "enabled" : "disabled",
      } satisfies VendorInfo;

      setVendor(nextVendor);
      setDraftVendor(cloneVendor(nextVendor));
      setIsEditingVendor(false);
      setToast({ tone: "success", message: locale === "zh" ? "厂家信息已更新" : "Vendor information updated" });
    } catch (error) {
      setToast({
        tone: "danger",
        message: error instanceof Error ? error.message : locale === "zh" ? "保存厂家失败" : "Failed to save vendor",
      });
    }
  };

  const restoreVendor = () => {
    const restored = cloneVendor(initialDeepSeekVendor);
    setVendor(restored);
    setDraftVendor(cloneVendor(restored));
    setToast({ tone: "success", message: locale === "zh" ? "DeepSeek 已添加" : "DeepSeek added" });
  };

  const requestActionConfirm = (action: VendorActionType) => {
    if (!vendor) {
      return;
    }

    const textMap =
      locale === "zh"
        ? {
            test: {
              title: "确认测试连接？",
              description: "将使用当前厂家配置执行一次连通性测试。",
              confirmLabel: "开始测试"
            },
            enable: {
              title: "确认启用厂家？",
              description: "启用后可用于模型调用与路由。",
              confirmLabel: copy.vendorSection.actions.enable
            },
            disable: {
              title: "确认禁用厂家？",
              description: "禁用后将停止该厂家模型的在线调用。",
              confirmLabel: copy.vendorSection.actions.disable
            },
            delete: {
              title: "确认删除厂家？",
              description: "删除后厂家配置将从当前列表中移除。",
              confirmLabel: copy.vendorSection.deleteConfirm
            }
          }
        : {
            test: {
              title: "Confirm test connection?",
              description: "A connectivity check will run with current vendor settings.",
              confirmLabel: "Start Test"
            },
            enable: {
              title: "Confirm enable vendor?",
              description: "Enabled vendor can be used in model routing.",
              confirmLabel: copy.vendorSection.actions.enable
            },
            disable: {
              title: "Confirm disable vendor?",
              description: "Disabled vendor will stop receiving calls.",
              confirmLabel: copy.vendorSection.actions.disable
            },
            delete: {
              title: "Confirm delete vendor?",
              description: "Vendor config will be removed from current list.",
              confirmLabel: copy.vendorSection.deleteConfirm
            }
          };

    setConfirmDialog({ action, ...textMap[action] });
  };

  const runConfirmedAction = async () => {
    if (!confirmDialog || !vendor) {
      return;
    }

    if (confirmDialog.action === "test") {
      setTestingVendor(true);
      try {
        const result = await testDeepSeekVendor({
          model: "deepseek-chat",
          enableThinking: false,
        });

        setVendor((prev) => {
          if (!prev) {
            return prev;
          }
          const updated = {
            ...prev,
            keyConfigured: result.configured,
            apiBase: prev.apiBase,
          };
          setDraftVendor((draftPrev) => ({ ...draftPrev, keyConfigured: result.configured }));
          return updated;
        });

        const latencyText = typeof result.latency_ms === "number" ? ` (${result.latency_ms}ms)` : "";
        const message =
          locale === "zh"
            ? `${result.ok ? "连接测试通过" : "连接测试失败"}${latencyText}：${result.message}`
            : `${result.ok ? "Connection test passed" : "Connection test failed"}${latencyText}: ${result.message}`;

        setToast({
          tone: result.ok ? "success" : "warning",
          message,
        });
      } catch (error) {
        setToast({
          tone: "danger",
          message: error instanceof Error ? error.message : locale === "zh" ? "连接测试失败" : "Connection test failed",
        });
      } finally {
        setTestingVendor(false);
      }
    }

    if (confirmDialog.action === "enable") {
      try {
        const target = vendor;
        const saved = await updateVendorConfig("chat", {
          capability: "chat",
          vendor_id: target.vendorId,
          display_name: target.displayName,
          api_base: target.apiBase,
          model: "deepseek-chat",
          enabled: true,
          api_key: "",
        });
        setVendor((prev) => (prev ? { ...prev, status: saved.enabled ? "enabled" : "disabled" } : prev));
        setToast({ tone: "success", message: locale === "zh" ? "厂家已启用" : "Vendor enabled" });
      } catch (error) {
        setToast({
          tone: "danger",
          message: error instanceof Error ? error.message : locale === "zh" ? "启用失败" : "Enable failed",
        });
      }
    }

    if (confirmDialog.action === "disable") {
      try {
        const target = vendor;
        const saved = await updateVendorConfig("chat", {
          capability: "chat",
          vendor_id: target.vendorId,
          display_name: target.displayName,
          api_base: target.apiBase,
          model: "deepseek-chat",
          enabled: false,
          api_key: "",
        });
        setVendor((prev) => (prev ? { ...prev, status: saved.enabled ? "enabled" : "disabled" } : prev));
        setToast({ tone: "warning", message: locale === "zh" ? "厂家已禁用" : "Vendor disabled" });
      } catch (error) {
        setToast({
          tone: "danger",
          message: error instanceof Error ? error.message : locale === "zh" ? "禁用失败" : "Disable failed",
        });
      }
    }

    if (confirmDialog.action === "delete") {
      setVendor(null);
      setIsEditingVendor(false);
      setToast({ tone: "danger", message: locale === "zh" ? "厂家已删除" : "Vendor deleted" });
    }

    setConfirmDialog(null);
  };

  const saveEmbeddingVendorConfig = async () => {
    setSavingEmbeddingVendor(true);
    try {
      const saved = await updateVendorConfig("embedding", {
        capability: "embedding",
        vendor_id: embeddingVendor.vendorId,
        display_name: embeddingVendor.displayName,
        api_base: embeddingVendor.apiBase,
        model: embeddingVendor.model,
        enabled: embeddingVendor.enabled,
        api_key: embeddingVendor.apiKey.trim(),
      });
      setEmbeddingVendor((prev) => ({
        ...prev,
        keyConfigured: saved.key_configured,
        apiKeyMask: saved.api_key_mask,
        source: saved.source,
        apiKey: "",
      }));
      setToast({ tone: "success", message: locale === "zh" ? "Embedding 厂家配置已保存" : "Embedding vendor saved" });
    } catch (error) {
      setToast({
        tone: "danger",
        message: error instanceof Error ? error.message : locale === "zh" ? "保存失败" : "Save failed",
      });
    } finally {
      setSavingEmbeddingVendor(false);
    }
  };

  const runEmbeddingVendorTest = async () => {
    setTestingEmbeddingVendor(true);
    try {
      const result = await testEmbeddingVendor();
      const latencyText = typeof result.latency_ms === "number" ? ` (${result.latency_ms}ms)` : "";
      setToast({
        tone: result.ok ? "success" : "warning",
        message:
          locale === "zh"
            ? `${result.ok ? "连接测试通过" : "连接测试失败"}${latencyText}：${result.message}`
            : `${result.ok ? "Connection test passed" : "Connection test failed"}${latencyText}: ${result.message}`,
      });
      const configs = await listVendorConfigs();
      hydrateVendorsFromConfig(configs);
    } catch (error) {
      setToast({
        tone: "danger",
        message: error instanceof Error ? error.message : locale === "zh" ? "测试失败" : "Test failed",
      });
    } finally {
      setTestingEmbeddingVendor(false);
    }
  };

  const renderEmbeddingVendorManagement = () => {
    return (
      <div className="space-y-5">
        <header>
          <h4 className="text-xl font-semibold text-[hsl(var(--foreground))]">{copy.embeddingSection.title}</h4>
          <p className="mt-1 text-sm text-slate-300">{copy.embeddingSection.desc}</p>
        </header>

        <div className="grid gap-4 lg:grid-cols-2">
          <label className="grid gap-2 text-sm font-medium text-slate-200">
            {copy.embeddingSection.vendorId}
            <input
              value={embeddingVendor.vendorId}
              onChange={(event) => setEmbeddingVendor((prev) => ({ ...prev, vendorId: event.target.value }))}
              className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
            />
          </label>

          <label className="grid gap-2 text-sm font-medium text-slate-200">
            {copy.embeddingSection.displayName}
            <input
              value={embeddingVendor.displayName}
              onChange={(event) => setEmbeddingVendor((prev) => ({ ...prev, displayName: event.target.value }))}
              className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
            />
          </label>

          <label className="grid gap-2 text-sm font-medium text-slate-200 lg:col-span-2">
            {copy.embeddingSection.apiBase}
            <input
              value={embeddingVendor.apiBase}
              onChange={(event) => setEmbeddingVendor((prev) => ({ ...prev, apiBase: event.target.value }))}
              className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
            />
          </label>

          <label className="grid gap-2 text-sm font-medium text-slate-200">
            {copy.embeddingSection.model}
            <input
              value={embeddingVendor.model}
              onChange={(event) => setEmbeddingVendor((prev) => ({ ...prev, model: event.target.value }))}
              className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
            />
          </label>

          <label className="grid gap-2 text-sm font-medium text-slate-200">
            {copy.embeddingSection.apiKey}
            <input
              value={embeddingVendor.apiKey}
              onChange={(event) => setEmbeddingVendor((prev) => ({ ...prev, apiKey: event.target.value }))}
              placeholder={embeddingVendor.apiKeyMask || "sk-..."}
              className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
            />
            <span className="text-xs text-slate-400">{copy.embeddingSection.keyHint}</span>
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md border border-cyan-400/30 bg-cyan-500/15 px-2 py-1 text-xs text-cyan-100">
            {embeddingVendor.source === "ui" ? copy.embeddingSection.sourceUi : copy.embeddingSection.sourceEnv}
          </span>
          <span
            className={[
              "rounded-md border px-2 py-1 text-xs font-semibold",
              embeddingVendor.keyConfigured
                ? "border-emerald-400/35 bg-emerald-500/20 text-emerald-200"
                : "border-rose-400/35 bg-rose-500/15 text-rose-200",
            ].join(" ")}
          >
            {embeddingVendor.keyConfigured ? copy.vendorSection.configured : copy.vendorSection.missing}
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => {
              void saveEmbeddingVendorConfig();
            }}
            disabled={savingEmbeddingVendor}
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:opacity-60"
          >
            <Pencil className="h-4 w-4" />
            {savingEmbeddingVendor ? copy.embeddingSection.saving : copy.embeddingSection.save}
          </button>

          <button
            type="button"
            onClick={() => {
              void runEmbeddingVendorTest();
            }}
            disabled={testingEmbeddingVendor}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/10 disabled:opacity-60"
          >
            <RefreshCw className={["h-4 w-4", testingEmbeddingVendor ? "animate-spin" : ""].join(" ")} />
            {testingEmbeddingVendor ? copy.embeddingSection.testing : copy.embeddingSection.test}
          </button>
        </div>
      </div>
    );
  };

  const renderVendorManagement = () => {
    if (!isEditingVendor) {
      return (
        <div className="space-y-5">
          <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h4 className="text-xl font-semibold text-[hsl(var(--foreground))]">{copy.vendorSection.listTitle}</h4>
              <p className="mt-1 text-sm text-slate-300">{copy.vendorSection.listDesc}</p>
            </div>

            <button
              type="button"
              onClick={() => {
                if (!vendor) {
                  restoreVendor();
                }
              }}
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/10"
            >
              <Plus className="h-4 w-4" />
              {copy.vendorSection.addVendor}
            </button>
          </header>

          {!vendor ? (
            <div className="rounded-2xl border border-dashed border-white/15 bg-black/20 p-8 text-center">
              <h5 className="text-lg font-semibold text-[hsl(var(--foreground))]">{copy.vendorSection.emptyVendorTitle}</h5>
              <p className="mt-2 text-sm text-slate-300">{copy.vendorSection.emptyVendorDesc}</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-white/10 bg-black/20">
            <table className="min-w-full divide-y divide-white/10 text-sm">
              <thead className="bg-white/5 text-left text-slate-300">
                <tr>
                  <th className="px-4 py-3 font-semibold">{copy.vendorSection.headers.info}</th>
                  <th className="px-4 py-3 font-semibold">{copy.vendorSection.headers.apiKey}</th>
                  <th className="px-4 py-3 font-semibold">{copy.vendorSection.headers.description}</th>
                  <th className="px-4 py-3 font-semibold">{copy.vendorSection.headers.status}</th>
                  <th className="px-4 py-3 font-semibold">{copy.vendorSection.headers.features}</th>
                  <th className="px-4 py-3 font-semibold">{copy.vendorSection.headers.actions}</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-white/10">
                <tr>
                  <td className="px-4 py-4 align-top">
                    <p className="text-xl font-semibold text-[hsl(var(--foreground))]">{vendor.displayName}</p>
                    <p className="mt-1 text-sm text-slate-400">{vendor.vendorId}</p>
                  </td>
                  <td className="px-4 py-4 align-top">
                    <span
                      className={[
                        "rounded-md border px-2 py-1 text-xs font-semibold",
                        vendor.keyConfigured
                          ? "border-emerald-400/35 bg-emerald-500/20 text-emerald-200"
                          : "border-rose-400/35 bg-rose-500/15 text-rose-200"
                      ].join(" ")}
                    >
                      {vendor.keyConfigured ? copy.vendorSection.configured : copy.vendorSection.missing}
                    </span>
                  </td>
                  <td className="max-w-[340px] px-4 py-4 align-top text-base leading-7 text-slate-200">{vendor.description}</td>
                  <td className="px-4 py-4 align-top">
                    <span
                      className={[
                        "rounded-md border px-2 py-1 text-xs font-semibold",
                        vendor.status === "enabled"
                          ? "border-emerald-400/35 bg-emerald-500/20 text-emerald-200"
                          : "border-rose-400/35 bg-rose-500/15 text-rose-200"
                      ].join(" ")}
                    >
                      {vendor.status === "enabled" ? copy.vendorSection.statusEnabled : copy.vendorSection.statusDisabled}
                    </span>
                  </td>
                  <td className="px-4 py-4 align-top">
                    <div className="flex max-w-[340px] flex-wrap gap-2">
                      {vendorFeatureKeys
                        .filter((featureKey) => vendor.features[featureKey])
                        .map((featureKey) => (
                          <span
                            key={featureKey}
                            className="rounded-md border border-sky-400/35 bg-sky-500/15 px-2 py-0.5 text-xs font-medium text-sky-200"
                          >
                            {copy.featureLabels[featureKey]}
                          </span>
                        ))}
                    </div>
                  </td>
                  <td className="px-4 py-4 align-top">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={openVendorEditor}
                        className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:bg-white/10"
                      >
                        {copy.vendorSection.actions.edit}
                      </button>
                      <button
                        type="button"
                        onClick={() => requestActionConfirm("test")}
                        className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:bg-white/10"
                      >
                        {copy.vendorSection.actions.test}
                      </button>
                      <button
                        type="button"
                        onClick={() => requestActionConfirm(vendor.status === "enabled" ? "disable" : "enable")}
                        className={[
                          "rounded-lg border px-3 py-1.5 text-xs font-semibold",
                          vendor.status === "enabled"
                            ? "border-amber-400/35 bg-amber-500/20 text-amber-200"
                            : "border-emerald-400/35 bg-emerald-500/20 text-emerald-200"
                        ].join(" ")}
                      >
                        {vendor.status === "enabled" ? copy.vendorSection.actions.disable : copy.vendorSection.actions.enable}
                      </button>
                      <button
                        type="button"
                        onClick={() => requestActionConfirm("delete")}
                        className="rounded-lg border border-rose-400/35 bg-rose-500/15 px-3 py-1.5 text-xs font-semibold text-rose-200"
                      >
                        {copy.vendorSection.actions.delete}
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          )}

          <p className="text-xs text-slate-400">{copy.vendorSection.pageHint}</p>
        </div>
      );
    }

    return null;
  };

  return (
    <>
      <section className="space-y-5">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-3xl font-semibold text-[hsl(var(--foreground))]">{copy.title}</h2>
          <p className="mt-2 text-sm text-slate-300">{copy.subtitle}</p>
        </div>

        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/10"
        >
          <RefreshCw className="h-4 w-4" />
          {copy.reload}
        </button>
      </header>

      <div className="grid gap-4 xl:grid-cols-[250px_1fr]">
        <aside className="panel rounded-2xl p-3">
          <div className="space-y-2">
            {copy.sections.map((section) => {
              const Icon = section.icon;
              const isActive = section.id === activeSection;

              return (
                <button
                  key={section.id}
                  type="button"
                  onClick={() => {
                    setActiveSection(section.id);
                    if (section.id !== "vendor-management") {
                      setIsEditingVendor(false);
                    }
                  }}
                  className={[
                    "w-full rounded-xl border px-3 py-3 text-left transition",
                    isActive
                      ? "border-cyan-300/65 bg-cyan-400/15"
                      : "border-transparent bg-transparent hover:border-white/10 hover:bg-white/5"
                  ].join(" ")}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={[
                        "inline-flex h-8 w-8 items-center justify-center rounded-lg",
                        isActive ? "bg-cyan-300/20 text-cyan-200" : "bg-white/5 text-slate-400"
                      ].join(" ")}
                    >
                      <Icon className="h-4 w-4" />
                    </span>
                    <span>
                      <span className="block text-sm font-semibold text-[hsl(var(--foreground))]">{section.label}</span>
                      <span className="mt-0.5 block text-xs text-slate-400">{section.hint}</span>
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        <section className="panel rounded-2xl p-5 md:p-6">
          <header className="mb-5 flex items-center justify-between border-b border-white/10 pb-4">
            <h3 className="text-2xl font-semibold text-[hsl(var(--foreground))]">{activeSectionMeta.label}</h3>

            <button
              type="button"
              onClick={() => {
                if (activeSection === "vendor-management") {
                  if (vendor) {
                    openVendorEditor();
                  } else {
                    restoreVendor();
                  }
                  return;
                }
                if (activeSection === "embedding-vendor-management") {
                  void runEmbeddingVendorTest();
                  return;
                }
              }}
              className={[
                "inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition",
                activeSection === "vendor-management" || activeSection === "embedding-vendor-management"
                  ? "border border-white/10 bg-white/5 text-slate-200 hover:bg-white/10"
                  : "bg-cyan-500 text-slate-950 hover:bg-cyan-400"
              ].join(" ")}
            >
              {activeSection === "vendor-management" ? <Pencil className="h-4 w-4" /> : <RefreshCw className="h-4 w-4" />}
              {activeSection === "vendor-management"
                ? copy.vendorSection.editVendor
                : activeSection === "embedding-vendor-management"
                  ? copy.embeddingSection.test
                  : copy.validate}
            </button>
          </header>

          {activeSection === "config-validation" ? (
            <div className="space-y-6">
              <article className="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4">
                <div className="flex items-start gap-3">
                  <CircleAlert className="mt-1 h-5 w-5 text-amber-300" />
                  <div>
                    <h4 className="text-xl font-semibold text-amber-300">{copy.statusBannerTitle}</h4>
                    <ul className="mt-2 space-y-1 text-sm text-amber-200/90">
                      {copy.statusLines.map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </article>

              <section>
                <h4 className="text-xl font-semibold text-[hsl(var(--foreground))]">{copy.requiredTitle}</h4>
                <div className="mt-3 space-y-3">
                  {copy.requiredItems.map((item) => (
                    <article
                      key={item.title}
                      className="rounded-2xl border border-emerald-400/40 bg-emerald-500/10 px-4 py-4 md:px-5"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <BadgeCheck className="mt-1 h-5 w-5 text-emerald-300" />
                          <div>
                            <p className="text-2xl font-semibold text-[hsl(var(--foreground))] md:text-3xl">{item.title}</p>
                            <p className="mt-1 text-base text-slate-300 md:text-lg">{item.desc}</p>
                          </div>
                        </div>
                        <span className="shrink-0 rounded-lg border border-emerald-400/35 bg-emerald-500/20 px-3 py-1 text-sm font-semibold text-emerald-200">
                          {item.status}
                        </span>
                      </div>
                    </article>
                  ))}
                </div>
              </section>

              <section>
                <h4 className="text-xl font-semibold text-[hsl(var(--foreground))]">{copy.optionalTitle}</h4>
                <div className="mt-3 space-y-3">
                  {copy.optionalItems.map((item) => (
                    <article
                      key={item.title}
                      className="rounded-2xl border border-slate-500/35 bg-white/5 px-4 py-4 md:px-5"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <Server className="mt-1 h-5 w-5 text-slate-300" />
                          <div>
                            <p className="text-lg font-semibold text-[hsl(var(--foreground))]">{item.title}</p>
                            <p className="mt-1 text-sm text-slate-300">{item.desc}</p>
                          </div>
                        </div>
                        <span className="shrink-0 rounded-lg border border-slate-500/45 bg-white/5 px-3 py-1 text-xs font-semibold text-slate-300">
                          {item.status}
                        </span>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            </div>
          ) : activeSection === "vendor-management" ? (
            renderVendorManagement()
          ) : activeSection === "embedding-vendor-management" ? (
            renderEmbeddingVendorManagement()
          ) : (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-center">
              <h4 className="text-lg font-semibold text-[hsl(var(--foreground))]">{copy.placeholderTitle}</h4>
              <p className="mt-2 text-sm text-slate-300">{copy.placeholderDesc}</p>
            </div>
          )}
        </section>
      </div>
      </section>

      {activeSection === "vendor-management" && isEditingVendor && vendor && (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="absolute inset-0 bg-black/65 backdrop-blur-sm" onClick={closeVendorEditor} />

        <div className="panel relative z-10 max-h-[88vh] w-full max-w-4xl overflow-y-auto rounded-2xl p-5 md:p-6">
          <header className="flex items-center justify-between border-b border-white/10 pb-4">
            <h4 className="text-xl font-semibold text-[hsl(var(--foreground))]">{copy.vendorSection.editVendor}</h4>
            <button
              type="button"
              onClick={closeVendorEditor}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-slate-300 transition hover:bg-white/10"
            >
              <X className="h-4 w-4" />
            </button>
          </header>

          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <label className="grid gap-2 text-sm font-medium text-slate-200">
              {copy.vendorSection.fields.vendorId}
              <input
                value={draftVendor.vendorId}
                readOnly
                className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-slate-300"
              />
              <span className="text-xs text-slate-400">{copy.vendorSection.vendorIdHint}</span>
            </label>

            <label className="grid gap-2 text-sm font-medium text-slate-200">
              {copy.vendorSection.fields.displayName}
              <input
                value={draftVendor.displayName}
                onChange={(event) => setDraftVendor((prev) => ({ ...prev, displayName: event.target.value }))}
                className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
              />
            </label>

            <label className="grid gap-2 text-sm font-medium text-slate-200 lg:col-span-2">
              {copy.vendorSection.fields.description}
              <textarea
                value={draftVendor.description}
                onChange={(event) => setDraftVendor((prev) => ({ ...prev, description: event.target.value }))}
                rows={3}
                className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
              />
            </label>

            <label className="grid gap-2 text-sm font-medium text-slate-200">
              {copy.vendorSection.fields.website}
              <input
                value={draftVendor.website}
                onChange={(event) => setDraftVendor((prev) => ({ ...prev, website: event.target.value }))}
                className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
              />
            </label>

            <label className="grid gap-2 text-sm font-medium text-slate-200">
              {copy.vendorSection.fields.docsUrl}
              <input
                value={draftVendor.docsUrl}
                onChange={(event) => setDraftVendor((prev) => ({ ...prev, docsUrl: event.target.value }))}
                className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
              />
            </label>

            <label className="grid gap-2 text-sm font-medium text-slate-200 lg:col-span-2">
              {copy.vendorSection.fields.apiBase}
              <input
                value={draftVendor.apiBase}
                onChange={(event) => setDraftVendor((prev) => ({ ...prev, apiBase: event.target.value }))}
                className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-[hsl(var(--foreground))] outline-none ring-[hsl(var(--ring))] transition focus:ring-2"
              />
            </label>
          </div>

          <article className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="flex items-start gap-3">
              <FileText className="mt-1 h-5 w-5 text-cyan-300" />
              <div>
                <p className="text-base font-semibold text-[hsl(var(--foreground))]">{copy.vendorSection.securityTitle}</p>
                <p className="mt-1 text-sm text-slate-300">{copy.vendorSection.securityDesc}</p>
              </div>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div>
                <p className="text-sm font-medium text-slate-200">{copy.vendorSection.fields.keyStatus}</p>
                <span
                  className={[
                    "mt-2 inline-flex rounded-md border px-2 py-1 text-xs font-semibold",
                    draftVendor.keyConfigured
                      ? "border-emerald-400/35 bg-emerald-500/20 text-emerald-200"
                      : "border-rose-400/35 bg-rose-500/15 text-rose-200"
                  ].join(" ")}
                >
                  {draftVendor.keyConfigured ? copy.vendorSection.configured : copy.vendorSection.missing}
                </span>
              </div>

              <label className="grid gap-2 text-sm font-medium text-slate-200">
                {copy.vendorSection.fields.apiKey}
                <div className="relative">
                  <input
                    value={draftVendor.apiKeyMask}
                    readOnly
                    className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 pr-10 text-[hsl(var(--foreground))]"
                  />
                  <EyeOff className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                </div>
              </label>
            </div>
          </article>

          <section className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
            <p className="text-sm font-medium text-slate-200">{copy.vendorSection.headers.features}</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {vendorFeatureKeys.map((featureKey) => (
                <label
                  key={featureKey}
                  className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200"
                >
                  <input
                    type="checkbox"
                    checked={draftVendor.features[featureKey]}
                    onChange={(event) =>
                      setDraftVendor((prev) => ({
                        ...prev,
                        features: {
                          ...prev.features,
                          [featureKey]: event.target.checked
                        }
                      }))
                    }
                  />
                  {copy.featureLabels[featureKey]}
                </label>
              ))}
            </div>
          </section>

          <section className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
            <p className="text-sm font-medium text-slate-200">{copy.vendorSection.fields.status}</p>
            <div className="mt-3 flex items-center gap-2">
              <button
                type="button"
                onClick={() => setDraftVendor((prev) => ({ ...prev, status: "disabled" }))}
                className={[
                  "rounded-lg border px-4 py-2 text-sm font-semibold transition",
                  draftVendor.status === "disabled"
                    ? "border-rose-400/35 bg-rose-500/15 text-rose-200"
                    : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                ].join(" ")}
              >
                {copy.vendorSection.statusDisabled}
              </button>

              <button
                type="button"
                onClick={() => setDraftVendor((prev) => ({ ...prev, status: "enabled" }))}
                className={[
                  "rounded-lg border px-4 py-2 text-sm font-semibold transition",
                  draftVendor.status === "enabled"
                    ? "border-emerald-400/35 bg-emerald-500/20 text-emerald-200"
                    : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                ].join(" ")}
              >
                {copy.vendorSection.statusEnabled}
              </button>
            </div>
          </section>

          <footer className="mt-5 flex justify-end gap-2 border-t border-white/10 pt-4">
            <button
              type="button"
              onClick={closeVendorEditor}
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/10"
            >
              {copy.cancel}
            </button>

            <button
              type="button"
              onClick={saveVendorEditor}
              className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400"
            >
              <Pencil className="h-4 w-4" />
              {copy.save}
            </button>
          </footer>
        </div>
      </div>
      )}

      {confirmDialog && (
      <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
        <div className="absolute inset-0 bg-black/70" onClick={() => setConfirmDialog(null)} />
        <div className="panel relative z-10 w-full max-w-md rounded-2xl p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-1 h-5 w-5 text-amber-300" />
            <div>
              <h4 className="text-lg font-semibold text-[hsl(var(--foreground))]">{confirmDialog.title}</h4>
              <p className="mt-1 text-sm text-slate-300">{confirmDialog.description}</p>
            </div>
          </div>

          <footer className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setConfirmDialog(null)}
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/10"
            >
              {copy.vendorSection.confirmCancel}
            </button>

            <button
              type="button"
              onClick={() => {
                void runConfirmedAction();
              }}
              disabled={testingVendor && confirmDialog.action === "test"}
              className={[
                "inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60",
                confirmDialog.action === "delete"
                  ? "bg-rose-500 text-rose-50 hover:bg-rose-400"
                  : confirmDialog.action === "disable"
                    ? "bg-amber-500 text-amber-950 hover:bg-amber-400"
                    : "bg-cyan-500 text-slate-950 hover:bg-cyan-400"
              ].join(" ")}
            >
              {testingVendor && confirmDialog.action === "test" ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : confirmDialog.action === "delete" ? (
                <Trash2 className="h-4 w-4" />
              ) : (
                <CircleCheck className="h-4 w-4" />
              )}
              {testingVendor && confirmDialog.action === "test"
                ? locale === "zh"
                  ? "测试中..."
                  : "Testing..."
                : confirmDialog.confirmLabel}
            </button>
          </footer>
        </div>
      </div>
      )}

      {toast && (
      <div className="fixed right-4 top-[96px] z-[65]">
        <div
          className={[
            "flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium shadow-lg",
            toast.tone === "success"
              ? "border-emerald-400/35 bg-emerald-500/20 text-emerald-100"
              : toast.tone === "warning"
                ? "border-amber-400/35 bg-amber-500/20 text-amber-100"
                : "border-rose-400/35 bg-rose-500/20 text-rose-100"
          ].join(" ")}
        >
          {toast.tone === "success" ? <CircleCheck className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
          {toast.message}
        </div>
      </div>
      )}
    </>
  );
}
