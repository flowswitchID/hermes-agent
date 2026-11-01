"""Solve the hCaptcha IMAGE challenge with a vision model using numbered-grid classification.

hCaptcha renders images on a <canvas>. Instead of slicing the canvas into tiles and
classifying each tile individually (which fails on reasoning-style challenges like
"click the flower the bee never lands on"), we overlay a numbered grid on the full
canvas and ask the vision model: "which cell number?" This turns an expensive
grounding problem into a simple classification problem — the VLM chooses from N²
labels instead of guessing pixel coordinates, and it costs ONE API call per page
instead of 16.

Grid-overlay also enables drag challenges: ask for two cells (source, target) and
execute a programmatic drag via page.mouse.
"""
import asyncio
import base64
import io
import logging
import os
import re
import time

from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)
_GRID = 4
_SKIP_SEL = ".button-submit"
_MAX_RETRIES = 3  # retries per page with fresh canvas capture


def is_hard_challenge(target: str) -> bool:
    """hCaptcha challenge categories that vision models reliably FAIL at.

    Odd-one-out / rotation / abstract reasoning ("does not match", "does not
    belong", "different shape") are adversarially generated to defeat AI. Live
    tests: mistral-large picked confidently-wrong cells 3x in a row. Object
    detection ("click all X", "click the X") is where vision models shine.
    For hard categories we click Skip (same .button-submit, label becomes
    "Skip") to cycle to a fresh, hopefully easier challenge.
    """
    tl = target.lower()
    return any(k in tl for k in (
        "does not match", "doesn't match", "does not belong", "doesn't belong",
        "not match", "different from", "odd one out", "unlike",
        "does not fit", "doesn't fit", "different shape", "is different",
        "which shape", "same shape", "rotate", "rotation", "tilted",
        "horizont", "vertically", "mirror", "reflection",
    ))


# One-line JS, NO backslash escapes, NO double quotes. Frame.evaluate embeds the
# expression in a wrapper string literal where \n would become a real newline and
# break ("string literal contains an unescaped line break"). Using
# String.fromCharCode(10) and task.startsWith() keeps it bulletproof.
_CHALLENGE_META_JS = ("() => { const txt = document.body.innerText; "
    "const lines = txt.split(String.fromCharCode(10)).filter(l => l.trim()); "
    "const task = lines.find(l => !l.includes('try again') "
    "&& !l.match(/^(Skip|Verify|Next|EN)$/) && l.length > 5) || ''; "
    "const c = document.querySelector('canvas'); "
    "const r = c ? c.getBoundingClientRect() : null; "
    "const hasDrag = task.startsWith('drag') "
    "|| /help the (creature|monkey|robot|character)/i.test(task); "
    "const btn = document.querySelector('.button-submit'); "
    "return { target: task, "
    "canvasRect: r ? {x: r.x, y: r.y, w: c.width, h: c.height, cssW: r.width, cssH: r.height} : null, "
    "isDrag: hasDrag, buttonText: btn ? btn.innerText.trim() : '' }; }")


async def _challenge_meta(fr) -> dict:
    """Extract challenge task text + detect layout."""
    return await fr.evaluate(_CHALLENGE_META_JS)


async def _get_canvas_b64(fr) -> str:
    """Get the FULLEST canvas as a base64-encoded PNG.

    hCaptcha challenge frames contain several <canvas> elements (loading
    animation, hidden layers, etc.). querySelector('canvas') grabs the FIRST,
    which is often a blank/animating layer — producing an empty image the
    vision model then hallucinates answers from. We capture ALL canvases and
    return the one whose PNG is largest (most visual content), preferring
    opaque non-blank pixels.
    """
    res = await fr.evaluate("""() => {
        const cvs = [...document.querySelectorAll('canvas')];
        if (!cvs.length) return {b64: '', info: [], idx: -1};
        const out = {b64: '', info: [], idx: -1};
        let bestScore = 0;
        for (const c of cvs) {
            try {
                const w = c.width, h = c.height;
                if (!w || !h) continue;
                let opaque = 0;
                try {
                    const g = c.getContext('2d');
                    const d = g.getImageData(0, 0, Math.min(w, 320), Math.min(h, 320)).data;
                    for (let i = 3; i < d.length; i += 16) if (d[i] > 40) opaque++;
                } catch (e) {}
                const score = w * h * (0.3 + opaque / 400);
                out.info.push(cvs.indexOf(c) + ':' + w + 'x' + h + '/css' + c.clientWidth + 'x' + c.clientHeight + '/op' + Math.round(opaque * 100 / (Math.min(w,320)*Math.min(h,320)/16)));
                if (score > bestScore) {
                    bestScore = score;
                    out.b64 = c.toDataURL('image/png').split(',')[1] || '';
                    out.idx = cvs.indexOf(c);
                }
            } catch (e) {}
        }
        return out;
    }""")
    if isinstance(res, dict):
        if res.get("info"):
            print("HCV_CANVAS_INVENTORY", res["info"], flush=True)
        return res.get("b64", "")
    return res or ""


