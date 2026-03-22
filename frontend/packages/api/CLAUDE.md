[根目录](../../../CLAUDE.md) > [frontend](../../CLAUDE.md) > [packages](../) > **api**

# @panwatch/api · CLAUDE.md

> 生成时间：2026-03-22 19:55:32

## 模块职责

`@panwatch/api` 是前端 HTTP 客户端封装包，提供：
- 统一的 `fetchAPI()` 请求函数（自动附加认证头、处理错误）
- 所有后端 API 的类型定义（TypeScript 接口）
- 各功能模块的 API 调用函数

## 入口

`src/index.ts` 统一导出所有子模块：
```typescript
export * from './client'
export * from './types'
export * from './stocks'
export * from './insight'
export * from './app'
export * from './auth'
export * from './recommendations'
export * from './discovery'
export * from './dashboard'
```

## 子模块说明

| 文件 | 说明 |
|------|------|
| `src/client.ts` | `fetchAPI<T>()` 基础请求函数，自动附加 JWT |
| `src/types.ts` | 核心类型定义（AIModel, AIService, NotifyChannel, DataSource） |
| `src/auth.ts` | `login()`, `isAuthenticated()`, `logout()`, `getToken()` |
| `src/app.ts` | 应用级 API：`appApi.version()` |
| `src/stocks.ts` | 股票、持仓、账户相关 API |
| `src/insight.ts` | AI 洞察、历史分析 API |
| `src/recommendations.ts` | 推荐榜、建议池 API |
| `src/discovery.ts` | 市场发现 API |
| `src/dashboard.ts` | 仪表盘概览 API |

## 关键类型

```typescript
interface AIModel {
  id: number; name: string; service_id: number;
  model: string; is_default: boolean;
}
interface AIService {
  id: number; name: string; base_url: string;
  api_key: string; models: AIModel[];
}
interface NotifyChannel {
  id: number; name: string; type: string;
  config: Record<string, string>;
  enabled: boolean; is_default: boolean;
}
interface DataSource {
  id: number; name: string; type: string; provider: string;
  config: Record<string, unknown>;
  enabled: boolean; priority: number;
  supports_batch: boolean; test_symbols: string[];
}
```

## 使用方式

```typescript
import { fetchAPI, isAuthenticated, login, appApi } from '@panwatch/api'

// 通用请求（自动附加 token）
const data = await fetchAPI<MyType>('/stocks')

// 认证
await login(username, password)
if (isAuthenticated()) { ... }

// 版本检查
const { version } = await appApi.version()
```

## 变更记录 (Changelog)

| 时间 | 变更内容 |
|------|----------|
| 2026-03-22 19:55:32 | 初次生成模块文档 |
