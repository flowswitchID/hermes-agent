---
name: panel-url-patterns
description: Generate Firebase RTDB panel URLs from naming patterns.
---

# Panel URL Generation Patterns

## When to Use
Live sources (GitHub code search, Telegram channel scrape via r.jina.ai) return empty. Generate candidate Firebase RTDB panel URLs from known naming conventions.

## Standard Format
```
https://{prefix}-{n}-default-rtdb.firebaseio.com
```

## Asia-Southeast1 Format
```
https://{prefix}-{n}-default-rtdb.asia-southeast1.firebasedatabase.app
```

## Prefix Sets
India/general: pm-kisan, pmkisan, pm, kisan, rto, challan, panel-wala, panel, admin-panel, hospital, bank, carder, india, indian, desi, jio, jiopanel, reliance, nexus, infiniti, idn
Admin variants: sk-admin, ck-admin, my-admin
Common Indian first names: rahul, raj, amit, vikash, ashish, rohit, sanjay, pintu, bihari, kundan, sunil, manoj, gaurav, deepak, nitin, sachin
City names: mumbai, delhi, bangalore, chennai, kolkata, hyderabad, pune, ahmedabad, jaipur, lucknow, kanpur

## Number Ranges
- firebaseio.com: 1–300 per prefix
- asia-southeast1.firebasedatabase.app: 1–100 per prefix, max 2 per prefix to control volume

## Deduplication
Compare generated URLs against existing FIREBASE_PANELS list before appending. Use exact string match on the URL.

## Pitfalls
- Do not exceed reasonable total panel count (keep under 2k new panels per generation to avoid scan time explosion).
- Empty API keys in generated entries are fine; scanner treats empty string as no restriction.
- Some prefixes produce zero live instances; volume is expected.