# API Audit Patterns — Session-Derived Reference (Rolly No-KYC Casino, 2026-07)

Patterns and findings from no-account-credential audits of Rolly.io (Next.js + socket.io + Gitbook docs, with ZK-verified on-chain casino + Rakeback / Weekly Bonus / VIP Transfer / Affiliate commission / Points mining / Early Rollers Race leaderboard). The audit runs entirely on public docs and JS-bundle reverse-engineering because Rolly is explicitly no-KYC wallet-based. Patterns are portable to any no-KYC crypto-casino whose affiliate / bonus / VIP logic ships in client bundles.

## 0. First-Move: Lock the Budget

A no-KYC gambling audit can easily hit a tool-call budget. The biggest wastes this session ran into:

- **Loading chunks one by one in serial curl loops.** Each chunk download is a separate tool call. Batch them: download the affiliate page once, extract all chunk URLs in one grep, then iterate with `for url in $(cat urls); do curl ... &` in a single shell command that downloads everything to disk in one call.
- **Chasing decorative code paths.** When a chunk returns 9 bytes (a CSS chunk), don't load it as a JS file. Filter for the JS chunks only.
- **Grepping the same patterns repeatedly.** Pick the highest-value greps (`emit(`, `getReferral`, `commissionRate`, `fetch(\`${e}/api/`, `?r=`, regex literals) and run them once against every downloaded chunk in a single tool call.
- **Trying to enumerate the socket.io server URL.** Often it's constructed in a code-split module that the page doesn't ship. If you can't find it in 3 attempts, document that it's server-only and stop.

Always: (a) download everything, (b) grep everything, (c) THEN form hypotheses, in that order. Don't explore interactively.

## 1. Gitbook `.md` Export is the Schema (Medium — prerequisite for everything)

**Symptom:** The target's docs are hosted on Gitbook. Every page can be fetched as Markdown by appending `.md` to the URL, and `llms.txt` lists every page.

**Detection recipe:**
```bash
# 1. Get the page index
curl -sL https://docs.target.com/llms.txt

# 2. Walk every page, save the .md
for path in programs/vip-transfer-program programs/affiliate-program \
            casino/bonuses tech-specs programs/bug-bounty-program verify-official-channels \
            terms-and-policies help-center/24-7-support; do
  curl -sL "https://docs.target.com/${path}.md" -o "${path//\//_}.md"
done
```

**What you get:**
- Exact formula for every bonus (`Rakeback = Wager × HouseEdge × 15%`, `Commission = Wager × HouseEdge/2 × Your%`)
- Eligibility thresholds ("$100 deposited, $500k wagered on other platforms, 1-month trial")
- Race-pool sizes ("10M Rolly Points", "$5,000 referral pool", "$120,000 top target")
- The published house edges per game (Rolly Originals: 1% on dice/keno/coinflip/crash, 2% on limbo/plinko — all stated as 99% and 98% RTP)
- Exact expiration mechanics ("Weekly Bonus burns at next Monday 00:00 UTC, doesn't accumulate")

**Why it's a finding for the audit, not a vulnerability:** A precise formula in the docs lets you reverse-engineer the SQL/JS that implements it, then check for off-by-one / rounding / cap / overflow bugs.

**Cross-reference for bonus formula bugs:** Any "exact formula in docs" should be checked for:
- Rounding direction (banker vs. round-half-up vs. truncate)
- Currency precision (USDT has 6 decimals, but rakeback may be paid in integer cents)
- Per-bet cap vs. cumulative
- House edge in basis points vs. percentage (1.0% vs 100 bp)

## 2. Referral Link Format is `/r=CODE` Query Param (High)

**Symptom:** The default referral link format is `https://target.com?r=CODE`. The CODE is exposed in the URL bar and can be anything the user chose.

**Detection recipe (from JS bundle):**
```bash
grep -oE 'getReferralLink.{0,80}' chunk_*.js
# Found: getReferralLink = (e) => "https://rolly.io?r=" + e
```

**Validation pattern in the bundle (look for regex literals):**
```bash
grep -oE '/\^\[a-zA-Z0-9_.\][+]\$/' chunk_*.js | sort -u
# Found: /^[a-zA-Z0-9_]+$/ — only the character class is validated
```

**What this implies:**
- The code is **user-chosen**, not server-generated
- The character class allows lowercase, uppercase, digits, and underscore
- A user can squat `admin`, `vip`, `rolly_support`, `support_`, etc.
- The server must enforce uniqueness; if it doesn't, an attacker can re-claim codes

