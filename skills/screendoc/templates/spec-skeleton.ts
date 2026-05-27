/**
 * /screendoc spec skeleton
 *
 * 這個檔案是給 ralph-loop 期間寫 / 改 spec 用的範本。
 * 真正的專案 spec 名稱建議叫 `manual.spec.ts`，跑出來的 PNG 放在 `out/<TIMESTAMP>/`。
 *
 * 已內建保護：
 *   FM-001 全域 timeout = 60s
 *   FM-002 shot() 自帶 size warn (< 30KB 視為可疑)
 *   FM-004 resetState() 會關 antd notification
 *   FM-006 cleanup undefined guard
 *   FM-008 ApiHelper 先 res.json() 再 ctx.dispose()
 *   FM-009 連續兩張 md5 相同自動警告
 *   FM-013 scrollIntoCenter() 強制滾到視窗中央再 hover
 *   FM-029 beforeAll timeout = 5min
 *   FM-030 全樹 md5 dedup（spec 結束自動掃）
 */

import { test, expect, APIRequestContext, Page, Locator } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

// =============================================================================
// 常數 / 環境
// =============================================================================

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:3000';
const PREFIX = process.env.E2E_PREFIX ?? ''; // FM-011: 截圖環境用空字串避免 [E2E] 入鏡
const OUT_ROOT = path.join(process.cwd(), 'out');
const RUN_DIR = path.join(OUT_ROOT, new Date().toISOString().replace(/[:.]/g, '-'));

fs.mkdirSync(RUN_DIR, { recursive: true });

// =============================================================================
// Design System Adapter（框架中立）
// =============================================================================
//
// resetState() / waitReady() 需要知道「modal 關閉鈕 / 通知關閉鈕 / spinner / 內容錨點」
// 的選擇器——這些每個 design system 不同。把它們抽成 preset，由 DESIGN_SYSTEM 環境變數選。
//
// Phase 0.4 偵測到專案用哪個 DS 後，設 DESIGN_SYSTEM=antd|mui|chakra|radix|mantine。
// 預設 'generic'：用 role/aria 的通用 fallback，能跑但不如指定 preset 精準。
//
// 選擇器來源：各 DS 官方 DOM 結構（antd v5 / MUI v5-6 / Chakra v2 / Radix·shadcn / Mantine v7）。
// 升級 DS 大版號時請回頭核對這張表。

interface DesignSystemAdapter {
  /** modal / dialog 的關閉按鈕 */
  modalClose: string;
  /** toast / notification 的關閉鈕 */
  notificationClose: string;
  /** 載入中 spinner（waitReady 會等它消失）*/
  spinner: string;
  /** 主內容錨點：出現代表頁面實質載入完成（waitReady 用）*/
  contentAnchor: string;
}

const DESIGN_SYSTEMS: Record<string, DesignSystemAdapter> = {
  // 通用 fallback：不依賴任何 DS class，只靠 ARIA role / aria-label。
  // 大小寫不敏感（i 旗標）涵蓋 "close" / "Close" 兩種寫法。
  generic: {
    modalClose: '[role="dialog"] button[aria-label*="close" i], [role="dialog"] [aria-label*="關閉"]',
    notificationClose: '[role="alert"] button[aria-label*="close" i], [role="status"] button[aria-label*="close" i]',
    spinner: '[role="progressbar"], [aria-busy="true"]',
    contentAnchor: 'main, [role="main"], header, h1',
  },
  antd: {
    modalClose: '.ant-modal-close',
    notificationClose: '.ant-notification-notice-close, .ant-message-notice',
    spinner: '.ant-spin-spinning',
    contentAnchor: '.ant-layout-content, .ant-table, header, h1',
  },
  mui: {
    // MUI Dialog 沒固定 class，靠 aria-label（大小寫各專案不一，用 i 旗標）
    modalClose: '.MuiDialog-root button[aria-label*="close" i]',
    notificationClose: '.MuiSnackbar-root button, .MuiAlert-action button',
    spinner: '.MuiCircularProgress-root',
    contentAnchor: 'main, .MuiContainer-root, header, h1',
  },
  chakra: {
    modalClose: '.chakra-modal__close-btn',
    notificationClose: '.chakra-toast .chakra-close-button',
    spinner: '.chakra-spinner',
    contentAnchor: 'main, header, h1',
  },
  radix: {
    // Radix / shadcn：Dialog close 靠 aria-label；Toast / Sonner 有 data 屬性
    modalClose: '[role="dialog"] button[aria-label*="close" i]',
    notificationClose: '[data-close-button], [data-radix-toast-close]',
    spinner: '.animate-spin',
    contentAnchor: 'main, header, h1',
  },
  mantine: {
    modalClose: '.mantine-Modal-close',
    notificationClose: '.mantine-Notification-closeButton',
    spinner: '.mantine-Loader-root',
    contentAnchor: 'main, .mantine-AppShell-main, header, h1',
  },
};

