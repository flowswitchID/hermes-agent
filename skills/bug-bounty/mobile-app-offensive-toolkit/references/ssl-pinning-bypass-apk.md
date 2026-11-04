# SSL-Pinning Bypass on Android APKs (patch for interception)

Goal: rebuild a target APK so proxy interception (Burp/mitmproxy) works — Java-layer
pinning dead, user CA trusted, WebView SSL errors auto-proceed. Procedure validated on
Cocos2dx/OkHttp apps and Facebook 585 (fbtls).

## TOOLCHAIN (install once)

```bash
# Java + apktool (repo moved: iBotPeach -> iBotPeaches, v3.x)
apt-get install -y default-jre-headless
curl -sL -o apktool.jar https://github.com/iBotPeaches/Apktool/releases/download/v3.0.3/apktool_3.0.3.jar

# smali assembler ONLY (assemble smali->dex; the 2.5.2 jar has no disassembler)
curl -sL -o smali.jar https://bitbucket.org/JesusFreke/smali/downloads/smali-2.5.2.jar

# signer (v1+v2+v3, zipalign, debug cert)
curl -sL -o uber-apk-signer.jar https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar
```

## 1. LOCATE THE PINNING (before touching anything)

Decode: `java -jar apktool.jar d -f target.apk -o dec`

Grep the dex strings (do not decode 20+ smali dirs to find this):

```bash
python3 - <<'EOF'
import zipfile
z = zipfile.ZipFile('target.apk')
for d in [n for n in z.namelist() if n.endswith('.dex')]:
    b = z.read(d)
    for p in [b'CertificatePinner', b'checkServerTrusted', b'onReceivedSslError',
              b'X509TrustManager', b'fbtls', b'sslpry', b'SSLPry', b'verifyCertificate']:
        if b.count(p): print(d, p.decode(), b.count(p))
EOF
```

Check the manifest and NSC: `grep -o 'networkSecurityConfig="[^"]*"' dec/AndroidManifest.xml`
— the xml file name is often obfuscated (`APKTOOL_RENAMED_0x7f170004.xml` in the decode
tree; find the REAL entry name in the apk zip by scanning `res/*.xml` for the bytes
`network-security-config`).

Check native libs for pinning engines: `libsslpry.so` / boringssl strings. If absent
(Facebook 585), pinning is pure Java — smali patching suffices, no Frida needed.

## 2. PATCH POINTS (smali)

Write a Python patcher (regex on `.method` blocks) that:

1. **Pinner check no-op** — e.g. OkHttp `CertificatePinner.check` / app-specific
   `check(...)` / Facebook `LX/00ND;->A03([Ljava/security/cert/X509Certificate;)V`
   -> body `return-void`. ALSO no-op any companion config/expiry method it feeds
   (`LX/00ND;->A02(Ljava/util/List;)V`).
2. **Trust-all X509TrustManager** — replace the factory method body with
   `new-instance` of a trust-all impl (or point the factory at an existing
   trust-all class), or make each `checkServerTrusted` impl `return-void`.
3. **HostnameVerifier** — every `verify(...)Z` -> `const/4 v0, 0x1`.
4. **WebView** — every `onReceivedSslError` method body ->
   `invoke-virtual {p2}, Landroid/webkit/SslErrorHandler;->proceed()V` + `return-void`.
5. **NSC** — strip `<pin-set>` contents (keep the element empty), add
   `<certificates src="user"/>` to base-config trust-anchors,
   `cleartextTrafficPermitted="true"`. Keep debug-overrides `overridePins="true"`.

Find the enforcement funnels first: patch where all callers converge (e.g. FB
`CertificateVerifier` and `X/00ME` both call `00ND.A03` — one patch covers both).
Leave delegating wrappers alone; they then run the platform chain check, which now
passes because the user CA is trusted.

## 3. REBUILD — DECIDE BY APP OWNER

**Default: `java -Xmx3g -jar apktool.jar b dec -o patched.apk`** works for most apps.

**If aapt2 fails on `$` in resource file paths** (Meta/Facebook builds ship
`res/invalid1A/$$animated_splash_screen__1__0.xml` etc.):

- **Do NOT fight aapt2. Do zip surgery instead:**
  1. Assemble dexes directly: `java -jar smali.jar a dec/smali_classesN -o classesN.dex`
     for every dir (`smali/` -> `classes.dex`, `smali_classesN/` -> `classesN.dex`).
     Takes ~40s/dex on a 4GB VPS; run as a background job.
  2. Compile the patched NSC alone in a mini apktool project
     (`apktool.yml` + bare `AndroidManifest.xml` + `res/xml/nsc.xml`) -> extract the
     compiled binary AXML.
  3. Rewrite the ORIGINAL apk zip: replace `classes*.dex` (STORED) and the NSC entry
     only; copy every other entry byte-identical. `resources.arsc`, obfuscated res
     dirs, libs, assets all survive untouched, so resource IDs cannot shift.

**Other aapt2 resource errors on full rebuild:** `failed to read PNG signature` =
WebP bytes with a .png name (Meta ships many). Scan magic bytes across `dec/res/`
and rename by real format (`RIFF....WEBP` -> .webp, `\xff\xd8` -> .jpg). Only needed
on the full-rebuild path; zip surgery never touches them.

## 4. SIGN (and repack XAPK)

```bash
java -jar uber-apk-signer.jar -a patched.apk -o signed
```

XAPK installs (SAI / Split Installer) need base + every split signed with the SAME
key. Store splits (APKPure `config.*.apk`) arrive pre-signed with the vendor key and
uber-apk-signer skips them: strip `META-INF/*.RSA|*.SF|*.MF` from the split first,
then sign it with the same debug key. Verify with
`keytool -printcert -jarfile <apk> | grep SHA256` on both — fingerprints must match.
Repack: `base + splits + manifest.json + icon.png` into the .xapk.

