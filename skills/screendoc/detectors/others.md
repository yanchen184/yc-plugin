# Detector: 其他主流框架

> Angular / Svelte / SvelteKit / Remix / Astro / Flutter Web 共用的偵測與 Playwright 注意事項。

---

## Angular

**訊號**：`package.json` 有 `@angular/core`，根有 `angular.json`

**啟動**：`npm start` 或 `ng serve` → port 4200

**Playwright 注意**：
- Zone.js 等候：用 `page.waitForFunction(() => (window as any).getAllAngularRootElements?.()?.[0] != null)`
- networkidle 通常已夠
- Angular Material：`.mat-progress-spinner` 消失即可
- Auth：通常在 cookie 或 localStorage（`access_token`）

---

## Svelte / SvelteKit

**訊號**：
- Svelte：`package.json` 有 `svelte`，副檔名 `.svelte`
- SvelteKit：另外有 `@sveltejs/kit`、`svelte.config.js`

**啟動**：
- Svelte：`npm run dev` → 預設 5173
- SvelteKit：同上，建議 `npm run build && npm run preview`

**Playwright 注意**：
- `+page.svelte` 載入很快，networkidle + 200ms 多半足夠
- Suspense / await blocks 需另外等元素

---

## Remix

**訊號**：`package.json` 有 `@remix-run/react` 與 `@remix-run/node`，根有 `remix.config.js` 或 `vite.config.ts` 含 `@remix-run/dev`

**啟動**：`npm run dev` → port 3000

**Playwright 注意**：
- Loaders 全部走 server，client 只在 navigation 時 fetch loader → networkidle 可信
- ErrorBoundary：spec 失敗時拍出來不一定是 application error，要細看

---

## Astro

**訊號**：`package.json` 有 `astro`，根有 `astro.config.mjs`

**啟動**：
- 開發：`npm run dev` → 4321
- production：`npm run build && npm run preview`

**Playwright 注意**：
- 大部分頁是 SSG / SSR HTML，networkidle 完成即可截
- Islands hydration：等到 `[data-astro-cid]` 或具體元件 hydrated 再 hover / click
- View transitions：跨頁要 `await page.waitForLoadState('domcontentloaded')` 再 `networkidle`

---

## Flutter Web

**訊號**：根有 `pubspec.yaml`，且有 `web/index.html` 或 build 後產出 `build/web/`

**啟動**：
- dev：`flutter run -d chrome --web-port 8080`
- production：`flutter build web` → 用 `python3 -m http.server 8080 -d build/web/`

**Playwright 注意**：
- 整個 app 是一張 canvas（`flt-glass-pane`），**Playwright 看不到 Flutter widget**
- 截圖是可以的，但**不能用 selector**，必須用座標 click：
  ```ts
  await page.mouse.click(x, y);
  ```
- 文字輸入：`await page.keyboard.type('xxx')`
- 等候：用 `page.waitForFunction(() => document.querySelector('flt-glass-pane'))`
- caption 視角等同：因為沒有 DOM，新手視角的「找按鈕」會困難 → 截圖必須在 caption 中明確指出座標位置（「左上角圓角矩形按鈕」）

**特殊建議**：Flutter Web 拍出來的手冊閱讀體驗較弱，若可能優先拍其原生平台版本。

---

## 通用 fallback

如果以上都不命中：

1. 確認入口 URL 可開
2. spec 用 `domcontentloaded` + `networkidle` + `waitForTimeout(800)` 雙保險
3. 在 caption 視角嚴格要求「肉眼可見」的錨點，不要依賴框架特性