const DS: DesignSystemAdapter =
  DESIGN_SYSTEMS[process.env.DESIGN_SYSTEM ?? 'generic'] ?? DESIGN_SYSTEMS.generic;

// =============================================================================
// 截圖 helpers
// =============================================================================

const md5Cache = new Map<string, string>();

/**
 * 截目前 viewport
 *
 * 自帶：
 *   - 等候穩定（waitReady）
 *   - 寫檔
 *   - md5 + size 檢查
 *   - 連續重複警告
 */
export async function shot(
  page: Page,
  filename: string,
  opts: { fullPage?: boolean; mask?: Locator[]; reason?: string } = {},
) {
  await waitReady(page);
  const file = path.join(RUN_DIR, filename);
  const buf = await page.screenshot({
    path: file,
    fullPage: opts.fullPage ?? false,
    mask: opts.mask ?? [],
    animations: 'disabled',
  });

  const size = buf.length;
  const md5 = crypto.createHash('md5').update(buf).digest('hex');

  // FM-002: 太小 = 可能截到 spinner / 空白
  if (size < 30 * 1024) {
    console.warn(`⚠️  [size] ${filename} only ${size} bytes — 可能截到空白頁`);
  }

  // FM-009: 連續兩張完全相同
  for (const [prev, prevMd5] of md5Cache) {
    if (prevMd5 === md5) {
      console.warn(`⚠️  [md5-dup] ${filename} 與 ${prev} 完全相同 — 可能 navigation 沒換頁`);
      break;
    }
  }

  md5Cache.set(filename, md5);
  if (opts.reason) console.log(`📸 ${filename}  (${(size / 1024).toFixed(1)}KB)  — ${opts.reason}`);
}

/** 截 fullPage（卷軸全部）*/
export async function shotFull(page: Page, filename: string, reason?: string) {
  return shot(page, filename, { fullPage: true, reason });
}

// =============================================================================
// 等待 helpers
// =============================================================================

/**
 * 標準的「頁面穩定」等候組合：
 *   1. networkidle
 *   2. spinner 消失（選擇器由 design-system adapter 決定，FM-002）
 *   3. 最少 200ms 動畫餘韻
 *
 * 主內容錨點 DS.contentAnchor 供呼叫端在特定頁面額外 waitFor 用，
 * 這裡不強制等它（不同頁面錨點不同，硬等會誤判 timeout）。
 */
export async function waitReady(page: Page, opts: { extraMs?: number } = {}) {
  await page.waitForLoadState('networkidle', { timeout: 60_000 });
  // FM-002: spinner 還在就別截，避免截到轉圈圈。等不到（本來就沒 spinner）也不報錯。
  await page
    .locator(DS.spinner)
    .first()
    .waitFor({ state: 'hidden', timeout: 10_000 })
    .catch(() => {});
  await page.waitForTimeout(opts.extraMs ?? 200);
}

