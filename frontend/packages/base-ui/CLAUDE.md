[根目录](../../../CLAUDE.md) > [frontend](../../CLAUDE.md) > [packages](../) > **base-ui**

# @panwatch/base-ui · CLAUDE.md

> 生成时间：2026-03-22 19:55:32

## 模块职责

`@panwatch/base-ui` 是 PanWatch 基础 UI 组件库，封装通用 Radix UI + TailwindCSS 组件，供主应用和 `@panwatch/biz-ui` 共用。

## 组件清单

| 文件 | 组件 | 基础库 |
|------|------|--------|
| `components/ui/button.tsx` | `Button` | class-variance-authority |
| `components/ui/dialog.tsx` | `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription` | @radix-ui/react-dialog |
| `components/ui/select.tsx` | `Select`, `SelectTrigger`, `SelectContent`, `SelectItem` | @radix-ui/react-select |
| `components/ui/popover.tsx` | `Popover`, `PopoverTrigger`, `PopoverContent` | @radix-ui/react-popover |
| `components/ui/hover-popover.tsx` | `HoverPopover` | @radix-ui/react-popover |
| `components/ui/label.tsx` | `Label` | @radix-ui/react-label |
| `components/ui/input.tsx` | `Input` | HTML input |
| `components/ui/switch.tsx` | `Switch` | @radix-ui/react-switch |
| `components/ui/badge.tsx` | `Badge` | class-variance-authority |
| `components/ui/calendar.tsx` | `Calendar` | react-day-picker |
| `components/ui/toast.tsx` | `Toast`, `Toaster` | @radix-ui/react-toast |
| `components/ui/skeleton.tsx` | `Skeleton` | Tailwind animate |

## 工具函数

| 文件 | 说明 |
|------|------|
| `src/cn.ts` | `cn()` clsx + tailwind-merge 工具函数 |
| `src/index.ts` | 统一导出 |

## 变更记录 (Changelog)

| 时间 | 变更内容 |
|------|----------|
| 2026-03-22 19:55:32 | 初次生成模块文档 |