**Write every XAPK-level entry as ZIP_STORED.** SAI opens the base APK through a
NESTED ZipInputStream and inflates XAPK entries as it copies them; a deflated
entry whose stream is even slightly off produces `invalid entry size (expected X
but got Y)` or `invalid stored block lengths` at install time. STORED entries
remove the inflate failure class entirely (cost: a bigger .xapk, e.g. 125MB->229MB
for FB 585 — irrelevant for delivery). After repack, verify the zip structurally:
central-directory csize/usize must equal the local-header values for every entry,
and `zipfile.testzip()` must pass — a mismatch means a streaming write left a
data-descriptor entry and the artifact is not SAI-safe.

## 5. VERIFY THE FINAL ARTIFACT (never skip)

smali 2.5.2 is assemble-only — you cannot disassemble the new dex to check it.
Instead **decode the final signed APK with apktool and re-read the patched smali**:
`A03` shows `return-void`, the NSC decodes without `pin-set` and with user trust,
WebView handlers show `proceed()`. Also `zipfile.testzip()` the XAPK.

The NSC entry itself SURVIVES a patched build (obfuscated name, e.g. `res/36u.xml`)
— "stripped" means the pin-set inside was replaced, not that the file was deleted.
Confirm the patch by the entry's decoded strings (`network-security-config`,
`base-config`, `trust-anchors`, `certificates`, `system`, `user`,
`cleartextTrafficPermitted`), never by entry presence/absence. Record the built
artifact's md5 — it is the value the operator verifies on device after download.

## 6. ACQUIRING LATEST APKs

Mirrors (apkmirror/apkpure/apkfab/uptodown) sit behind Cloudflare/reCAPTCHA from a
datacenter IP. Working route: **apkeep** (EFF) — prebuilt Linux binaries from GitHub
releases; recent builds need GLIBC 2.38, so on older hosts pick an older release tag.

```bash
./apkeep -a com.facebook.katana -d apk-pure outdir/   # -> com.facebook.katana.xapk
```

If blocked, have the operator upload the APK to the VPS (`/root/`) and work from that.

## DELIVERY

- Artifacts land in `/root/` (operator convention).
- Telegram gateway caps outgoing documents at 20MB. For a phone-side install of a
  90-230MB artifact, split and send parts — gofile.io's >100MB downloads arrive
  corrupt on device, so prefer this route:
  ```bash
  split -b 19M -d -a 1 file.xapk part
  cat part* | md5sum   # must equal md5sum file.xapk — verify BEFORE sending
  ```
  Send each part via MEDIA:, then give the join + verify commands:
  `cat part0 part1 ... part6 > fb.xapk` then `md5sum fb.xapk` (must match).
- VPS path + pull command remains the fallback when parts delivery is impractical.
- Ship a Frida companion script alongside the patched APK (blanket
  TrustManagerImpl.verifyChain, X509TrustManager impls, HostnameVerifier,
  okhttp CertificatePinner.check, WebView proceed) as runtime belt-and-braces.

## DEVICE INSTALL TROUBLESHOOT (SAI / Split Installer)

`java.util.zip.ZipException: invalid code lengths set`, `invalid entry size
(expected X but got Y)`, or `invalid stored block lengths` from `ZipApkSource` /
`RootlessSaiPackageInstaller.install` = the COPY ON THE DEVICE is corrupt
(truncated or CDN-mangled download), not a bad artifact. Triage in this order:

1. Verify the source on the VPS: `zipfile.testzip()` every APK and the XAPK, then
   `md5sum` the XAPK against its parts (`cat part* | md5sum`). Both pass -> the
   artifact is good; re-deliver.
2. On device, verify BEFORE install: `md5sum fb.xapk` must equal the VPS hash.
   A matching file size does not prove content integrity.
3. Uninstall the original app first — patched builds are debug-signed, and the
   vendor release key on the installed app rejects the overwrite. (Skip for a
   coexist build whose permissions were renamed — see
   `axml-manifest-and-v1-signing.md` §3.)
4. Re-deliver via Telegram split parts (DELIVERY above), not the same gofile link.
5. If the VPS artifact passes every check AND the device md5 matches but SAI
   still throws size/inflate errors: SAI caches the parsed apksource by
   filename — deliver under a NEW filename to force a re-parse.
6. If the operator insists on a download link, follow `large-file-delivery.md`.

## BUILD ENVIRONMENT (4GB VPS)

- Check `free -m` before dex assembly or any >100MB zip write. A headless
  Android VM under QEMU holds ~2GB by itself — stop it before a big build.
- Stop background processes BY PID (`ps aux` -> `kill <pid>`). Never
  `pkill -f <name>` when that name also appears in your own command — the
  pattern matches the agent's own shell and SIGTERMs the terminal mid-task.
- In-memory python `zipfile` writes of >100MB get interrupted on a RAM-starved
  box; handle large artifacts with streaming CLI (`split`, `cat`) and verify
  with md5.

## FACEBOOK 585 QUICK REFERENCE (re-map for other versions)

- Enforcement: `LX/00ND;->A03` (pin match) + `A02` (pin-config expiry); callers
  `LX/00ME` (X509ExtendedTrustManager wrapper) and
  `com/facebook/mobilenetwork/internal/certificateverifier/CertificateVerifier`.
- NSC real path: `res/36u.xml` (obfuscated; 18-pin set, expiration ~2027).
- WebView handlers: 10 classes in `smali_classes20` (`X/0tM*`, `X/0tN*`).
- Native libs arm64-only, no libsslpry — pure Java pinning.
- WebP-as-.png + `$`-named res files force the zip-surgery path.