async def _get_best_canvas(fr) -> tuple[str, int]:
    """Return (b64, canvas_index) of the fullest canvas. index -1 if none."""
    res = await fr.evaluate("""() => {
        const cvs = [...document.querySelectorAll('canvas')];
        if (!cvs.length) return {b64: '', idx: -1};
        let bestScore = 0, best = null, bestIdx = -1;
        for (const c of cvs) {
            try {
                const w = c.width, h = c.height;
                if (!w || !h) continue;
                let opaque = 0;
                try {
                    const g = c.getContext('2d');
                    const d = g.getImageData(0, 0, Math.min(w, 320), Math.min(h, 320)).data;
                    for (let i = 3; i < d.length; i += 16) if (d[i] > 40) opaque++;
                } catch (e) {}
                const score = w * h * (0.3 + opaque / 400);
                if (score > bestScore) {
                    bestScore = score;
                    best = c;
                    bestIdx = cvs.indexOf(c);
                }
            } catch (e) {}
        }
        if (!best) return {b64: '', idx: -1};
        return {b64: best.toDataURL('image/png').split(',')[1] || '', idx: bestIdx};
    }""")
    if isinstance(res, dict):
        return res.get("b64", ""), res.get("idx", -1)
    return "", -1


def _grid_overlay(b64: str, grid: int = _GRID) -> str:
    """Crop each tile, upscale, and arrange into a labeled montage.

    Old approach (drawing numbers ON TOP of tiles) obscured content — the yellow
    labels and red lines hid the very detail hCaptcha challenges test (subtle
    odd-one-out differences). New approach: tiles are cropped from the canvas,
    upscaled 2x (LANCZOS), and laid out with GAPs between them; the yellow cell
    number lives in the gap ABOVE each tile, never covering tile pixels.
    """
    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    w, h = img.size
    tw, th = w // grid, h // grid
    SCALE = 2
    GAP = 36
    cell = tw * SCALE
    out_w = grid * cell + (grid + 1) * GAP
    out_h = grid * cell + (grid + 1) * GAP
    canvas = Image.new("RGB", (out_w, out_h), (250, 250, 250))
    draw = ImageDraw.Draw(canvas)
    n = 0
    for r in range(grid):
        for c in range(grid):
            tile = img.crop((c * tw, r * th, (c + 1) * tw, (r + 1) * th))
            tile = tile.resize((cell, cell), Image.LANCZOS)
            x = GAP + c * (cell + GAP)
            y = GAP + r * (cell + GAP)
            canvas.paste(tile, (x, y))
            # label in the gap directly ABOVE the tile (top row uses outer margin)
            lx, ly = x + 4, y - GAP + 4
            draw.rectangle([lx - 3, ly - 3, lx + 44, ly + 26], fill="yellow", outline="black")
            draw.text((lx, ly), str(n), fill="black")
            n += 1
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _build_prompt(target: str, grid: int = _GRID, attempt: int = 0) -> str:
    """Build an improved prompt with chain-of-thought reasoning.

    Different prompt strategies per attempt to get diverse answers:
    - attempt 0: Direct analysis with step-by-step reasoning
    - attempt 1: Focus on visual comparison / counting
    - attempt 2: Simplified — just describe what you see per cell

    Odd-one-out challenges ("does not match / does not belong / different")
    get a dedicated prompt — there is typically exactly ONE odd cell.
    """
    N = grid * grid
    tl = target.lower()
    odd_out = any(k in tl for k in (
        "does not match", "doesn't match", "does not belong", "doesn't belong",
        "not match", "different from", "odd one out", "unlike",
        "does not fit", "doesn't fit", "which shape is different",
    ))

    if odd_out:
        return (
            f"You are solving an hCaptcha challenge. The image is a {grid}x{grid} "
            f"grid of tiles. Tile numbering: row 1 = {list(range(0, grid))}, "
            f"row 2 = {list(range(grid, 2*grid))}, "
            f"row 3 = {list(range(2*grid, 3*grid))}, "
            f"row 4 = {list(range(3*grid, 4*grid))} "
            f"(left to right, top to bottom).\n\n"
            f'CHALLENGE: "{target}"\n\n'
            f"This is an ODD-ONE-OUT task: exactly ONE cell does not match the rest. "
            f"Most cells are identical (same shape, color, pattern, or orientation); "
            f"one single cell is different.\n\n"
            f"Step-by-step:\n"
            f"1. Scan all {N} cells and identify the dominant group (what most cells look like).\n"
            f"2. Find the ONE cell that breaks the pattern — different shape, missing part, "
            f"flipped, wrong color, or otherwise unlike the others.\n"
            f"3. Double-check: is it REALLY different, or just rotated/positioned oddly?\n\n"
            f"Reply ONLY that single cell's number. If you truly cannot find an odd "
            f"cell, reply: none"
        )

    base = (
        f"You are solving an hCaptcha image challenge. "
        f"The image is a {grid}x{grid} grid of tiles. Tile numbering: "
        f"row 1 = {list(range(0, grid))}, row 2 = {list(range(grid, 2*grid))}, "
        f"row 3 = {list(range(2*grid, 3*grid))}, row 4 = {list(range(3*grid, 4*grid))} "
        f"(left to right, top to bottom).\n\n"
        f"CHALLENGE: \"{target}\"\n\n"
    )

    if attempt == 0:
        # Primary: step-by-step reasoning
        base += (
            "Step-by-step:\n"
            "1. Read the challenge text carefully — what is it asking you to find/click?\n"
            "2. Examine EACH cell (0 through 15) one by one.\n"
            "3. For each cell, describe what you see in 5 words or less.\n"
            "4. Compare cells to determine which ones match the challenge.\n"
            "5. Consider edge cases: 'does NOT match', 'is different from others', 'shortest/longest'.\n\n"
            "After analysis, reply ONLY the matching cell number(s), comma-separated.\n"
            "Example: 3,7,11\n"
            "If nothing matches: none"
        )
    elif attempt == 1:
        # Secondary: forced comparison
        base += (
            "Look at each cell and compare them:\n"
            "- Which cells contain the SAME thing? Group them.\n"
            "- Which cells are DIFFERENT or UNIQUE?\n"
            "- The challenge usually asks for the odd one out, or specific items.\n\n"
            "Reply ONLY matching cell number(s), comma-separated.\n"
            "Example: 5,12\n"
            "If nothing matches: none"
        )
    else:
        # Tertiary: simple description + match
        base += (
            "Describe each cell briefly, then pick the answer:\n"
            f"Cell 0: [what?]\nCell 1: [what?]\n...Cell {N-1}: [what?]\n\n"
            "Now: which cell(s) match the challenge?\n"
            "Reply ONLY the cell number(s), comma-separated.\n"
            "Example: 2,8\n"
            "If nothing matches: none"
        )

    return base


