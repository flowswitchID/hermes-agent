---
name: apk-xapk-rebuild-signing
version: 1.0.0
description: Use when re-signing or repacking modded APKs/XAPKs.
---

# APK/XAPK Rebuild & Signing

## When to Use
- Rebuilding/repacking a patched or modded APK (dual-install, patched manifest, injected libs)
- Fixing INSTALL_PARSE_FAILED_NO_CERTIFICATES / "invalid stored block lengths" / corrupt XAPK delivery
- Making an app's HTTPS traffic interceptable (SSL-pinning bypass via network security config — see references/ssl-pinning-nsa-bypass.md)
- Packaging or delivering an XAPK to a phone (split parts, md5 verification)

## Signing
- Sign with apksigner (AOSP reference), never hand-rolled v1 JAR signing. Hand-rolled v1 fails with INSTALL_PARSE_FAILED_NO_CERTIFICATES because libcore's Manifest.read() rejects MANIFEST.MF lines >72 bytes — any MF/SF edit must preserve the original 72-byte continuation wrapping byte-for-byte (surgical digest-value replacement only).
- Modded APKs are often v3-only (v1 intentionally broken by the modder) — fine when minSdk>=30, since the platform only requires v2/v3. apksigner with --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true regenerates all schemes.
- Pipeline: zipalign -f -p 4 -> apksigner sign -> apksigner verify. Verify with --min-sdk-version 30 --max-sdk-version 30 for an accurate scheme report (default assume-v1-only gives misleading v1=false).

## Patching a single compiled resource (no full rebuild)
- When the change is ONE compiled resource (e.g. the network security config), swap that zip entry in place — preserve every entry's original compress_type, drop stale META-INF/*.SF/.RSA/MANIFEST.MF, zipalign, re-sign. A full apktool rebuild is the wrong tool for a one-entry change.
- Find a compiled XML entry by scanning zip entry bytes for the UTF-8 form of a distinctive element name (modern AXML string pools are UTF-8, not UTF-16).
- Compile the replacement AXML with apktool's bundled aapt2: extract `prebuilt/linux/aapt2_64` and `prebuilt/android-framework.jar` from apktool.jar, then `aapt2_64 compile --dir <proj>/res -o c.zip` and `aapt2_64 link -o mini.apk --manifest <proj>/AndroidManifest.xml -I android-framework.jar --min-sdk-version <app minSdk> c.zip`. Compiled AXML is self-contained (own string pool; android: attr IDs are standard) — the obfuscated res path it lands at does not matter.
- Verify the swap landed by apktool-decoding the SIGNED final APK (`d -s`, sources off) and reading the decoded xml — never trust the swap without decoding the artifact you will ship.

## Modern-app APK pitfalls (2025+ builds, e.g. Meta apps)
- Old aapt2 (build-tools 30.0.3) cannot parse modern resources.arsc ("illegal map type 'unknown' (25)") — dump/compile/link with apktool's bundled aapt2 instead; the apktool auto-installed framework 1.apk is unreadable by old aapt2 as well.
- apktool full rebuild of these APKs dies twice over: WebP bytes under .png names (aapt2 compile fails the PNG signature check — rename to .webp, resource name unchanged) and `$` in res filenames ("invalid file path", Meta internal build naming). Treat both as a dead end for full rebuild; use the surgical entry swap when the change is resource-only.
- A Play-style base APK (few early-load libs, native libs in split_config.<abi>) cannot run standalone — patch a complete build (base with all native libs) instead of the Play base the user may have downloaded.
- Matching the previous build's scheme profile is enough: a v3-valid signature installs fine on Android 11+; do not burn time chasing v1/v2 verify output when the known-good build had the same profile.

## Packaging
- ZIP_STORED for every XAPK entry — streaming Deflater output triggers "invalid stored block lengths" ZipException on device.
- Ship the joined-file md5 plus per-part md5s; receiver joins with `cat` + `md5sum` and verifies before install.
- Telegram document delivery caps below ~19MB — split into <=15MB parts.

## Verification before delivery
- Cert proof: `adb install-multiple -r -d base.apk config.apk` on any AVD. INSTALL_PARSE_FAILED_NO_CERTIFICATES = signature bug (pre-verification); ABI mismatch after parse = verification already passed, signature is fine.
- Bundled QEMU2 emulator cannot boot arm64 system images on an x86 host (FATAL at launch); raw qemu-system-aarch64 with AOSP arm64 images stalls at userspace init (ramdisk partition-layout mismatch) — use an x86_64 AVD for parse/cert proof instead of burning time on ARM VM boot.
- VPS has no unzip/jarsigner (JRE-only Java) — extract with python zipfile, inspect PKCS#7 with python cryptography.
- requiredSplitTypes / com.android.vending.splits.required are Play-Store-only constraints; pm install accepts base-only APKs of split apps.