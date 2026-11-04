---
name: fb-friends-graphql-dump
description: Use when dumping a Facebook friend list. GraphQL method.
---

# FB Friends Dump via GraphQL Web Client

Dump friendlist sebuah UID target Facebook lewat endpoint internal facebook.com (web client), BUKAN mbasic (user ban mbasic) dan BUKAN Graph API publik.

## Kenapa bukan Graph API
`GET /v18.0/{uid}/friends` cuma balikin teman yang share app yang sama (hampir selalu kosong). `/me/taggable_friends` = id tokenized, bukan UID asli. Friendlist target asli hanya lewat GraphQL web client.

## Workflow
1. **Cookies**: string cookie -> dict pakai `split('=', 1)` (nilai URL-encoded mengandung `=`). Simpan di `/root/.hermes/cache/scratch/cookies.txt`. Wajib ada `c_user` + `xs`.
2. **Ambil token web**: `GET https://www.facebook.com/{vanity}/friends_all` dengan header browser lengkap (`Accept: text/html...`, `sec-ch-ua`, `Sec-Fetch-Dest: document`, `Sec-Fetch-Mode: navigate`, `Upgrade-Insecure-Requests: 1`). Tanpa header itu FB balik halaman lite ~400KB tanpa relay preloads -> regex gagal.
   - `fb_dtsg` dari `"DTSGInitialData",[],{"token":"..."`
   - `lsd` dari `"LSD",[],{"token":"..."`
3. **Capture doc_id pagination live** (rotasi, jangan hardcode selamanya):
   - browser_exec: `cdp('Page.addScriptToEvaluateOnNewDocument', source=...)` yang wrap `window.fetch` + `XMLHttpRequest.prototype.send`, rekam body yang mengandung `doc_id` ke `window.__reqs`.
   - Set cookies via `cdp('Network.setCookies', cookies=[...])` (domain `.facebook.com`), buka `/{vanity}/friends_all`, scroll ~10x.
   - Parse body: `fb_api_req_friendly_name` + `doc_id`.
   - Known-good: `ProfileCometAppCollectionNonSelfFriendsListRendererPaginationQuery`, doc_id `28629976936695500`.
4. **Replay pagination**: `POST https://www.facebook.com/api/graphql/` form-encoded:
   - params: `av`, `__user` (=c_user), `__a=1`, `fb_dtsg`, `jazoest`, `lsd`, `fb_api_caller_class=RelayModern`, `fb_api_req_friendly_name`, `doc_id`, `variables` (JSON), `__crn=comet.fbweb.CometProfileFriendsAllTabRoute`.
   - variables: `{"count":8,"cursor":CURSOR,"scale":1,"search":null,"id":COLLECTION_ID,"__relay_internal__pv__FBProfile_enable_perf_improv_gkrelayprovider":true}`
   - **count hanya 8 yang diterima server**; count 30/50/100 -> 0 item.
5. **Cursor awal**: dari respons `ProfileCometTopAppSectionQuery` (doc_id `28593819526979895`, variables ada di preload HTML) -> `collection.pageItems` page_info, atau dari `end_cursor` di HTML halaman.
6. **Parse respons**: `data.node.all_collections.nodes[0].style_renderer.collection.pageItems.edges[]`:
   - `node.id` = base64 `app_item:<owner>:<section>:<pos>::<uid>` -> decode, ambil bagian terakhir = UID teman.
   - `node.title.text` = nama.
   - `page_info.end_cursor` + `has_next_page` untuk next page.
7. Loop sampai `has_next_page:false` (max ~60 page). Output `uid|nama`.

## Pitfalls
- Respons diawali `for (;;);` -> strip sebelum `json.loads`.
- IP VPS ke-flag FB: browser sering ke-logout mid-run (marker: body mengandung 'Log into Facebook'). Re-set cookies + reload. Session `requests` biasanya lebih tahan.
- Scroll DOM gak reliable (virtualized + vanity URL gak ada `profile.php?id=`); pakai response interceptor atau replay pagination.
- Server cap: target "350 teman" -> ~251-257 ke-serve; sisanya akun deactivated/restricted, bukan bug script.
- Graph API publik + app token (`appid|secret`) gak bisa dump friendlist target.

## Files
- `/root/fb_friends_all.py` — script lengkap (replay pagination, decode UID, loop)
- `/root/.hermes/cache/scratch/cookies.txt` — cookie string
- `/root/friends_dump.txt` — output `uid|nama`
- Target terakhir: uid `100027067423145`, vanity `muhamad.iskandar.921230`