def _parse_cells(text: str, grid: int = _GRID, max_cells: int = 4) -> list[int]:
    """Parse cell numbers from model response, filtering to valid range.

    Rejects responses that enumerate nearly the whole grid (e.g. an
    explanation listing "0,1,2,...,15") — those are descriptions, not picks.
    """
    N = grid * grid
    nums = []
    for m in re.finditer(r"\d+", text):
        v = int(m.group())
        if 0 <= v < N:
            nums.append(v)
    seen = set()
    uniq = [x for x in nums if not (x in seen or seen.add(x))]
    if len(uniq) > max_cells:
        return []
    return uniq


def _is_scattered(target: str) -> bool:
    """True when the challenge uses SCATTERED shapes (odd-one-out layout),
    where tiles float freely on the canvas instead of a 4x4 grid.
    """
    t = target.lower()
    return any(k in t for k in (
        "does not match", "doesn't match", "does not follow", "odd one out",
        "different from the rest", "shape that does not", "that does not match",
        "does not belong", "shape that grows", "shape that is different",
        "find all", "select all", "select things", "click on the",
        "based on the number", "cannot lift", "click on all",
    ))


def _canvas_is_scattered(w: int, h: int) -> bool:
    """Layout heuristic: hCaptcha grid challenges use a ~square canvas
    (4x4 tiles → 1:1). Scattered odd-one-out layouts use a wide/rect canvas
    (e.g. 1000x940 = 1.06, often with empty margins). Treat clearly
    non-square canvases as scattered."""
    if not w or not h:
        return False
    ratio = w / h
    return ratio > 1.03 or ratio < 0.97


def _compress_png_to_jpeg(b64_png: str, quality: int = 95) -> str:
    """Compress PNG b64 to JPEG b64 — 3x smaller, preserves detail for vision.
    Also enhance contrast so shapes stand out on dark captcha backgrounds."""
    try:
        img = Image.open(io.BytesIO(base64.b64decode(b64_png))).convert("RGB")
        # Contrast enhance: boost shape visibility on dark backgrounds
        from PIL import ImageEnhance
        img = ImageEnhance.Contrast(img).enhance(1.5)
        img = ImageEnhance.Brightness(img).enhance(1.2)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return b64_png


