# Detector: Next.js (Pages Router / App Router)

## 偵測訊號

- `package.json` 有 `next`
- 有 `next.config.js` / `next.config.mjs` / `next.config.ts`
- 有 `pages/` 或 `app/` 目錄

## 啟動

- `npm run dev` → 預設 port 3000
- 建議跑 production：
  ```bash
  npm run build && npm start
  ```
  以避免 dev mode 的 HMR / overlay 干擾截圖

## Playwright 進入點

```ts
const BASE = process.env.BASE_URL ?? 'http://localhost:3000';
```

## 路由 / Auth

- App Router (>= 13)：很多 server component，networkidle 之後可能還在 RSC streaming
- 中介軟體 redirect：先確認 spec 跟得上 chained redirect
- next-auth：用 cookie，需要 `.addCookies()` 寫入 `__Secure-next-auth.session-token`

## 截圖前的標準等候

```ts
await page.waitForLoadState('networkidle');
// App Router 的 RSC streaming 額外等候
await page.waitForTimeout(500);
```

## 已知踩坑

- next dev overlay (`__nextjs_original-stack-frame`) 可能在 dev mode 浮現 → 用 `page.evaluate(() => document.querySelector('nextjs-portal')?.remove())` 移除
- Image optimization：`next/image` 在 dev 可能慢 → 等 `[data-nimg]` 載完
- Server Actions 觸發後不會立刻 navigation → 需等 toast 或 redirect 才截