**The test plan (auth required):**
```bash
# 1. Create campaign with code "admin"
socket.emit("referrals.create", { name: "x", code: "admin" })

# 2. Check if the resulting link serves a branded "admin" landing
curl -sL "https://target.com?r=admin" -A "Mozilla/5.0" | grep -oE 'Rolly|<title>[^<]+'

# 3. Try a brand-jacking code; expect 400/409 if uniqueness is enforced,
#    or 200 with the attacker's link if it isn't
```

**Report framing:** "Referral code is user-chosen with only character-class validation (`^[a-zA-Z0-9_]+$`). An attacker can claim brand-impersonating codes (`admin`, `support`, `vip`, or any string that looks official) for use in phishing campaigns. Even if server uniqueness is enforced, the *first* user to claim each code wins it permanently — a public lookup of which codes are already taken would confirm or deny. CWE-287 (Improper Authentication) or CWE-20 (Improper Input Validation) depending on whether the unique check exists."

## 3. Socket.io Events: `referrals.create / edit / withdraw` (Critical)

**Symptom:** The frontend talks to a socket.io gateway with event names that match the feature domain. Listing the events from the bundle reveals the entire state-machine surface.

**Detection recipe:**
```bash
# Find every emit() call across all chunks
grep -hoE 'emit\("[a-zA-Z._]+"' chunk_*.js | sort -u
# Output (Rolly example):
# emit("battles.join")
# emit("battles.leave")
# emit("battles.listBattles")
# emit("referrals.campaignsList")
# emit("referrals.create",{name,code})
# emit("referrals.edit",{campaignId,name})
# emit("referrals.referralsList",{...})
# emit("referrals.remove",{campaignId})
# emit("referrals.withdraw")
# emit("leaderboard.getLeaderboard")
# emit("pointsMining.activateDailyBoost")
# emit("pointsMining.activateWagerBoost")
# emit("pointsMining.getMinedBalance")
# emit("pointsMining.total")
# emit("pointsMining.userBoostsByDay")
# emit("profile.updateSettings")
# emit("profile.getIntercomJwt")
# emit("games.slots.initGame")
# emit("gamelist.getGamesByProvider")
# emit("gamelist.getProvidersAndCategories")
# emit("gamelist.getRecommendedGames")
# emit("slots.getLinkForDemo")
```

**Each event implies a server endpoint to probe. The interesting ones for business logic:**

- `referrals.create` — user-chosen code; check for duplicate-code handling, special-code blacklist (admin/rolly/support), case-sensitivity, trailing whitespace
- `referrals.edit({campaignId, name})` — rename attacks; can the user change the *code* itself? Is the `campaignId` derived from the authenticated user?
- `referrals.withdraw` — claim; check the floor (`$2` per docs) is enforced server-side
- `pointsMining.activateDailyBoost` / `activateWagerBoost` — timing race (see §6)
- `profile.updateSettings` — mass-assignment candidate; see if `commissionRate` or `vip` are settable fields

**The check for user-mutability of `commissionRate` is *critical* and the JS bundle often tells you the answer:**
```bash
# Look for whether commissionRate is sent in any emit()
grep -hoE 'emit\("[^"]+",[^)]*commissionRate[^)]*\)' chunk_*.js
# If empty, the field is read-only. If present, the server is accepting it.
```

On Rolly: `defaultCampaign.commissionRate` is *read* from the server response and *never sent* in any emit. The field is read-only on the client, which is the correct shape — but the server must still reject any `commissionRate` field in the socket payload. Probe with a custom client.

## 4. The `?r=` Attribution Race (Critical)

**Symptom:** Referral attribution happens when a new user lands on `?r=CODE`. The question is: *when* does the code get attached to the new account? At cookie-write time, at signup, at first deposit, or at first bet?

**The race condition:** If attribution is captured at cookie-write (or any pre-deposit step), the attacker can:
1. Open incognito window A, navigate to `target.com?r=ATTACKER_CODE`
2. Open incognito window B, navigate to `target.com?r=ATTACKER_CODE` in the same browser (so they share a session/cookie jar) — or in a different browser on the same machine
3. Sign up in B → B's account is attributed to A's code
4. Create account C in a new incognito, deposit, lose → C's full house-edge loss generates commission to A
5. Repeat for D, E, F, …, 100s of accounts

If, in addition, attribution is at **deposit or signup** (not "first real bet"), the attacker can also reverse the flow: have C sign up with C's own code (so C's wagering earns points to C), but later change C's referrer to A via an API call. Probe both directions.

**The "first-bet" gate does not save you.** If the *first bet* is what locks attribution, but a low-effort demo/free-spins bet counts, the attacker can still:
1. Open 100 browser profiles (Chrome profiles, multi-login wallets)
2. Sign up each on `?r=ATTACKER_CODE`
3. Each makes a 1-cent "qualifying bet" to lock attribution
4. Each then makes a 1-cent bet on a 99% RTP game → loses 0.01¢ per account per bet
5. Server-side: 100 accounts × per-account commission = 100x commission
6. After threshold ($2), `referrals.withdraw` → cash out

