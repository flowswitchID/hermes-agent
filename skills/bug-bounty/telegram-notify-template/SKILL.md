---
name: telegram-notify-template
description: Send Telegram alerts for activation-link farming runs.
---

# Telegram Notification Templates

## Implementation Pattern
```python
import os, requests

def get_telegram_creds():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    return token, chat_id

def send_telegram(text, parse_mode="HTML"):
    token, chat_id = get_telegram_creds()
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False
```

## Activation Alert (HTML)
```python
account = cookie_profile.get('email', 'unknown') if cookie_profile else 'none'
msg = (
    f"✅ <b>ACTIVATED</b>\n"
    f"Link: {link}\n"
    f"Account: {account}\n"
    f"Verify: {verify_msg}"
)
send_telegram(msg)
```

## Redeemed Unverified Alert (HTML)
```python
msg = (
    f"⚠️ <b>REDEEMED_UNVERIFIED</b>\n"
    f"Link: {link}\n"
    f"Verify: {verify_msg}"
)
send_telegram(msg)
```

## Final Summary (HTML)
```python
msg = (
    f"📊 <b>PROMO FARM SUMMARY</b>\n"
    f"ACTIVATED: {activated}\n"
    f"REDEEMED: {redeemed}\n"
    f"EXPIRED: {expired}\n"
    f"USED: {used}\n"
    f"TOTAL: {total}\n"
    f"Results: {output_file}"
)
send_telegram(msg)
```

## Send Parameters
- `parse_mode`: HTML
- `disable_web_page_preview`: True
- Timeout: 15s
- Fail silently if token/chat_id missing; do not crash farm loop.

## Pitfalls
- Telegram message length limit is 4096 chars. Truncate link lists if necessary.
- HTML parse_mode requires escaping `<` and `>` in user-generated content. Activation URLs are safe.
- Bot must be started (user sent /start) or chat_id must be exact for delivery.