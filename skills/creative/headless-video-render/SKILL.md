---
name: headless-video-render
description: Render web/HTML animations to MP4 via Chromium and FFmpeg.
---

# Headless Video Render (Web-to-MP4 via Chromium & FFmpeg)

Export frame-accurate video from web animations (HTML/CSS/GSAP/Canvas) to MP4 on headless Linux environments without frame dropping or disk I/O bottlenecks.

## 1. System Prerequisites

On headless Linux (Ubuntu/Debian VPS), Chromium requires system libraries:
```bash
apt-get update && apt-get install -y -qq \
  libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
  libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
  libcairo2 libpango-1.0-0 libpangocairo-1.0-0
```

Verify binary paths:
- Chromium: Check `/root/.hermes/tools/chromium-1208/chrome-linux64/chrome` or system `which chromium`
- FFmpeg: Check `/root/.hermes/tools/ffmpeg-9.0.1-linux-x64/bin/ffmpeg` or system `which ffmpeg`

## 2. Animation Interface Requirement

The HTML file must expose a deterministic time-scrubbing interface on `window.OPENER` so the headless runner can seek time explicitly instead of relying on real-time playback:

```javascript
window.OPENER = {
  tl: masterTimeline,
  DURATION: 60,
  ready: true,
  seek: (t) => {
    masterTimeline.seek(t, false);
  }
};
```

Ensure autoplay is disabled when `?clean=1` is present in the URL.

## 3. Direct Pipe Architecture (Zero Disk I/O Bottleneck)

**Do NOT save thousands of individual PNG/JPEG files to disk.** Writing 1,800-3,600 files to disk exhausts inodes, causes high disk latency, and slows down encoding. Instead, stream screenshot buffers directly into `ffmpeg` stdin via `image2pipe`.

### Node.js / Puppeteer-Core Template (`render.mjs`)

```javascript
import puppeteer from 'puppeteer-core';
import { spawn } from 'node:child_process';

const CHROME_PATH = process.env.CHROME_PATH || '/root/.hermes/tools/chromium-1208/chrome-linux64/chrome';
const FFMPEG_PATH = process.env.FFMPEG_PATH || '/root/.hermes/tools/ffmpeg-9.0.1-linux-x64/bin/ffmpeg';
const HTML_URL = process.env.URL || 'file:///path/to/index.html?clean=1';
const AUDIO_PATH = process.env.AUDIO || null;
const OUTPUT_MP4 = process.env.OUT || 'output.mp4';

const FPS = Number(process.env.FPS || 30);
const WIDTH = Number(process.env.WIDTH || 720);   // 720x1280 for 9:16 vertical, 1920x1080 for 16:9
const HEIGHT = Number(process.env.HEIGHT || 1280);

const browser = await puppeteer.launch({
  executablePath: CHROME_PATH,
  headless: 'new',
  args: [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--hide-scrollbars'
  ]
});

const page = await browser.newPage();
await page.setViewport({ width: WIDTH, height: HEIGHT, deviceScaleFactor: 1 });
await page.goto(HTML_URL, { waitUntil: 'networkidle0' });
await page.waitForFunction('window.OPENER && window.OPENER.ready');
await page.evaluate(() => document.fonts.ready);

const DURATION = await page.evaluate(() => window.OPENER.DURATION || 60);
const TOTAL_FRAMES = Math.ceil(DURATION * FPS);

const ffmpegArgs = [
  '-y',
  '-f', 'image2pipe',
  '-framerate', String(FPS),
  '-i', 'pipe:0',
  ...(AUDIO_PATH ? ['-i', AUDIO_PATH] : []),
  '-c:v', 'libx264',
  '-preset', 'veryfast',
  '-crf', '18',
  '-pix_fmt', 'yuv420p',
  ...(AUDIO_PATH ? ['-c:a', 'aac', '-b:a', '192k', '-shortest'] : []),
  '-movflags', '+faststart',
  OUTPUT_MP4
];

const ffmpeg = spawn(FFMPEG_PATH, ffmpegArgs);
ffmpeg.stderr.on('data', () => {});

for (let i = 0; i < TOTAL_FRAMES; i++) {
  const time = i / FPS;
  await page.evaluate((t) => window.OPENER.seek(t), time);

  // Capture as compressed JPEG buffer for maximum encoding throughput
  const buf = await page.screenshot({
    type: 'jpeg',
    quality: 95,
    clip: { x: 0, y: 0, width: WIDTH, height: HEIGHT }
  });

  const canWrite = ffmpeg.stdin.write(buf);
  if (!canWrite) {
    await new Promise((resolve) => ffmpeg.stdin.once('drain', resolve));
  }
}

ffmpeg.stdin.end();
await new Promise((resolve, reject) => {
  ffmpeg.on('close', (code) => (code === 0 ? resolve() : reject(new Error(`Exit ${code}`))));
});
await browser.close();
```

## 4. Audio Synchronization for Headless Renderers

Headless Chromium does not record Web Audio API output during synthetic time scrubbing. To provide synchronized sound:
1. Synthesize sound FX and background music deterministically to a standalone `.wav` file (e.g. via Python `wave` module or Node.js) matching the exact timeline cue times.
2. Feed the `.wav` file into FFmpeg as the second input (`-i pipe:0 -i audio.wav`).
3. Use `-c:a aac -b:a 192k -shortest` to ensure seamless alignment and prevent trailing silence.

## 5. Pitfalls and Rules

- **Missing fonts:** Always wait for `await page.evaluate(() => document.fonts.ready)` before capturing frame 0 to prevent fallback font pop-in.
- **Backpressure handling:** Always check `const canWrite = ffmpeg.stdin.write(buf)` and wait for `drain` event if `false`; otherwise memory usage will balloon uncontrollably.
- **Mobile playback compatibility:** Always use `-pix_fmt yuv420p` and `-movflags +faststart`. Default H.264 formats like 4:4:4 or missing faststart atoms fail to play on mobile players and messaging apps (Telegram/WhatsApp).
- **GPU sandboxing on VPS:** Always supply `--no-sandbox` and `--disable-dev-shm-usage` when launching Chromium in containerized/VPS root environments.
