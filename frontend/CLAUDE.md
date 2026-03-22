[根目录](../CLAUDE.md) > **frontend**

# frontend · CLAUDE.md

> 生成时间：2026-03-22 19:55:32

## 模块职责

PanWatch 前端是一个基于 React 18 + Vite + TypeScript 的单页 PWA 应用，面向个人投资者提供：
- 投资组合管理（持仓、账户）
- AI Agent 管理与手动触发
- 价格提醒配置
- 机会发现与推荐榜
- 情报中心（历史分析、新闻）
- 数据源 / AI 服务 / 通知渠道配置
- MCP 工具页面
- PWA 离线访问支持

前端通过 pnpm workspace 管理三个子包：`@panwatch/api`、`@panwatch/biz-ui`、`@panwatch/base-ui`。

## 入口与启动

| 模式 | 命令 | 说明 |
|------|------|------|
| 开发 | `pnpm dev` | Vite dev server，代理 `/api` 到 `:8000` |
| 构建 | `pnpm build` | `tsc -b && vite build`，输出到 `dist/` |
| 预览 | `pnpm preview` | 预览构建产物 |

入口文件：`src/main.tsx` → `src/App.tsx`

## 路由结构

由 `react-router-dom v6` 管理，路由定义在 `src/App.tsx`：

| 路径 | 组件 | 说明 |
|------|------|------|
| `/` | `Dashboard` | 首页：市场指数、持仓概览 |
| `/portfolio` | `Stocks` | 持仓管理（自选股、账户、持仓） |
| `/intel` | `IntelCenter` | 情报中心（历史报告、新闻） |
| `/opportunities` | `Opportunities` | 机会发现（入场候选榜） |
| `/agents` | `Agents` | Agent 配置与触发 |
| `/alerts` | `PriceAlerts` | 价格提醒规则管理 |
| `/datasources` | `DataSources` | 数据源 / AI 服务配置 |
| `/mcp` | `MCP` | MCP 工具调用测试页 |
| `/settings` | `Settings` | 系统设置 |
| `/login` | `Login` | 登录页（JWT 认证） |

未认证时自动重定向到 `/login`（`RequireAuth` 组件守卫）。

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.3 | UI 框架 |
| TypeScript | 5.3 | 类型安全 |
| Vite | 5.0 | 构建工具 |
| TailwindCSS | 3.4 | 样式 |
| react-router-dom | 6.20 | 路由 |
| @radix-ui/* | — | 无障碍基础组件（Dialog, Select 等） |
| lucide-react | 0.300 | 图标 |
| react-markdown | 10.x | Markdown 渲染（AI 报告） |
| pnpm workspace | — | Monorepo 包管理 |

## 子包架构

```
frontend/packages/
├── api/          @panwatch/api     HTTP 客户端封装
├── biz-ui/       @panwatch/biz-ui  业务 UI 组件
└── base-ui/      @panwatch/base-ui 基础 UI 组件
```

路径别名（`vite.config.ts`）：
```
@               -> frontend/src
@panwatch/api   -> frontend/packages/api/src
@panwatch/biz-ui -> frontend/packages/biz-ui/src
@panwatch/base-ui -> frontend/packages/base-ui/src
```

## 认证机制

- 采用 JWT Token，存储于 `localStorage`
- `packages/api/src/auth.ts` 提供 `isAuthenticated()`、`logout()` 工具函数
- `packages/api/src/client.ts` 中封装 `fetchAPI()`，自动附加 `Authorization: Bearer <token>` 头

## PWA 支持

- `frontend/public/manifest.json`：PWA 清单（图标、名称）
- `frontend/public/sw.js`：Service Worker
- 图标：`icon-192.png`、`icon-512.png`、`icon.svg`

## 全局 Hooks

| Hook | 文件 | 说明 |
|------|------|------|
| `useTheme` | `src/hooks/use-theme.ts` | 深色/浅色主题切换（持久化到 localStorage） |
| `useRefresh` | `src/hooks/use-global-refresh.tsx` | 全局数据刷新 + 自动刷新进度环 |
| `useConfirmDialog` | `src/hooks/use-confirm-dialog.tsx` | 确认对话框 |

## 工具函数

| 文件 | 说明 |
|------|------|
| `src/lib/utils.ts` | `cn()` Tailwind 类名合并工具 |
| `src/lib/kline-scorer.ts` | 前端 K 线评分计算 |
| `src/lib/report-content.ts` | AI 报告内容格式化 |
| `src/lib/logger-map.ts` | 日志级别颜色映射 |

## 相关文件清单

| 文件 | 说明 |
|------|------|
| `frontend/src/App.tsx` | 路由、导航、认证守卫、主题切换 |
| `frontend/src/main.tsx` | React 应用挂载入口 |
| `frontend/src/index.css` | 全局 CSS 变量（颜色、圆角等） |
| `frontend/vite.config.ts` | Vite 配置、别名、代理 |
| `frontend/tailwind.config.js` | Tailwind 配置 |
| `frontend/tsconfig.json` | TypeScript 配置 |
| `frontend/pnpm-workspace.yaml` | pnpm workspace 配置 |
| `frontend/index.html` | HTML 模板 |

## 变更记录 (Changelog)

| 时间 | 变更内容 |
|------|----------|
| 2026-03-22 19:55:32 | 初次生成模块文档 |