# ── Dedicated vision pool for scattered: always uses 3.5-flash (smarter) ──
_scattered_pool = None

def _get_scattered_pool():
    """Force gemini-3.5-flash for scattered picks — flash-lite too weak."""
    global _scattered_pool
    if _scattered_pool is not None:
        return _scattered_pool
    try:
        from gemini_vision import KeyPool
        keyfile = os.path.join(os.path.dirname(__file__), "apikey.txt")
        _scattered_pool = KeyPool(keyfile=keyfile, model="gemini-3.5-flash")
        log.info("scattered vision pool: gemini-3.5-flash")
        return _scattered_pool
    except Exception as e:
        log.warning("scattered pool init failed: %s — falling back to main pool", e)
        return None


async def _pick_scattered_point(fr, keypool, target: str, grid: int = _GRID) -> tuple[list[tuple[float, float]], int]:
    """Ask the model for the CENTER (x, y) in canvas pixels of the odd shape.

    Returns (points, canvas_idx): list of (x_px, y_px) points and the index
    of the canvas they refer to, so the caller maps them onto the SAME canvas.
    """
    b64, canvas_idx = await _get_best_canvas(fr)
    if not b64:
        return [], -1
    # Compress PNG→JPEG for faster Gemini upload (320KB→30-50KB)
    b64 = _compress_png_to_jpeg(b64)
    # Use main keypool (flash-lite) — 3.5-flash safety-blocks captcha prompts
    pick_pool = keypool
    # save debug copy
    try:
        import io as _io
        from PIL import Image as _PIL
        _PIL.open(_io.BytesIO(base64.b64decode(b64))).save("/tmp/hc_debug_raw.png")
    except Exception:
        pass
    size = await fr.evaluate("""(idx) => {
        const c = [...document.querySelectorAll('canvas')][idx];
        return c ? {w: c.width, h: c.height} : {w: 1000, h: 940};
    }""", canvas_idx)
    W, H = size.get("w", 1000), size.get("h", 940)
    log.info("_pick_scattered canvas idx=%d size=%dx%d", canvas_idx, W, H)

    tl = target.lower()
    is_seq = any(k in tl for k in (
        "sequence", "circular", "order", "pattern", "follow", "series",
        "rotate", "rotation", "progression", "next", "logical",
    ))
    is_multi = any(k in tl for k in (
        "find all", "select all", "select things", "click on all",
        "based on the number", "cannot lift",
    ))
    is_grows = "grows" in tl or "bigger" in tl or "largest" in tl or "biggest" in tl

    if is_multi:
        # Multi-select: "Find all animals based on the number provided"
        # or "Select things you cannot lift using only one hand"
        prompt = (
            f"You are solving an hCaptcha challenge on a canvas ({W}x{H}). "
            f'CHALLENGE: "{target}"\n\n'
            f"There are multiple shapes/objects scattered on the image. "
            f"You must select ALL items that match the criteria. "
            f"List the CENTER coordinates (X,Y) of EACH matching item, "
            f"separated by semicolons. Example: 200,300;500,400;800,250\n"
            f"Reply ONLY coordinates, no explanation."
        )
    elif is_grows:
        # "Please click on the shape that grows" = find the BIGGEST shape
        # Keep prompt SHORT for speed (45s→8s). Accuracy was already fine.
        prompt = (
            f"hCaptcha: one shape is BIGGER than the rest. Image {W}x{H}.\n"
            f'"{target}"\n'
            f"Compare each shape's size. Reply center of BIGGEST: X,Y"
        )
    elif is_seq:
        prompt = (
            f"You are solving an hCaptcha challenge. The image shows shapes arranged "
            f"in a circle/row ({W} wide x {H} tall). "
            f'CHALLENGE: "{target}"\n\n'
            f"The shapes form a logical sequence or pattern (e.g. color, size, shape, "
            f"orientation changing step by step). ONE shape breaks the sequence.\n"
            f"1) Analyze the pattern carefully.\n"
            f"2) Find the shape that does NOT follow the pattern.\n"
            f"Reply with ONLY the center coordinates of that shape: X,Y"
        )
    else:
        # Default scattered odd-one-out
        prompt = (
            f"You are solving an hCaptcha challenge. The image shows several identical "
            f"shapes scattered on a canvas ({W} wide x {H} tall). "
            f'CHALLENGE: "{target}"\n\n'
            f"Exactly ONE shape is different from all the others.\n"
            f"Find that one shape and report the coordinates of its CENTER in canvas "
            f"pixels.\n"
            f"Reply with ONLY two integers: X,Y . No explanation."
        )

    points: list[tuple[float, float]] = []
    # Round 1-2: fast picks via 3.5-flash (smarter).
    for attempt in range(2):
        text = await asyncio.to_thread(pick_pool.ask, b64, prompt)
        log.info("_pick_scattered attempt %d -> %s", attempt + 1, text[:120])
        # Parse: "200,300" or "200,300;500,400" (multi-select)
        for coord in re.split(r"[;|\n]+", text.strip()):
            coord = coord.strip()
            m = re.search(r"(\d{1,4})\s*[,;\s]\s*(\d{1,4})", coord)
            if m:
                x, y = float(m.group(1)), float(m.group(2))
                if x <= W and y <= H:
                    points.append((x, y))
        await asyncio.sleep(0.3)
    # Round 3: stronger model confirmation (slower but smarter).
    confirm_model = os.getenv("HCAPTCHA_SCATTERED_CONFIRM_MODEL", "").strip()
    if confirm_model:
        try:
            old_model = getattr(keypool, "models", None)
            keypool.models = [confirm_model]
            text = await asyncio.to_thread(keypool.ask, b64, prompt)
            log.info("_pick_scattered confirm(%s) -> %s", confirm_model, text[:120])
            m = re.search(r"(\d{1,4})\s*[,;\s]\s*(\d{1,4})", text)
            if m:
                x, y = float(m.group(1)), float(m.group(2))
                if x <= W and y <= H:
                    points.append((x, y))
            if old_model is not None:
                keypool.models = old_model
        except Exception as e:
            log.warning("_pick_scattered confirm model failed: %s", str(e)[:80])
            if old_model is not None:
                keypool.models = old_model

    if not points:
        return [], canvas_idx
    # Single point — always return it (better than nothing)
    if len(points) == 1:
        log.info("_pick_scattered single point: %s", points[0])
        return [points[0]], canvas_idx
    # For multi-select challenges: deduplicate close points, return all
    # (consensus filtering would wrongly drop valid multi-click targets)
    if is_multi:
        # Deduplicate: merge points within 5% of each other
        deduped = []
        for p in points:
            merged = False
            for i, d in enumerate(deduped):
                if abs(p[0] - d[0]) < W * 0.05 and abs(p[1] - d[1]) < H * 0.05:
                    deduped[i] = ((d[0] + p[0]) / 2, (d[1] + p[1]) / 2)
                    merged = True
                    break
            if not merged:
                deduped.append(p)
        log.info("_pick_scattered multi-select: %d unique points (from %d)", len(deduped), len(points))
        return deduped, canvas_idx
    # Single-select: vote: average of points within 15% of each other (cluster)
    if len(points) >= 2:
        from collections import Counter
        # simple consensus: keep points whose x and y are each within 12% of the median
        xs = sorted(p[0] for p in points)
        ys = sorted(p[1] for p in points)
        mx, my = xs[len(xs) // 2], ys[len(ys) // 2]
        close = [p for p in points if abs(p[0] - mx) < W * 0.12 and abs(p[1] - my) < H * 0.12]
        if len(close) >= 2:
            return [close[0]], canvas_idx
        # Only 1 model near median or none — still better than zero.
        # A wrong guess gets a retry; NO guess gets nothing (guaranteed fail).
        if close:
            log.info("_pick_scattered 1/%d near median — returning best point", len(points))
            return [close[0]], canvas_idx
        # 0 near median but we have points — return the median point as fallback
        log.info("_pick_scattered weak consensus (%d/%d) — using median fallback", len(close), len(points))
        return [[mx, my]], canvas_idx
    return [], canvas_idx


async def _click_point(page, fr, point: tuple[float, float], canvas_idx: int = 0) -> None:
    """Click a canvas pixel coordinate, mapped onto the element bounding box.

    canvas_idx must match the canvas the vision model actually saw (the
    fullest canvas, see _get_best_canvas); using [0] here while the model
    saw a different-sized canvas shifts every click off-target.

    Uses locator.click(position=...) instead of manual page.mouse math:
    Playwright resolves the element's position within the (possibly nested,
    transformed, zoomed) iframe and dispatches proper pointer events at the
    right spot — manual cbox math drifts when hCaptcha applies CSS transforms.
    """
    try:
        c = fr.locator("canvas").nth(canvas_idx)
        size = await fr.evaluate("""(idx) => {
            const c = [...document.querySelectorAll('canvas')][idx];
            return c ? {w: c.width, h: c.height} : {w: 1000, h: 940};
        }""", canvas_idx)
        W, H = size.get("w", 1000), size.get("h", 940)
        x, y = point
        # element's CSS box scales internal pixels down; position= is
        # relative to the element's border box in CSS pixels
        box = await c.bounding_box()
        if not box:
            log.warning("point click: no bounding box for canvas %d", canvas_idx)
            return
        pos = {"x": (x / W) * box["width"], "y": (y / H) * box["height"]}
        try:
            await c.click(position=pos, timeout=8000)
            log.info("point click %s -> css pos %s ok", point, pos)
        except Exception as e1:
            # element likely covered by an overlay → fall back to raw mouse
            # events at the page-level coordinate (bypasses hit-testing).
            log.warning("point click locator failed (%s) — mouse fallback", str(e1).splitlines()[0][:90])
            px = box["x"] + pos["x"]
            py = box["y"] + pos["y"]
            await page.mouse.click(px, py)
            log.info("point click %s -> page (%s,%s) via mouse", point, round(px, 1), round(py, 1))
        await asyncio.sleep(0.3)
    except Exception as e:
        log.warning("point click %s: %s", point, str(e).splitlines()[0])


async def _pick_cells(fr, keypool, target: str, grid: int = _GRID) -> list[int]:
    """Ask the vision model which numbered-grid cells satisfy *target*.

    RETRY LOGIC: tries up to _MAX_RETRIES times with different prompts.
    Each retry captures a fresh canvas (in case it changed) and uses a
    different prompt strategy. Returns the most common answer.
    """
    b64 = await _get_canvas_b64(fr)
    if not b64:
        return []
    # Compress for faster Gemini upload
    b64 = _compress_png_to_jpeg(b64)
    # debug: save what the model sees (last capture wins)
    try:
        import io as _io
        from PIL import Image as _PIL
        _PIL.open(_io.BytesIO(base64.b64decode(b64))).save("/tmp/hc_debug_raw.png")
        _PIL.open(_io.BytesIO(base64.b64decode(_grid_overlay(b64)))).save("/tmp/hc_debug_grid.png")
    except Exception:
        pass

    all_picks: list[list[int]] = []

    for attempt in range(_MAX_RETRIES):
        # Re-capture canvas each attempt (hCaptcha may animate)
        if attempt > 0:
            await asyncio.sleep(0.5)
            new_b64 = await _get_canvas_b64(fr)
            if new_b64:
                b64 = new_b64

        # Send the RAW canvas (no upscale, no overlay) — upscaling blurs the
        # subtle differences hCaptcha tests (odd-one-out), and Gemini reasons
        # over the grid natively. Montage is the fallback if parsing fails.
        prompt = _build_prompt(target, grid, attempt)
        text = await asyncio.to_thread(keypool.ask, b64, prompt)
        log.info("_pick_cells attempt %d(%r) -> %s", attempt + 1, target[:40], text[:120])

        picks = _parse_cells(text, grid)
        if not picks and attempt == 0:
            # retry with montage (labeled) as a second opinion
            montage = _grid_overlay(b64, grid)
            text2 = await asyncio.to_thread(keypool.ask, montage, prompt)
            log.info("_pick_cells montage retry -> %s", text2[:120])
            picks = _parse_cells(text2, grid)
        if not picks:
            # stronger-model confirmation round (slower but smarter)
            confirm_model = os.getenv("HCAPTCHA_SCATTERED_CONFIRM_MODEL", "").strip()
            if confirm_model:
                old_models = keypool.models
                try:
                    keypool.models = [confirm_model]
                    text3 = await asyncio.to_thread(keypool.ask, b64, prompt)
                    log.info("_pick_cells confirm(%s) -> %s", confirm_model, text3[:120])
                    picks = _parse_cells(text3, grid)
                except Exception as e:
                    log.warning("_pick_cells confirm model failed: %s", str(e)[:80])
                finally:
                    keypool.models = old_models
        if picks:
            all_picks.append(picks)
            # If first attempt gives a confident answer (1-3 cells), use it
            if attempt == 0 and len(picks) <= 3:
                log.info("confident pick on attempt 1: %s", picks)
                return picks
        else:
            log.info("attempt %d returned no valid cells", attempt + 1)

    if not all_picks:
        return []

    # Vote: pick cells that appear in majority of attempts
    from collections import Counter
    flat = [c for picks in all_picks for c in picks]
    counts = Counter(flat)
    threshold = len(all_picks) / 2  # majority
    voted = [c for c, cnt in counts.most_common() if cnt >= threshold]

    if not voted:
        # Fallback: return the most frequent answer from first attempt
        voted = all_picks[0]

    log.info("voted picks: %s (from %d attempts: %s)", voted, len(all_picks), all_picks)
    return voted


async def _classify_tiles(fr, keypool, target: str) -> list[int]:
    """DEPRECATED — use _pick_cells instead."""
    return await _pick_cells(fr, keypool, target)


async def _best_canvas_index(fr) -> int:
    """Return the index of the canvas with the most visual content.

    Must MATCH the canvas _get_canvas_b64 captures (it picks the same one by
    the same scoring), so clicks land on the exact image the model saw.
    """
    return await fr.evaluate("""() => {
        const cvs = [...document.querySelectorAll('canvas')];
        if (!cvs.length) return 0;
        let bi = 0, bestScore = -1;
        for (let i = 0; i < cvs.length; i++) {
            const c = cvs[i];
            try {
                const w = c.width, h = c.height;
                if (!w || !h) continue;
                // same square-size filter as _get_canvas_b64
                const ar = w / h;
                if (ar < 0.8 || ar > 1.25) continue;
                if (w < 80 || w > 800) continue;
                let opaque = 0;
                try {
                    const g = c.getContext('2d');
                    const d = g.getImageData(0, 0, Math.min(w, 320), Math.min(h, 320)).data;
                    for (let j = 3; j < d.length; j += 16) if (d[j] > 40) opaque++;
                } catch (e) {}
                const score = w * h * (0.3 + opaque / 400);
                if (score > bestScore) { bestScore = score; bi = i; }
            } catch (e) {}
        }
        return bi;
    }""")


async def _click_tiles(page, fr, indices: list[int]) -> None:
    """Click matching tile positions on the canvas via page.mouse.

    Uses the SAME canvas the vision model analyzed (best-content index) so the
    click coordinates align with the tiles the model saw. page.mouse.click
    dispatches real OS-level events that hCaptcha respects.
    """
    bi = await _best_canvas_index(fr)
    cbox = await fr.locator("canvas").nth(bi).bounding_box()
    if not cbox:
        return
    tw = cbox["width"] / _GRID
    th = cbox["height"] / _GRID
    for idx in indices:
        col = idx % _GRID
        row = idx // _GRID
        x = cbox["x"] + (col + 0.5) * tw
        y = cbox["y"] + (row + 0.5) * th
        try:
            await page.mouse.click(x, y)
            await asyncio.sleep(0.3)
        except Exception as e:
            log.debug("tile %d click: %s", idx, str(e).splitlines()[0])


def _cell_center(cbox: dict, idx: int, grid: int = _GRID) -> tuple[float, float]:
    """Return (x, y) center pixel of cell `idx` within the canvas bounding box."""
    tw = cbox["width"] / grid
    th = cbox["height"] / grid
    col = idx % grid
    row = idx // grid
    return (cbox["x"] + (col + 0.5) * tw, cbox["y"] + (row + 0.5) * th)


async def _solve_drag(fr, page, keypool) -> bool:
    """Solve a drag challenge: identify source and target cells, then drag."""
    b64 = await _get_canvas_b64(fr)
    if not b64:
        return False
    b64 = _compress_png_to_jpeg(b64)
    gridded = _grid_overlay(b64, _GRID)
    prompt = (
        f"This image is a {_GRID}x{_GRID} grid of square tiles on a white "
        f"background; each tile has a yellow number label directly ABOVE it "
        f"(0..{_GRID * _GRID - 1}). The task requires dragging one cell to another. "
        f"Look at what each cell contains. Identify which cell has the object "
        f"that needs to be moved (source) and which cell is the correct destination (target).\n"
        f"Reply ONLY two cell numbers: source,target\n"
        f"Example: 4,10"
    )
    text = await asyncio.to_thread(keypool.ask, gridded, prompt)
    log.info("_solve_drag -> %s", text[:100])
    nums = re.findall(r"\d+", text)
    if len(nums) < 2:
        log.warning("_solve_drag: couldn't parse source/target from %r", text[:80])
        return False
    src, tgt = int(nums[0]), int(nums[-1])
    cbox = await fr.locator("canvas").bounding_box()
    if not cbox:
        return False
    sx, sy = _cell_center(cbox, src)
    tx, ty = _cell_center(cbox, tgt)
    try:
        await page.mouse.move(sx, sy)
        await asyncio.sleep(0.2)
        await page.mouse.down()
        # animate drag in ~10 smooth steps
        steps = 10
        for i in range(1, steps + 1):
            fx = sx + (tx - sx) * i / steps
            fy = sy + (ty - sy) * i / steps
            await page.mouse.move(fx, fy)
            await asyncio.sleep(0.05)
        await page.mouse.up()
        await asyncio.sleep(1)
        log.info("_solve_drag: %d -> %d done", src, tgt)
        return True
    except Exception as e:
        log.warning("_solve_drag failed: %s", str(e).splitlines()[0])
        return False


async def _click_submit(fr, wait_for_btn: float = 0, mode: str = "any") -> bool:
    """Click the submit button (Skip/Next/Verify). Returns True if clicked.

    wait_for_btn: seconds to poll for the button to APPEAR first. Scattered
    odd-one-out challenges often show the submit/verify button only AFTER
    a shape is clicked; clicking before it exists does nothing silently.

    mode:
      "any"    — click whatever button is there (Skip/Next/Verify). Used to
                 cycle away from a hard challenge.
      "verify" — only click when the button is NOT "Skip". hCaptcha shows the
                 Skip link until a shape is actually selected; clicking it
                 while "Skip" means we bail out of a challenge we meant to
                 answer. Polls up to wait_for_btn for the label to change.
    """
    try:
        deadline = time.time() + wait_for_btn
        btn = None
        text = ""
        while time.time() < deadline:
            btn = await fr.query_selector(_SKIP_SEL)
            if btn:
                text = (await btn.inner_text() or "").strip()
                if mode == "verify" and text.lower() == "skip":
                    btn = None  # still in "no selection" state — keep polling
                    await asyncio.sleep(0.3)
                    continue
                break
            await asyncio.sleep(0.3)
        if not btn:
            btn = await fr.query_selector(_SKIP_SEL)
            if btn and mode == "verify":
                text = (await btn.inner_text() or "").strip()
                if text.lower() == "skip":
                    return False
        if btn:
            log.warning("submit button: %r (mode=%s)", text, mode)
            try:
                await btn.click(timeout=3000)
            except Exception:
                # Element covered by overlay — force click + JS fallback
                try:
                    await btn.click(force=True, timeout=2000)
                except Exception:
                    await fr.evaluate(
                        "() => { const b = document.querySelector('.button-submit');"
                        " if(b) b.click(); }"
                    )
            return True
        log.warning("submit button NOT FOUND (mode=%s)", mode)
        return False
    except Exception as e:
        log.warning("_click_submit error: %s", str(e).splitlines()[0])
        return False
    return False


async def solve_hcaptcha_challenge(fr, page, keypool, max_pages: int = 5) -> bool:
    """Run the hCaptcha image challenge through all pages to completion.

    Returns True if Verify was pressed (caller checks for token).
    """
    meta = await _challenge_meta(fr)
    if not meta.get("canvasRect"):
        log.info("no challenge canvas found")
        return False
    if meta.get("isDrag"):
        log.warning("drag challenge — best-effort via grid")
        solved = await _solve_drag(fr, page, keypool)
        if not solved:
            await _click_submit(fr)  # Skip if drag fails
        return solved

    target = meta["target"]
    if not target:
        log.info("no challenge target found")
        return False

    log.info("challenge: target=%r btn=%r", target, meta.get("buttonText"))

    for page_num in range(1, max_pages + 1):
        meta = await _challenge_meta(fr)
        target = meta.get("target", "")
        btn_text = meta.get("buttonText", "")

        log.info("page %d/%d: target=%r btn=%r", page_num, max_pages, target, btn_text)

        if btn_text.lower() in ("verify", "verifizieren", "verificar", "vahvista"):
            break  # already on verify page, just click

        # Skip check for this fr before classify (can get stale between pages)
        fr = _find_challenge_frame(page)
        if not fr:
            log.warning("challenge frame lost")
            return False

        # Classify tiles and click matches (with retry)
        if target:
            positives = await _pick_cells(fr, keypool, target)
            log.info("grid pick -> %s", positives)
            await _click_tiles(page, fr, positives)
        else:
            log.info("no target text on this page — clicking first tiles as guess")
            await _click_tiles(page, fr, list(range(_GRID)))

        await asyncio.sleep(2)

        # Click Next/Verify to advance
        clicked = await _click_submit(fr)
        if not clicked:
            return False
        if btn_text.lower() in ("skip", "跳过", "huppel", "ohita", "überspringen"):
            return False  # user skipped, not solved
        await asyncio.sleep(2)

    # After last page, check for "Verify" button
    fr = _find_challenge_frame(page)
    if fr:
        meta = await _challenge_meta(fr)
        log.info("final state: btn=%r", meta.get("buttonText"))
        if meta.get("buttonText", "").lower() != "skip":
            await _click_submit(fr)

    return True


def _find_challenge_frame(page):
    """Return the hCaptcha challenge frame, or None."""
    for fr in page.frames:
        u = fr.url or ""
        if "#frame=challenge" in u and "hcaptcha" in u:
            return fr
    return None