**Cost of attack: 100 × 2 × 0.01 = $2.00 to drain $200 in commission.** On a 10% rake that's 20,000x ROI. (The `?r=` attribution race is the #1 most-likely-to-be-real bug on any no-KYC gambling program; on Rolly it's unverified pending a real account.)

**Detection recipe (with account):**
```bash
# Open two private browsing windows. Sign up in each via the same ?r=CODE link.
# Deposit minimum, place a single 0.01¢ bet. Check the affiliate dashboard:
# does it show two referrals under that code? Does the commission aggregate?
# If yes, the race is real.
```

**Report framing:** "Referral self-attribution enables unlimited commission farming. By signing up multiple accounts through my own referral link (each making the minimum qualifying bet), I can generate `n × 10% × house-edge × wager` commission per cycle, then withdraw after the $2 floor. On a $1 wager at 1% house edge, that's $0.001 per fake referral per bet. To drain the $5,000 monthly pool, an attacker needs to generate ~$5M of fake wagering, which at 0.001 per bet per account is ~5M bets across ~5,000 accounts at 1,000 bets each — but the attacker controls the bet size. CWE-840 (Business Logic Errors)."

## 5. Server-Side Field `targetAudience.vip` for Game Gating (Medium)

**Symptom:** The game list returned from `/api/search-games` (or equivalent) includes a per-game field like `preRelease: { targetAudience: { vip: false } }`. This is the server's "who can see this game" gate.

**Detection recipe:**
```bash
curl -sL "https://target/api/search-games" | python3 -c "
import json,sys
d = json.load(sys.stdin)
for cat in d.get('data', {}).get('games', {}).values():
    for g in cat.get('games', []):
        pre = g.get('preRelease', {})
        if pre.get('targetAudience', {}).get('vip'):
            print('VIP-GATED:', g.get('name'), g.get('_id'))
"
# Output (Rolly example): no VIP-gated games currently; all show vip:false
```

**What to look for:**
- The field name (`vip`, `tier`, `level`, `audience`, `accessLevel`) — useful for later authenticated testing
- The current value: any game with `vip: true` is the test target
- Whether the field is honored by the `/games/slots/initGame` socket emit (i.e., can a non-VIP user start a VIP-gated game?)
- Whether the field is honored by the public game list (i.e., does the list endpoint *filter* the games, or just *flag* them?)

**Common bug:** the list endpoint *flags* games but doesn't *filter*. The init endpoint then enforces the flag client-side by checking the user's tier. The server-side enforcement on `initGame` is missing → low-tier user can start a VIP-gated game.

**To probe without auth:** The list endpoint is public. The init endpoint requires auth. If init just returns the game URL and the game itself runs in an iframe against a separate (possibly unauthenticated) launch URL, you may be able to reach the game URL via `slots.getLinkForDemo` (the demo version is usually public).

## 6. Daily Boost Activation Race (High)

**Symptom:** A "daily boost" or "challenge boost" gives a temporary multiplier to points mining. The user must "activate" the boost once they've earned enough qualifying activity. The activation is a discrete client emit.

**Detection recipe (from bundle):**
```bash
grep -hoE 'emit\("[^"]*[Bb]oost[^"]*",[^)]*\)' chunk_*.js
# Found:
# emit("pointsMining.activateDailyBoost")
# emit("pointsMining.activateWagerBoost")
```

**The race:** If the server checks "did the user earn 500 wager points today" *at activation time*, the user can:
1. Activate the boost *before* earning 500 → server returns 200 because the check uses stale state
2. Or: emit the activation 100 times in a 100ms window → each emit hits a different backend worker before the "already activated" lock is set → 100x boost stack

**Or more commonly:** The boost is meant to be a "claim the boost you earned" button. If the server is not enforcing "you have 500 points today" and the client-side check is the only gate, an attacker who can read the client can skip the gate.

**Doc language that hints the race is real:**
> "Earn 500 Rolly Points through wagering in a day to unlock a +20% boost lasting 24 hours. You choose when to activate it, but if you don't do this before 10:00 UTC the next day, it expires."

"You choose when to activate" + "24 hours long" + "expires 10:00 UTC" is the public phrasing. The actual server behavior on a premature activate is not specified. **Test it.**

**The "wager boost" specifically** ("Earn 500 Rolly Points through wagering in a day") is the highest-stakes one. If it's activated without actually having 500 points, and the server doesn't re-check, the boost compounds the *next* 500 points at +20% AND extends the activation window. The compound effect makes this worth a Critical if confirmed.

