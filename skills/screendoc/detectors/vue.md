# Detector: Vue (Vue 3 / Nuxt 視為單獨)

## 偵測訊號

- `package.json` 有 `vue` (>= 3.x)
- 有 `<template>` 區塊的 .vue 檔
- 有 `createApp` from 'vue'

## 啟動

- 通常是 `vite` → port 5173
- 老專案可能用 `vue-cli-service serve` → port 8080

## Playwright 注意事項

- Vue 3 reactivity 比 React 快，多數情況 networkidle 已夠
- Pinia store 初始化可能 async，多等 200ms

## UI 庫對應

| UI 庫 | 注意點 |
|---|---|
| Element Plus | `.el-loading-mask` 消失 |
| Vuetify | `.v-progress-circular` 消失 |
| Naive UI | `.n-spin` 消失 |
| Quasar | `.q-loading` 消失 |

## Auth

通常一樣 localStorage / cookie，與 React 同。

## 已知踩坑

- 路由轉換動畫可能讓 networkidle 不觸發 → 加 `waitForTimeout(300)`
- `<Suspense>` 內元件需等 await `defineAsyncComponent`
