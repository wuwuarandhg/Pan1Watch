[根目录](../../../CLAUDE.md) > [frontend](../../CLAUDE.md) > [packages](../) > **biz-ui**

# @panwatch/biz-ui · CLAUDE.md

> 生成时间：2026-03-22 19:55:32

## 模块职责

`@panwatch/biz-ui` 是 PanWatch 业务组件库，封装与股票/基金/AI 分析业务强相关的 React 组件，供主应用 `frontend/src` 使用。

## 组件清单

| 文件 | 组件 | 说明 |
|------|------|------|
| `components/InteractiveKline.tsx` | `InteractiveKline` | 交互式 K 线图 |
| `components/KlineModal.tsx` | `KlineModal` | K 线图弹窗 |
| `components/kline-summary-dialog.tsx` | `KlineSummaryDialog` | K 线摘要对话框 |
| `components/kline-indicators.tsx` | — | K 线技术指标展示 |
| `components/InteractiveFundChart.tsx` | `InteractiveFundChart` | 基金交互式图表 |
| `components/stock-price-alert-panel.tsx` | — | 股票价格提醒面板 |
| `components/price-alert-form-dialog.tsx` | — | 价格提醒规则表单 |
| `components/stock-insight-modal.tsx` | `StockInsightModal` | 股票 AI 洞察弹窗 |
| `components/ai-suggestion-badge.tsx` | — | AI 建议徽章 |
| `components/suggestion-badge.tsx` | — | 建议状态徽章 |
| `components/technical-badge.tsx` | — | 技术形态徽章 |
| `components/badge-chip.tsx` | — | 通用徽章芯片 |
| `components/logs-modal.tsx` | `LogsModal` | 系统日志弹窗（含 SSE 实时流） |
| `components/onboarding.tsx` | — | 新用户引导 |
| `components/AmbientBackground.tsx` | `AmbientBackground` | 环境背景动效 |
| `components/suggestion-action.ts` | — | 建议动作工具函数 |

## 辅助模块

| 文件 | 说明 |
|------|------|
| `src/market.ts` | 市场相关工具函数（市场名称、颜色映射） |
| `src/index.ts` | 统一导出 |

## 依赖

- `@panwatch/base-ui`：基础 UI 组件
- `@panwatch/api`：API 请求
- React、lucide-react、react-markdown

## 变更记录 (Changelog)

| 时间 | 变更内容 |
|------|----------|
| 2026-03-22 19:55:32 | 初次生成模块文档 |