**To probe with account:**
```bash
# Right after signup, before any wager
socket.emit("pointsMining.activateWagerBoost", {})
# If 200, server doesn't check the qualifier. Critical.
# If 400/422 with "insufficient points", server enforces. Closed.
```

## 7. Rakeback Rounding / Off-by-One (Medium)

**Symptom:** `Rakeback = Wager × HouseEdge × 15%` is computed per bet. The precision at which Wager and HouseEdge are stored determines whether the user is over- or under-paid.

**Detection recipe (from bundle):**
```bash
grep -hoE 'Rakeback|houseEdge|house_edge|houseedge' chunk_*.js | sort -u
# The houseEdge field appears in the game settings endpoint
curl -sL "https://target/api/front-gateway/getGameSettings" | python3 -m json.tool | head -100
```

**What to look for:**
- Is `houseEdge` stored as a float, a percentage, or a basis-point integer?
- Is the per-bet calculation done in integer math (floor), float math (round-half-to-even), or banker's rounding?
- Does the *cumulative* rakeback get re-rounded every bet, or is the running sum stored at full precision?
- Is there a per-bet cap on rakeback? (Some casinos cap at e.g. 1 USDT to limit bonus abuse on huge bets.)

**The off-by-one risk:** If `houseEdge` is stored as `0.01` (1%) but the formula computes `Wager × 0.01 × 0.15` in float math, on a $1,000,000 bet you get a precision drift of `~0.000001` per calc. Over 1000 bets the cumulative drift is on the order of micro-cents. **Not exploitable.** But if `houseEdge` is stored as `100` (basis points) and the formula divides by `10000` at the wrong point, the per-bet calculation can drift by up to 1 cent, which over thousands of bets is meaningful.

**A more practical rounding bug:** A user's available rakeback is displayed as `$1.999` and the claim threshold is `$2`. The user claims at `$1.999` and the server rounds *down* to `$1.99` — the user lost a fraction of a cent. Over thousands of claims, the platform under-pays its own users. (Not security, but a known pattern in real audits.)

## 8. Composite Recon Script for No-KYC Casino Targets (Recipe)

```bash
TARGET="https://target.com"
DOCS="$TARGET-docs"
OUT="audit-$(date +%Y%m%d)"; mkdir -p $OUT && cd $OUT

# A. Pull docs (assuming Gitbook-style or similar with .md export)
curl -sL "$DOCS/llms.txt" -o llms.txt
for path in $(grep -oE "$DOCS/[a-z0-9/-]+\.md" llms.txt | sort -u); do
  curl -sL "$path" -o "$(basename $path)"
done

# B. Pull the main page; extract chunk URLs
curl -sL "$TARGET/" -A "Mozilla/5.0" -o home.html
chunks=$(grep -oE '/_next/static/chunks/[a-zA-Z0-9_~.-]+\.js' home.html | sort -u)

# Also pull the most likely feature pages
for p in affiliate referral mining bonus campaigns rewards; do
  status=$(curl -sLI "$TARGET/$p" -A "Mozilla/5.0" -o /dev/null -w '%{http_code}' 2>/dev/null)
  if [ "$status" = "200" ]; then
    extra=$(curl -sL "$TARGET/$p" -A "Mozilla/5.0" | grep -oE '/_next/static/chunks/[a-zA-Z0-9_~.-]+\.js')
    chunks="$chunks $extra"
  fi
done

# C. Download all chunks in one pass
for c in $(echo "$chunks" | sort -u); do
  curl -sL "$TARGET$c" -o "chunk_$(basename $c .js).js"
done

# D. Extract API surface and event names in one pass
echo "=== Front-gateway endpoints ==="
grep -hoE 'fetch\([^)]*front-gateway[^)]*\)' chunk_*.js | sort -u
echo
echo "=== Socket events emitted ==="
grep -hoE 'emit\("[a-zA-Z._]+"' chunk_*.js | sort -u
echo
echo "=== Validation regexes ==="
grep -hoE '/\^\[a-zA-Z0-9_./+()-]+\[+]\$/' chunk_*.js | sort -u
echo
echo "=== URL builders (referral, claim, etc.) ==="
grep -hoE 'getReferralLink|getCampaignLink|getVipLink|getBonusLink' chunk_*.js | sort -u
echo
echo "=== User-mutable fields in emit() ==="
grep -hoE 'emit\("[^"]+",\{[^}]*\}\) ' chunk_*.js | sort -u | head -50
echo
echo "=== VIP-gated / restricted games ==="
curl -sL "$TARGET/api/search-games" -A "Mozilla/5.0" 2>/dev/null | \
  python3 -c "
import json,sys
d = json.load(sys.stdin)
for k,v in d.get('data',{}).get('games',{}).items():
    for g in v.get('games',[]):
        if g.get('preRelease',{}).get('targetAudience',{}).get('vip'):
            print('VIP-GATED:', g.get('name'))
        if g.get('restrictedCountries'):
            print(g.get('name'), 'restricts', len(g.get('restrictedCountries',[])), 'countries')
"

# E. Cross-reference docs and code
# For every formula in the docs, grep the bundle for the same variables
for formula in Rakeback WeeklyBonus Commission OnchainMultiplier ChallengeBoost CheckInBoost; do
  echo "=== $formula ==="
  grep -hoE ".{50}$formula.{50}" *.md | head -3
  grep -hoE ".{30}$formula.{30}" chunk_*.js | head -3
done
```