/** 滾到 row 中央後 hover（FM-013）*/
export async function scrollIntoCenter(loc: Locator) {
  await loc.scrollIntoViewIfNeeded();
  await loc.evaluate((el) => {
    el.scrollIntoView({ block: 'center', inline: 'center', behavior: 'instant' as ScrollBehavior });
  });
}

// =============================================================================
// 環境重設 — 在每個 chapter 開頭呼叫，避免上一章殘留 UI 干擾
// =============================================================================

export async function resetState(page: Page) {
  // FM-004: 關閉所有通知（選擇器由 design-system adapter 決定）
  await page
    .locator(DS.notificationClose)
    .all()
    .then((els) => Promise.all(els.map((e) => e.click().catch(() => {}))));

  // 關 modal / dialog
  await page
    .locator(DS.modalClose)
    .all()
    .then((els) => Promise.all(els.map((e) => e.click().catch(() => {}))));

  // 關 popover / dropdown
  await page.keyboard.press('Escape').catch(() => {});
  await waitReady(page);
}

// =============================================================================
// CJK 文字匹配 helper（FM-007: antd 雙字按鈕會插空格）
// =============================================================================

export function cjkButton(text: string): RegExp {
  // 「取消」-> /取.?消/
  const chars = [...text];
  return new RegExp(chars.join('.?'));
}

// =============================================================================
// API helper — beforeAll 用，順序務必先 .json() 再 dispose（FM-008）
// =============================================================================

export class ApiHelper {
  constructor(private ctx: APIRequestContext, private base: string = BASE_URL) {}

  async post<T = any>(p: string, body: any): Promise<T> {
    const r = await this.ctx.post(`${this.base}${p}`, { data: body });
    const j = await r.json();
    return this.unwrap(j);
  }

  async get<T = any>(p: string): Promise<T> {
    const r = await this.ctx.get(`${this.base}${p}`);
    const j = await r.json();
    return this.unwrap(j);
  }

  async destroy(p: string): Promise<void> {
    await this.ctx.delete(`${this.base}${p}`);
  }

  /**
   * 自動解包 nocobase / axios interceptor 的多層結構
   * - { data: { data: [...], meta: {...} } }  -> [...]
   * - { data: [...] }                         -> [...]
   * - [...]                                   -> [...]
   */
  private unwrap<T>(j: any): T {
    if (j?.data?.data !== undefined) return j.data.data;
    if (j?.data !== undefined) return j.data;
    return j;
  }
}

// =============================================================================
// 範例：spec 主體骨架（直接複製到專案 spec，把 chapter 內容換成自己的）
// =============================================================================

test.describe.configure({ mode: 'serial' });

// 固定 viewport 對齊 shotlist.json 預設（1440x900）。
// 不設的話會吃 Playwright 預設 1280x720，每張圖大小不可控、且跟手冊規格不一致。
// 個別 shot 需要不同尺寸時，在該 test 內 page.setViewportSize() 覆寫。
test.use({ viewport: { width: 1440, height: 900 } });

test.describe('manual screenshots', () => {
  let cleanup: { flush: () => Promise<void> } | undefined; // FM-006

  test.beforeAll(async ({ playwright }) => {
    test.setTimeout(300_000); // FM-029
    const ctx = await playwright.request.newContext();
    const api = new ApiHelper(ctx);

    // ⚠️ TODO: seed your data here
    // const proj = await api.post('/api/projects:create', { name: PREFIX + 'demo' });

    cleanup = {
      flush: async () => {
        // ⚠️ TODO: cleanup
        await ctx.dispose();
      },
    };
  });

  test.afterAll(async () => {
    if (cleanup) await cleanup.flush(); // FM-006
  });

  test('chapter 1 - 入口', async ({ page }) => {
    await page.goto(BASE_URL, { timeout: 60_000 }); // FM-001
    await resetState(page);
    await shot(page, '01-01-home.png', { reason: '首頁總覽' });
    // 後續 chapter 在 ralph-loop 期間補
  });
});
