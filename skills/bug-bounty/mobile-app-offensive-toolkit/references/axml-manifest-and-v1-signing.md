# Binary AXML manifest surgery + pure-Python v1 re-signing

Use when the only change is in `AndroidManifest.xml` (permission rename, component
flags, coexist fixes) and/or the toolchain lacks apktool/aapt2/apksigner. Validated
on Facebook 585 katana (permission-collision coexist with com.facebook.lite).

## 1. Decide: binary AXML patch vs full rebuild

If the change lives entirely in the manifest, patch the **binary AXML in place**:
extract `AndroidManifest.xml` from the APK, rewrite the string pool, reassemble.
No apktool decode/rebuild — resource IDs cannot shift, resources.arsc and splits
are untouched. A **string-pool rename covers every reference** (uses-permission,
android:permission attrs) because they share pool entries — no per-reference walk.

## 2. AXML binary format rules that bite

- File = 8-byte header (type 0x0003, headerSize 8, fileSize) + string pool chunk
  (0x0001) + optional resource-ids chunk (0x0180) + XML chunks.
- String pool chunk: 8-byte chunk header + 20-byte pool header (stringCount,
  styleCount, flags, stringsStart, stylesStart). `stringsStart` is relative to
  CHUNK start (28 + 4*n typically). `stringsStart == 0` means UTF-16 pool
  (is_utf8=False) — decode entries as utf-16-le, null-terminated, even-padded.
- Element chunk (0x0102): headerSize=16 covers type/hsize/size/lineNumber/comment.
  Then ns u32, name u32, attributeStart u16, attributeSize u16, attributeCount
  u16, idIndex/classIndex/styleIndex u16.
  **attributeStart is relative to the end of the 16-byte node header → absolute
  offset = headerSize + attributeStart (typically 36, NOT 20).** Hardcoding 20 or
  `8+20` silently reads the header as attribute data and yields 0 matches.
- Each attribute: ns u32, name u32, rawValue u32, then typedValue
  (size u16, res0 u8, dataType u8, data u32). dataType 0x03 = STRING (data =
  pool index), 0x12 = INT_DEC.
- Rebuilding the pool: keep the same flags, offsets relative to data start,
  UTF-16 entries null-terminated and even-length padded. New chunk
  **size = 8 + payload length** — the payload already includes the 20-byte pool
  header; writing 28+payload overruns by 20 and corrupts every following chunk.
- Tail (resource-ids + all XML chunks) copies verbatim — all references are
  pool-relative; there are no absolute file offsets to fix.
- Verify by re-parsing the FINAL artifact: element count must equal the original
  and the old strings must be absent from the pool.

## 3. INSTALL_FAILED_DUPLICATE_PERMISSION — coexist without uninstalling

PackageManager rejects a package that *declares* a permission name already owned
by another installed package. Fix by renaming the declarations (pool rename does
the references too) to a namespace the other package does not own.

- Meta collision set with com.facebook.lite:
  `com.facebook.receiver.permission.ACCESS` and
  `com.facebook.permission.prod.FB_APP_COMMUNICATION`.
- Rename map (katana side):
  `com.facebook.receiver.permission.ACCESS` → `com.facebook.katana.receiver.permission.ACCESS`
  `com.facebook.permission.prod.FB_APP_COMMUNICATION` → `com.facebook.katana.permission.prod.FB_APP_COMMUNICATION`
- Leave already-namespaced declarations alone (`com.facebook.katana.*`).
- `<uses-permission>` of a permission OWNED by the other package is legal — only
  declarations collide, so usages need no change.

## 4. v1 JAR signing from scratch (no apksigner / jarsigner / uber-apk-signer)

Build the chain in this order; Android verifies exactly this:

1. **MANIFEST.MF** — main attrs, then per-entry section:
   `Name: <path>` + `SHA-256-Digest: <b64(sha256(file content))>`.
   **The Name line is part of the digested section bytes** — a parser that drops
   it emits sections that fail SF verification for every entry.
2. **.SF** — `Signature-Version: 1.0` + per-entry `Name:` +
   `SHA-256-Digest: <b64(sha256(the manifest SECTION bytes))>`.
   The SF digests manifest sections, NOT file content.
3. **.RSA** — PKCS#7 SignedData:
   - ContentInfo = SEQUENCE { OID 1.2.840.113549.1.7.2, **[0] EXPLICIT** SignedData }
     — the [0] wrapper is mandatory; omitting it makes the block unparseable.
   - SignedData = SEQUENCE { version, digestAlgorithms SET{sha256},
     encapContentInfo (OID data, empty content), certificates [0] {cert},
     signerInfos SET }.
   - SignerInfo = { version, sid, digestAlgorithm,
     digestEncryptionAlgorithm rsa-sha256, signature } — **NO signedAttrs.**
     Android's PKCS#7 parser rejects the signed-attrs form with
     `INSTALL_PARSE_FAILED_NO_CERTIFICATES ... toDerInputStream rejects tag
     type -96: Sequence tag error`; the legacy sign-over-SF form is accepted.
   - The signature is computed **directly over the .SF bytes** (encapContentInfo
     content stays empty) — not over a DER SET of attrs, not over inner content.
   - AlgorithmIdentifier SEQUENCEs (sha256, rsa-sha256) carry **NULL
     parameters**; omitting them is a second rejection trigger.
4. **Repack streaming** — replace AndroidManifest.xml + META-INF/MANIFEST.MF +
   META-INF/ANDROIDD.SF + META-INF/ANDROIDD.RSA, drop any other
   `*.SF|*.RSA|*.DSA`, copy every other entry byte-identical (keep original
   compress_type and date_time per ZipInfo).
5. **Verify the final artifact** — full chain: SF digest == sha256(manifest
   section) per entry; manifest digest == sha256(file content) per entry;
   messageDigest attr == sha256(SF); RSA signature verifies against the embedded
   cert. A matching entry count on the manifest rebuild (e.g. thousands) is the
   first signal the section parser kept the Name lines.

## 5. Minimal-DER mistakes (each broke a build before it worked)

- Compare the OID **payload** hex, not the full TLV — a DER walker returns
  content only: signedData is `2a864886f70d010702`, messageDigest is
  `2a864886f70d010904` (no `0609` prefix).
- `x509.load_der_x509_certificate` needs the FULL TLV — pass the byte slice up
  to the element end, not the walker's payload.
- Know which digest belongs to which level: MF digest = file CONTENT,
  SF digest = manifest SECTION, messageDigest attr = SF bytes. A verifier that
  digests the wrong operand reports false mismatches on a correct artifact.
- Python zipfile writes of large APKs on a RAM-starved box: stream with
  `shutil.copyfileobj` per entry (or CLI `split`/`cat`), never one giant
  in-memory build.