**Expected output on a typical no-KYC casino:**
- 10-30 docs, each with an exact formula
- 30-50 JS chunks, with 5-30 socket events
- 1-3 regexes validating user input (often weak)
- A list of VIP-gated games (if any)
- A list of restricted countries
- A mapping of "doc says X" → "code computes X" — divergences are findings

## 9. The "No Account Required" Audit Boundary (Reminder)

Most impactful bugs in no-KYC gambling programs require:
- A real wallet (smallest denomination, ~$5 in ETH/BNB/SOL)
- Connection to the program's socket.io gateway (URL is server-side and not always findable in the bundle)
- Several days of test data to verify rolling-window mechanics (weekly bonus, monthly target bonuses, 14-day welcome bonus drops, 1-month VIP trial wagering)

**The right play on this kind of target:**
1. Submit the static analysis findings (formula divergence, regex weakness, user-chosen code, daily-boost emit surface) as a single Medium report titled "Business Logic Recon: Static Analysis of [Target] Affiliate / Bonus System"
2. The Bug Bounty program description explicitly says "any feature available on your account" — features are the test surface, not the source code
3. Most programs will grant a small test account for a serious recon report

**What you CAN'T prove without auth:**
- Actual server-side enforcement of the `?r=` attribution timing
- Whether `commissionRate` is server-rejected if you send it
- Whether the daily-boost emit has a server-side qualifier check
- Whether the welcome-bonus 14-day drops expire properly
- Whether the VIP trial wager counter is player-bound

**What you CAN claim from static analysis alone (Medium severity):**
- User-chosen referral code without blacklist (`/^[a-zA-Z0-9_]+$/` is a weak validation)
- Frontend code structure that *implies* a self-attribution race if attribution happens pre-bet
- Doc/code divergence on commission formula
- Public game-list endpoint that exposes per-game VIP flags
- The full socket.io event surface (information disclosure, CWE-200)

## 10. The "Welcome Bonus Half-Instant / Half-Daily-Drop" Time-Bomb (Medium)

**Pattern from docs:**
> "A free bonus from $100 to $500, based on your confirmed wager elsewhere. Half is paid instantly, and the other half over 14 days as daily drops (they don't accumulate)."

**The check:** "They don't accumulate" is the load-bearing clause. It means daily drops are forfeited if unclaimed for 24 hours. If the server stores the drops as a 14-row table and marks rows as "claimed" or "expired" at the right time, it's correct. If the server stores a single cumulative number and the user can re-trigger the drop calculation by some action (e.g. switching wallet, re-claiming the welcome bonus after a deposit churn), the user could harvest the unclaimed drops multiple times.

**Static check (from bundle):**
```bash
grep -hoE 'welcomeBonus|welcome_bonus|dailyDrop|daily_drop' chunk_*.js | sort -u
# If the welcome bonus is fetched on a 24h cadence, look for cache busts
# If the welcome bonus is gated by a "claimCount" counter, look for the reset trigger
```

**Dynamic check (with account):**
1. Deposit qualifying amount
2. Receive welcome bonus (e.g., $200, with $100 instant + $100 over 14 days = $7.14/day)
3. Do nothing for 14 days; the 14 × $7.14 unclaimed drops should be $0
4. Re-do the qualifying action (deposit + wager); does the welcome bonus re-fire?
5. If it re-fires, the drop table is *new* per welcome bonus — unclaimed drops from the first round are forever lost (acceptable) but the new round is claimable (acceptable). Test anyway.
6. The actual bug: if the drop table is *reused* and the new round resets the 14-day counter without re-paying the instant half, the drops can be harvested by waiting 14 days between welcome bonuses.

## 11. The "Default Campaign" vs. "Custom Campaign" Distinction (Medium)

**Pattern from Rolly docs:**
> "Your default campaign is already active from day one, no additional setup needed."

**Implication:** Every user has a default campaign whose code is *server-generated* (presumably). Custom campaigns (the ones users can create with `referrals.create`) have user-chosen codes. The default campaign's commission rate is also server-set (10% per docs).

