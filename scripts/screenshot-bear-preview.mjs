import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const outPath = join(__dirname, '../public/assets/generated/bear-preview-screenshot.png');
const url = 'http://127.0.0.1:5173/bear-review.html';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForTimeout(800); // let animation start
await page.screenshot({ path: outPath, fullPage: true });
await browser.close();
console.log('saved', outPath);
