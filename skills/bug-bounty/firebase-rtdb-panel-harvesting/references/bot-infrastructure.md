# Bot Infrastructure Analysis Patterns

## Telegram Bot Pattern

When source code is found inside a panel, it almost always follows this shape:

```javascript
const BOT_TOKEN = '<digits>:<alphanumeric>';
const BOT_USERNAME = '<botname>';
const TELEGRAM_API = `https://api.telegram.org/bot${BOT_TOKEN}`;
```

Extract the token and username. Verify with `getMe`. If active, the bot is
listening for messages/callbacks.

## Firebase Panel List Pattern

Bots embed their panel sources in a `DEFAULT_PANELS` array:

```javascript
const DEFAULT_PANELS = [
  { url: 'https://<name>-default-rtdb.firebaseio.com', key: 'AIzaSy...' },
  ...
];
```

Extract all URLs and keys. These are the live sources the bot polls.

## Attack Flow Pattern

Typical Jio Gemini activation bot flow:

1. `sendJioOtp(mobile)` → POST `https://www.jio.com/api/jio-login-service/login/sendOtp`
2. `waitForOtpForTarget()` → poll Firebase RTDB for incoming SMS
3. `verifyJioOtp(mobile, otp)` → POST `https://www.jio.com/api/jio-login-service/login/validateOtp`
4. `getActivation(cookieJar)` → chain of Jio OTT API calls
   - `authenticate/authJsonData`
   - `ott/subscription/navigate/Z0241`
   - `ott/subscription/activate/Z0241`
   - `ott/subscription/google-ai` → extract `redirectionURL`
5. Return `serviceactivation.google.com/subscription/new/<TOKEN>`

## Hosting Region

Look for:
- `AWS Mumbai (ap-south-1)`
- `PORT: process.env.PORT || 8080`
- Healthcheck server on port 8080
- `dns.setDefaultResultOrder('ipv4first')` — AWS IPv4 preference

## Auto-Claim Batch Mode

Bots often have a batch mode:
```javascript
async function executeAutoClaimAll(chatId) {
  const targets = await scanPanels();
  const total = Math.min(simTargets.length, 12);
  for (let i = 0; i < total; i++) {
    await executeAutoClaim(chatId, simTargets[i]);
  }
}
```

Batch size is typically 6-12 numbers per run.

## CAPTCHA Bypass Pattern

When Jio returns `CAPTCHA_REQUIRED`, the bot pivots to a manual-assist mode:
- Display a "Open Jio Login Page" button
- Continue listening on Firebase for the OTP
- The user manually requests OTP on their phone
- Bot intercepts and returns the code

This is the most reliable path when running from cloud datacenters.