**The bug class:** If the custom campaign's code is user-chosen and the default campaign's code is server-generated, a user can create a custom campaign whose code matches the default campaign's code (or another user's default campaign). The server must reject this. If the server only checks uniqueness within the user's own campaigns, two different users can each have a campaign with the same code — and the attribution is non-deterministic (whichever the lookup hits first wins).

**Static check:** Look for the `defaultCampaign.code` field. If it appears in any `?r=` URL builder output, the default campaign's code is the actual attribution handle. If a user can spoof it via `referrals.create` with the same code, attribution is compromised.

**On Rolly specifically:** the default campaign's code is not visible in the JS bundle (it's returned at runtime by `referrals.campaignsList`). The `getReferralLink` function in the bundle takes the code as a parameter — which means it can be called with *any* code, not just the default. The custom-campaign code path is therefore just as user-controllable as the docs imply.

## 12. The "Rolly Originals `preRelease` Is the *Real* On-Chain Beta" (Informational)

**Finding (from `/api/search-games`):** All 6 Rolly Originals (dice, keno, limbo, coinflip, plinko, crash) have `"preRelease": { "targetAudience": { "vip": false }, "isNew": true, "endDate": "2026-07-02T..." }` and `"isPreRelease": true`.

**What this means:** The Originals (which are advertised as "the first ZK-verified casino games on the market" in the docs) are still in pre-release. The `endDate` is in the past (`2026-07-02`), which suggests the pre-release window has closed but the `isPreRelease` flag is still on the wire.

**Implications for the audit:**
- The RTPs are set artificially high (99% / 98%) during pre-release to encourage play
- After pre-release ends, the RTPs may drop
- The `preRelease` flag is the *server's* per-game state machine, not a UI hint — this is a real backend field that's worth monitoring for changes
- Any game with `vip: true` in `targetAudience` would be a server-side VIP gate that bypasses the UI's default tier display

**Track this field over time.** If a new Originals release flips `vip: true`, the gate activates and a fresh audit of the new gate is warranted.

## 13. The "Validate BNB for Gas" Hint (Low — minor user-friction finding)

**From Early Rollers Race docs (Level 2 / Level 3 badge claim):**
> "Make sure you have a small amount of BNB in your wallet to cover gas fees for claiming badges. A couple of dollars in BNB should be enough."

**What this tells you:** The program mints on-chain Badges (SBTs) when users claim level rewards. Each mint costs BNB gas. The user pays the gas.

**Audit implication:** The `WalletIcon` component (referenced in the bundle) is just the icon; the actual mint transaction is built client-side from the badge-claim endpoint. The endpoint must return a `gasEstimate` or rely on a default gas limit. If the gas estimate is off by an order of magnitude (e.g. 21k gas for an SBT mint that actually costs 200k), the user's wallet will show "out of gas" or silently fail. This is a *user-experience* bug, not a security one, but it's worth noting in the report.

**Security-flavored variant:** If the badge-claim endpoint returns a `to:` address that's user-controlled, an attacker could redirect the mint to a contract they control, intercepting the SBT. Probe by capturing the `init` payload from `games.slots.initGame` and similar endpoints and checking if any field is user-mutable.

## 14. The Bug Bounty Program Constraint (Methodology)

Most no-KYC gambling programs (Rolly included) have:
- A low cap on Critical ($5,000 USDT max)
- A 30-day program window
- Manual review with intercom chat as the only report channel
- "First to report" reward; no consolidated payout
- "Any feature available on your account" as the test surface

**This makes the optimal play:**
1. Find the highest-impact bug that can be confirmed without an account (Medium severity, $200–750 USDT)
2. Submit early (the 30-day window is short; later submissions are deprioritized)
3. Use the static analysis findings as a "recon" report and request a test account for follow-up
4. The reward for static analysis alone is usually Small (Rolly Points, $1–50); the reward for a confirmed Critical is up to 5,000 USDT — but only with a real account

**Don't waste 4 hours finding 5 Small bugs when 1 hour of static analysis produces a Medium-tier recon report that requests escalation access.**

## 15. Open Questions (Things This Audit Couldn't Confirm Without an Account)

These are the things that, if confirmed, would each be a Critical-severity finding. Each is one socket emit and one boolean answer:

