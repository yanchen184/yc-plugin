# Detector: NocoBase plugin

## 偵測訊號

- 路徑包含 `storage/plugins/@<scope>/plugin-*` 或 `packages/plugins/`
- `package.json` 有 `@nocobase/client` / `@nocobase/server` peer dependency
- 有 `dist/client/index.js`（**AMD 格式**，不是 ESM）
- 有 `src/client/` `src/server/` 雙端結構

## 啟動

- 在 NocoBase 主專案執行 `yarn dev`，預設 port 13000
- plugin 啟用：`yarn pm enable <plugin-name>`
- 啟用後重新載入頁面，看到 sidebar 新項目即代表成功

## AMD 載入坑

NocoBase plugin 的 client 端 entry 必須是 **AMD bundle**：

```js
define(['@nocobase/client', 'react', 'antd', '@formily/react'], function(client, React, antd, formily) {
  const h = React.createElement;
  // ...
  return { default: MyPlugin };
});
```

不能是 ES module。打包工具設定要是 `libraryTarget: 'amd'` 或 rollup `format: 'amd'`。

## Playwright 進入點

```ts
const BASE = process.env.BASE_URL ?? 'http://localhost:13000';
await page.goto(`${BASE}/admin/${pluginRoute}`, { timeout: 60_000 });
```

## Auth 與初始化

NocoBase 用 cookie + JWT，建議跑 spec 前先取得 token：

```ts
test.beforeAll(async ({ playwright }) => {
  const ctx = await playwright.request.newContext();
  const r = await ctx.post(`${BASE}/api/auth:signIn`, {
    data: { account: 'admin@nocobase.com', password: 'admin123' },
  });
  const j = await r.json();
  const token = j.data.token;
  // ...
});
```

## API 解包層數規則（FM-027）

NocoBase 的 framework action 與 custom action 解包層數不同：

| Action 類型 | response 結構 | 解包 |
|---|---|---|
| 框架 `:list` `:create` 等 | `{ data: { data: [...], meta: {...} } }` | `j.data.data` |
| 自訂 controller 直接 return | `{ data: ... }` | `j.data` |

ApiHelper 的 `unwrap()` 已自動處理（看 `templates/spec-skeleton.ts`）。

## 截圖前的標準等候

```ts
await page.waitForLoadState('networkidle');
// 等 antd app shell 載完
await page.waitForSelector('.ant-pro-layout, .ant-layout', { state: 'visible' });
// 等 plugin 內容
await page.waitForTimeout(500);
```

## 已知踩坑

- `[E2E-TPL]` 文字有方括號 → 用 `getByText('[E2E-TPL]xxx')` 而非 locator（FM-005）
- antd notification 殘留 → resetState() 自動關（FM-004）
- antd 雙字按鈕插空格 → 用 `cjkButton('取消')` regex（FM-007）
- AMD 變數名衝突：bundle 內部的 `const h = ...` 不能跟 `import { h }` 同名 → 看 memory `project_dochub_frontend_breakthrough.md`
