# SSL-Pinning Bypass via Network Security Config (surgical NSA patch)

Class-level recipe for making an app's HTTPS traffic interceptable (mitmproxy /
reqable / Burp) with no smali changes and no root — proven on Meta/Facebook builds.

## Mechanism
- Android resolves pinning from the app's `network-security-config`. Adding
  `<certificates overridePins="true" src="user" />` to `<base-config>`
  `<trust-anchors>` makes chains signed by a USER-installed CA override the
  `<pin-set>` entries. Cronet/Fizz (Chromium network stack) honors this, so it
  defeats FB's pinning without touching native code.
- `<debug-overrides>` only apply to `android:debuggable="true"` apps — useless on
  release builds. Do not rely on them.
- Removing the `<pin-set>` from `<domain-config>` is optional once overridePins is
  in base-config; keep or remove, both work for user-CA chains.

## Procedure (one-entry surgical swap)
1. Decode the app's NSA config once (apktool `d -s` on a working build) to get the
   text form; the resource id is stable across builds of the same app.
2. Write the patched NSA xml: base-config trust-anchors =
   `system` + `user overridePins="true"`; keep the app's own domain-configs.
3. Compile it: extract `prebuilt/linux/aapt2_64` + `prebuilt/android-framework.jar`
   from apktool.jar; mini project (`res/xml/<name>.xml` + minimal manifest with
   uses-sdk) -> `aapt2_64 compile --dir mini/res -o c.zip` ->
   `aapt2_64 link -o mini.apk --manifest mini/AndroidManifest.xml -I android-framework.jar --min-sdk-version <app minSdk> c.zip`.
4. Find the NSA entry in the target APK: scan zip entries for UTF-8
   `network-security-config` (compiled AXML string pool).
5. Swap: rewrite the zip preserving compress_type, replace that entry's bytes with
   the compiled AXML from mini.apk, drop stale META-INF sigs.
6. zipalign -f -p 4 -> apksigner sign (same key as the prior build) -> verify.
7. Decode the SIGNED APK again (`d -s`) and confirm `overridePins="true"` is in
   the decoded NSA xml before shipping.

## Choosing the patch target
- Patch a COMPLETE build. A Play-style base APK (only early-load libs like
  breakpad/superpack; native libs live in split_config.<abi>) crashes at startup —
  it is a version reference, not an installable target.
- A previously-shipped working build with the same version is the ideal target:
  identical signature profile, only the one entry changes.

## Operator-side steps (what the user does after install)
1. Install the proxy's CA certificate into the phone's USER store (Settings >
   Security > Encryption & credentials > Install a certificate > CA).
2. Point the phone's WiFi proxy at the interception host.
3. Open the app — pinned domains now appear in the proxy as plain CONNECT/HTTPS
   flows. No root required.

## Pitfalls
- apksigner v1/v2 verify can report false on huge modded bases while v3 verifies
  true; Android 11+ only needs v2/v3 — compare against the prior build's profile
  instead of chasing green on every scheme.
- Do NOT do a full apktool rebuild for this class of change: WebP-named-.png files
  and `$`-prefixed res filenames in modern Meta builds break aapt2 compile.
