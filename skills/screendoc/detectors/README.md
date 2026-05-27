# Detectors — Phase 0 偵測流程

> Phase 0 (Precheck) 用這份索引決定「目標專案是哪一種框架」，
> 並讀對應的 detector 檔取得啟動方式、Playwright 等候策略、已知踩坑。

## 偵測順序（先特殊、後通用）

由上而下檢查，**第一個命中的就用它**，不要繼續往下：

| # | 框架 | 訊號（任一命中即可） | Detector |
|---|------|---------------------|----------|
| 1 | NocoBase plugin | 路徑含 `storage/plugins/@*/plugin-*` 或 `packages/plugins/`；`package.json` 有 `@nocobase/client` 或 `@nocobase/server` peer dep | [nocobase.md](./nocobase.md) |
| 2 | Next.js | `package.json` 有 `next`；有 `next.config.{js,mjs,ts}`；有 `pages/` 或 `app/` | [next.md](./next.md) |
| 3 | Remix | `package.json` 有 `@remix-run/react`；有 `remix.config.js` 或 `vite.config.ts` 引用 `@remix-run/dev` | [others.md#remix](./others.md) |
| 4 | SvelteKit | `package.json` 有 `@sveltejs/kit`；有 `svelte.config.js` | [others.md#svelte--sveltekit](./others.md) |
| 5 | Astro | `package.json` 有 `astro`；有 `astro.config.mjs` | [others.md#astro](./others.md) |
| 6 | Angular | `package.json` 有 `@angular/core`；根有 `angular.json` | [others.md#angular](./others.md) |
| 7 | Svelte（非 Kit） | `package.json` 有 `svelte`，但無 `@sveltejs/kit` | [others.md#svelte--sveltekit](./others.md) |
| 8 | Flutter Web | 根有 `pubspec.yaml`；有 `web/index.html` 或 `build/web/` | [others.md#flutter-web](./others.md) |
| 9 | Vue | `package.json` 有 `vue`；副檔名 `.vue` 廣泛存在 | [vue.md](./vue.md) |
| 10 | React（兜底） | `package.json` 有 `react` 但無上述特殊訊號 | [react.md](./react.md) |

## 偵測不出來時

如果以上 10 種都不命中：

1. **不要硬猜**——直接告知使用者：「無法判別這個前端框架，請手動指定 `--framework=...`」
2. 通用 fallback 等候策略：`domcontentloaded` → `networkidle` → `waitForTimeout(800)` 雙保險
3. caption 視角中嚴格要求肉眼可見錨點，不依賴框架特性
4. 把這個 case 記下來——可能是要新增 detector 的時機

## 為什麼 NocoBase 排最前

NocoBase 的 plugin 架構是 **AMD bundle 嵌在 React 裏面**，
單看 `package.json` 會看到 `@nocobase/client` peer dep，但同時也有 `react` ——
若先判 React 就會走錯路。所以「特殊框架」優先於「底層 framework」。

同理 Next/Remix/SvelteKit 排在 React/Svelte 之前。

## 加新 detector 的步驟

1. 在這個資料夾新增 `<framework>.md`（或合併進 `others.md`）
2. 內容一定要有：**偵測訊號**、**啟動指令**、**Playwright 進入點**、**標準等候**、**已知踩坑**
3. 在上方表格適當的優先位置插入這個框架
4. 如果跟既有框架的訊號可能重疊（比如新框架是基於 React），記得放在 React 之前
