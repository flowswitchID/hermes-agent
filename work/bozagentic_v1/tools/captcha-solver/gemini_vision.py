"""Gemini vision backend for the hCaptcha image solver — drop-in for mistral_vision.KeyPool.

Same interface: KeyPool(keyfile, model=...) with .keys and .ask(image_b64, prompt) -> str.
Uses the official Google generativelanguage API (REST, no SDK needed).

Model can be a comma-separated list ("gemini-3.1-flash-lite,gemini-3-flash-preview") —
each ask() round-robins across models so voting gets diverse opinions.
"""
import base64
import json
import os
import threading
import time
import urllib.error
import urllib.request

_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class KeyPool:
    # Gemini vision timeout: default 30s was too short for large canvases.
    # 60s gives margin for 429 retries + large image upload.
    def __init__(self, keyfile=None, model=None, timeout=60):
        self.keys: list[str] = []
        env_key = os.getenv("GEMINI_API_KEY", "").strip()
        if env_key:
            self.keys.append(env_key)
        if keyfile and os.path.exists(keyfile):
            for line in open(keyfile, encoding="utf-8"):
                k = line.strip()
                if k and k not in self.keys:
                    self.keys.append(k)
        if not self.keys:
            raise RuntimeError("GEMINI_API_KEY not set and no keyfile given")
        # apikey.txt in the solver dir holds MISTRAL keys — never mix them in.
        # Gemini keys start with "AQ." (Google AI Studio). Filter strictly; if
        # only Mistral keys were found, keep the env key (if any) else error.
        env_only = bool(env_key)
        self.keys = [k for k in self.keys if k.startswith("AQ.")]
        if not self.keys:
            if env_only:
                self.keys = [env_key]
            else:
                raise RuntimeError("no valid Gemini key found (expected AQ.* prefix)")

        raw = model or os.getenv("HCAPTCHA_GEMINI_MODEL", "gemini-3.1-flash-lite")
        self.models = [m.strip() for m in raw.split(",") if m.strip()]
        if not self.models:
            self.models = ["gemini-3.1-flash-lite"]
        self.model = self.models[0]  # compat attr
        self.timeout = timeout
        self._idx = 0
        self._lock = threading.Lock()
        self._last_error = ""
        # Warmup: first Gemini call takes 30-70s cold. Fire a cheap ping
        # at init so the first REAL call is fast (~4s).
        threading.Thread(target=self._warmup, daemon=True).start()

    def _warmup(self):
        """Fire a tiny request to warm the Gemini connection pool."""
        try:
            import base64 as _b64
            from io import BytesIO
            from PIL import Image as _Img
            img = _Img.new("RGB", (4, 4), "white")
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=50)
            tiny = _b64.b64encode(buf.getvalue()).decode()
            self.ask(tiny, "Reply OK")
        except Exception:
            pass

    def ask(self, image_b64: str, prompt: str, timeout=None) -> str:
        """Ask one model (round-robin across keys AND models). Returns text."""
        with self._lock:
            key = self.keys[self._idx % len(self.keys)]
            model = self.models[(self._idx // len(self.keys)) % len(self.models)]
            self._idx += 1

        body = json.dumps({
            "contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/png", "data": image_b64}},
            ]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200},
        }).encode("utf-8")

        req = urllib.request.Request(
            _API.format(model=model),
            data=body,
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        )
        to = timeout or self.timeout
        # On HTTP error, retry with the NEXT model (bad-request/rate-limit
        # issues are often model-specific). 429 gets exponential backoff;
        # after exhausting every key/model we return "" so the solver keeps
        # going with fewer opinions instead of crashing the whole challenge.
        for attempt_no in range(4):
            try:
                with urllib.request.urlopen(req, timeout=to) as resp:
                    d = json.load(resp)
                parts = d.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts).strip()
                if not text:
                    self._last_error = f"{model}: empty response"
                return text
            except urllib.error.HTTPError as e:
                detail = ""
                try:
                    detail = e.read().decode()[:300]
                except Exception:
                    pass
                self._last_error = f"{model}: HTTP {e.code} {e.reason} {detail}"
                if e.code == 429:
                    time.sleep(1.5 * (attempt_no + 1))
                elif e.code == 400:
                    # prompt/image rejected — retrying won't help, try next model
                    time.sleep(0.3)
                elif e.code >= 500:
                    time.sleep(1.0 * (attempt_no + 1))
                # rotate to next key/model
                with self._lock:
                    self._idx += 1
                    key = self.keys[self._idx % len(self.keys)]
                    model = self.models[(self._idx // len(self.keys)) % len(self.models)]
                req = urllib.request.Request(
                    _API.format(model=model),
                    data=body,
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                )
            except Exception as e:
                self._last_error = f"{model}: {e}"
                raise
        # all keys/models exhausted (likely quota) — degrade gracefully
        self._last_error = f"{model}: exhausted keys/models ({self._last_error})"
        return ""