| # | Question | Server response that confirms | Server response that closes |
|---|---|---|---|
| 1 | Does `referrals.create` reject duplicate or blacklisted codes? | 200 with the new code (no check) | 409 / 400 with "code already in use" or "code reserved" |
| 2 | Does `referrals.create` accept a `commissionRate` field from the client? | 200 with the attacker-set rate | 200 but server overrides |
| 3 | Does `referrals.withdraw` enforce the $2 minimum server-side? | 200 for amounts < $2 (closes this attack) | 400 with "below minimum" |
| 4 | Does `pointsMining.activateWagerBoost` check that 500 points were earned today? | 200 when activated with 0 points | 400 with "insufficient" |
| 5 | Does the `?r=` attribution lock at signup / first deposit / first bet / first wager? | Cookie-write: race-real | First-bet only: not a race |
| 6 | Does the welcome-bonus drop counter reset on churn (deposit-withdraw-deposit)? | Second welcome bonus fires | Single fire per player |
| 7 | Does the VIP trial wager counter accept non-Slots/Originals wagers? | 200 counts live-dealer wagers | 200 but only slots/originals |
| 8 | Are the per-bet `houseEdge` and `ignoredBonuses` flags in `/api/search-games` honored by `games.slots.initGame`? | Non-bonus games accepted bets that count toward commission | Respected |

Each row is ~5 minutes to test once you have an account. The cost of running the full table is $5 of test capital and ~1 hour of socket interaction.

---

## 16. The `gamelist.getMainHistory` Unauth Leak (Critical — no account needed)

**Symptom:** The single socket event that powers the homepage "Live Wins" leaderboard — `gamelist.getMainHistory` — is reachable from a bare socket.io client with no auth, no cookie, no token. The response returns `data = { all: [...50], high: [...50], rare: [...50], wins: [...50], highWins: [...50] }` to *any* TCP client that can reach `wss://rolly.io/socket.io/`.

**Detection recipe (one-liner, no account needed):**
```python
import socketio
sio = socketio.Client(reconnection=False)
sio.connect('https://rolly.io', transports=['websocket'])
print(sio.call('gamelist.getMainHistory', {}))
```

**What it leaks per bet:**
- `user._id` (Mongo id), `user.name` (login), `user.userName`, `user.avatar`
- `user.isVip`, `user.isSystemAccount`, `user.canAccrueBonuses`, `user.canMinePoints`, `user.type` (only in `high` / `rare` / `highWins` lists — these are account-level flags that should not be in a public bet projection)
- `user.isHidden` (privacy preference of the bettor, leaked as a flag even when set)
- `amount` (real money), `currency`, `multi` (multiplier), `winAmount` (real money won)
- `txHash` (on-chain tx; links each bet to a merkle inclusion proof on explorer.rolly.io)
- `gameId`, `game`, `category`, `frontName`, `timestamp`, internal bet `_id`

**Why it's Critical on a "no-KYC, privacy-first" ZK casino:** the `txHash` is the join key between off-chain bet identity and on-chain wallet activity. Combined with the leaked `isVip` / `canAccrueBonuses` flags, an attacker can:
- Deanonymize every player (including VIPs and system accounts)
- Build a whales list for targeted phishing / social engineering
- Correlate on-chain addresses to betting patterns
- Track "isHidden=true" users' bets anyway (the flag is leaked even when set)

**Auth gating is inconsistent across events** (probe the whole event surface — see §17):
- `profile.getIntercomJwt`, `betsHistory.getCrossHistory` → `{ code: 13022, error: 'Unauthorized.' }` ✓
- `gamelist.getMainHistory`, `profile.subscribeMainHistory` → `200 OK` with full data ✗
- `gamelist.getHistory`, `gamelist.getWins` → `13003 Method not registered` (no auth gate, just unimplemented)

**Fix:**
1. Wrap every socket handler in a single server-side middleware (`io.use((socket, next) => …)`) that requires a valid session token (cookie `rolly_session` or the `rolly:access:v1` token from localStorage) before *any* handler runs. Today each handler checks auth independently — exactly the pattern that ships exposed events.
2. Project the `user` sub-object down to `{ _id, name, avatar }` for unauth callers; strip `isVip / canAccrueBonuses / canMinePoints / isSystemAccount / type / userName / isHidden` from the public bet feed entirely. Move VIP status to a per-user `users.getPublicProfile` handler that is rate-limited.
3. Strip `txHash` from any pre-commitment bet response (the hash shouldn't be in a public broadcast — it's a merkle-binding key).

---

## 17. The "Per-Handler Auth" Default-Allow Trap (High — any future event is exposed by default)

**Symptom:** Socket.io auth is implemented as a `if (!socket.userId) return error` check inside each handler, not as a single `io.use()` middleware. Some events have the check, some don't. A new event added by any developer is exposed to the internet until someone remembers to add the check.

