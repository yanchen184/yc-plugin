# Detector: React (CRA / Vite / 自架)

## 偵測訊號（任一命中即視為 React）

- `package.json` 有 `react` 與 `react-dom`
- 入口檔有 `import App from './App'` 或 `<React.StrictMode>` 包覆
- 沒有 next / remix / nocobase 框架特徵

## 啟動指令推測

- 看 `package.json` scripts.dev / scripts.start：
  - `vite` → `npm run dev` (port 5173)
  - `react-scripts start` → `npm start` (port 3000)
  - 自架 webpack-dev-server → 看設定

## Playwright 進入點

```ts
const BASE = process.env.BASE_URL ?? 'http://localhost:5173';
await page.goto(BASE, { timeout: 60_000 });
```

## 常見 UI 庫對應

| UI 庫 | CJK 按鈕坑 | 等候建議 |
|---|---|---|
| antd | 雙字插空格 → 用 regex（FM-007） | `[role=alert]` 收 toast |
| MUI | 無空格問題 | `.MuiCircularProgress-root` 消失 |
| Chakra | 無 | `[data-loading]` 屬性 |
| 純 css | 無 | 自己寫 selector |

## Auth 處理

- localStorage / sessionStorage 帶 token：
  ```ts
  await page.addInitScript(t => localStorage.setItem('token', t), JWT);
  ```
- Cookie：
  ```ts
  await context.addCookies([{ name: 'token', value: JWT, url: BASE }]);
  ```

## 截圖前的標準等候

```ts
await page.waitForLoadState('networkidle');
await page.waitForSelector('#root > *', { state: 'attached' });  // mount
await page.waitForTimeout(200);
```

## 已知踩坑

- Vite HMR 可能造成 networkidle 不停 → 跑 `--mode production` 或 `npm run build && vite preview`
- React 19 的 transition 會延後 commit → 改等具體元素而非 networkidle