**Probing the surface (no auth needed):**
```python
import socketio
sio = socketio.Client(reconnection=False)
sio.connect('https://rolly.io', transports=['websocket'])

events = [
    'profile.getIntercomJwt', 'betsHistory.getCrossHistory', 'gamelist.getMainHistory',
    'profile.subscribeMainHistory', 'gamelist.getHistory', 'gamelist.getWins',
    'users.search', 'users.find', 'users.getProfile', 'users.getByName',
    'auth.getNonce', 'auth.login', 'mining.getPool', 'withdraw.getQuote',
    'cashout.getQuote', 'balance.get', 'users.balance',
]
for e in events:
    r = sio.call(e, {}, timeout=2)
    auth_gated = isinstance(r, dict) and r.get('code') == 13022
    public_ok  = isinstance(r, dict) and 'data' in r
    not_impl   = isinstance(r, dict) and r.get('code') == 13003
    print(f"{e:35s} auth={auth_gated}  public={public_ok}  unimplemented={not_impl}  raw={str(r)[:80]}")
```

**Why this matters:** Adding a new event like `funkit.deposit` or `profile.getBalance` to the gateway ships it exposed to the internet by default. The auth check has to be remembered per-handler. **Switch to default-deny** with an explicit allowlist of genuinely public events.

**Fix:**
- `io.use((socket, next) => { verifySession(socket.handshake.auth?.token ?? socket.handshake.headers.cookie); next() })` before any `socket.on(...)` call.
- CI lint: fail the build if a new `socket.on('foo', …)` handler in the gateway is not wrapped in `requireAuth(...)`.
- Test: in a pre-prod env, connect with no auth, then with a stale auth, and assert every handler returns `13022` for the former and behaves correctly for the latter.

---

## 18. PII Over-Fetching in Public Bet Projections (High — same call as §16)

**Symptom:** Even *after* Finding 16 is fixed (auth gate added), the same event currently over-fetches the `user` sub-object. The `high` / `rare` / `highWins` lists return:

```json
{
  "_id": "6a48d3798b07bbc119456619",
  "name": "Viper",
  "isVip": true,
  "canAccrueBonuses": true,
  "canMinePoints": true,
  "isSystemAccount": false,
  "type": "default",
  "userName": "Viper"
}
```

The `isVip` and `canMinePoints` flags are account-level, not bet-level. They identify whales for targeted phishing.

**Detection recipe (no account):**
```python
sio = socketio.Client(reconnection=False); sio.connect('https://rolly.io', transports=['websocket'])
for bet in sio.call('gamelist.getMainHistory', {})['data']['high']:
    print(bet['user'])   # exposes isVip, canAccrueBonuses, isSystemAccount, type
```

**Diff in user fields per list (observed):**
| List | Fields in `user` |
|---|---|
| `all` | `_id, avatar, isHidden, name` |
| `wins` | `_id, avatar, isHidden, name` |
| `high` | `_id, avatar, isHidden, name, userName, type, isVip, isSystemAccount, canAccrueBonuses, canMinePoints` |
| `rare` | same as `high` |
| `highWins` | same as `high` |

**Fix:** in the server's projection layer, return only `{ _id, name, avatar }` for the public feed. Move `isVip` into a separate per-user rate-limited handler.

---

## 19. `txHash` in Pre-Commitment Public Feed (Medium — links off-chain bet to on-chain tx)

**Symptom:** Every bet in the public feed (the unauth one in §16) carries `txHash` — the on-chain transaction hash. This is the join key between (a) a user's off-chain bet identity on Rolly and (b) their on-chain wallet activity on Arbitrum.

**Why this matters on a ZK-casino:** Rolly markets itself as "no-KYC, privacy-first" with ZK-verified bets. But the public feed publishes the same data that an explorer (explorer.rolly.io) uses to bind a bet to a wallet. So even though the bet amount and outcome are committed via ZK proof, the linkage from "user X placed bet Y" to "user X controls wallet 0xABC" is publicly observable.

**Detection recipe:** any unauth call to `gamelist.getMainHistory` returns the `txHash` field. The hash is the same hash visible on `https://explorer.rolly.io/transaction/<hash>`.

**Fix:** strip `txHash` from the public projection. The hash is a merkle-inclusion *commitment* — it should only be released to the bettor themselves (via the `betsHistory.getMyHistory` authenticated path), not broadcast to every visitor.

---

## 20. Socket.io Server URL = Same-Origin (Deployment Note)

**Finding (informational):** the frontend's `createSocketConnection(p, "https://rolly.io")` (in `17_cdz248ieoz.js`) connects to the *same origin* as the Next.js app. CORS is correctly restricted to `Access-Control-Allow-Origin: https://rolly.io`, so cross-origin pages can't read responses.

**Implication for testing:** you can hit the socket from any IP that can reach `rolly.io`. No origin spoofing required. All §16/§17/§18/§19 work from the public internet.

**Implication for the dev team:** the socket and the Next.js app share a domain — they should also share a rate-limiter and a CDN (currently the socket handshake hits Cloudflare's 521 on the `api.rolly.io` subdomain, but the main origin serves it fine). Worth a load-test to ensure a flood of websocket connections can't take down the static asset path.
