# Headless Android VM (QEMU+KVM) for Interception Work

Run Android-x86 on a headless Linux VPS with KVM, drive it without adb, and stand up a
traffic-intercept pipeline. Use when the operator needs a live Android environment
(Frida spawn, proxy intercept, cert install) but has no physical device and no binder
module for Waydroid.

## When to Use

- VPS has `/dev/kvm` but no `/dev/binderfs` (Waydroid impossible) -> QEMU+KVM.
- Need to intercept an app's HTTPS traffic with mitmproxy + Frida SSL-pinning bypass
  from a server with no display.

## Procedure

### 1. Check host capability

```bash
ls /dev/kvm            # must exist
ls /dev/binderfs       # if missing, Waydroid is out; use QEMU
nproc; free -m; df -h  # Android-x86 9 needs ~2 GB RAM, 2 vCPU
```

### 2. Get the Android-x86 ISO

Release 9.0 (Pie) x86_64 from SourceForge mirrors. Verify size after download
(965,738,496 bytes for `android-x86_64-9.0-r2.iso`).

### 3. Extract kernel/initrd and boot direct (skip GRUB and the setup wizard)

Loop-mount the ISO read-only and copy out `/kernel` + `/initrd.img`. The boot
cmdline lives in `boot/grub/grub.cfg` -> `efi/boot/android.cfg` (GRUB) or
`isolinux/isolinux.cfg` (syslinux); read them to get the exact params.

Boot without GRUB interaction:

```bash
qemu-system-x86_64 -enable-kvm -m 2048 -smp 2 -cpu host \
  -kernel iso/kernel -initrd iso/initrd.img \
  -append "root=/dev/ram0 quiet SETUPWIZARD=0 SRC= DATA=" \
  -drive file=android-x86_64-9.0-r2.iso,format=raw,if=virtio,media=cdrom,readonly=on \
  -netdev user,id=net0,hostfwd=tcp::5555-:5555,hostfwd=tcp::27042-:27042 \
  -device virtio-net-pci,netdev=net0 \
  -vnc :0 -monitor unix:$VMDIR/mon.sock,server,nowait \
  -daemonize -pidfile $VMDIR/qemu.pid
```

`SETUPWIZARD=0` skips the entire first-boot wizard — do this before trying to
click through Wi-Fi/Google-account/screen-lock screens by hand. Only the
"Select a Home app" dialog remains; pick Taskbar (or Quickstep).

### 4. Drive the GUI via VNC while adb is offline

Write a minimal pure-stdlib RFB client (socket + struct, no deps) supporting:

- `shot out.ppm` — FramebufferUpdateRequest, raw encoding only, request encodings
  `[0, -223, -224]` (raw + DesktopSize + LastRect), skip pseudo-encodings (`enc < 0`).
- `click X Y` — PointerEvent down/up.
- `type <string>` — KeyEvent per char: uppercase and symbols need Shift_L (0xFFE1)
  held; printable ASCII keysyms equal their codepoints.
- `key <name>` — named keys: ret=0xFF0D, tab=0xFF09, esc=0xFF1B, arrows 0xFF51-54,
  space=0x20.

Alternative screenshot path when VNC is awkward:
`echo "screendump /path/s.ppm" | socat - UNIX-CONNECT:$VMDIR/mon.sock` then
`convert s.ppm s.png` (imagemagick).

### 5. Enable adb TCP from inside the guest

Android-x86 does NOT listen on 5555 by default. Open the Terminal Emulator
(app drawer -> search "terminal") and run:

```sh
setprop service.adb.tcp.port 5555
netstat -tln        # confirm 0.0.0.0:5555 LISTEN
```

Then from the host: `adb connect 127.0.0.1:5555`.

### 6. Intercept pipeline (once adb is online)

- Push frida-server (`frida-server-<ver>-android-x86_64.xz`) to `/data/local/tmp`,
  chmod 755, run with `-l 0.0.0.0` (hostfwd 27042 already maps it).
- Run `mitmdump --mode regular --listen-port 8080 --set ssl_insecure=true -w capture.mitm`.
- Point the guest proxy at the host: the guest sees the host as `10.0.2.2` under
  QEMU user networking -> `adb shell settings put global http_proxy 10.0.2.2:8080`.
- Spawn the target under Frida with the SSL-pinning bypass script
  (`frida -H 127.0.0.1:27042 -f <pkg> -l bypass.js --no-pause`).
- mitmproxy CA cert must be a SYSTEM cert on API >= 24 (push to
  `/system/etc/security/cacerts/<hash>.0`, needs root) or use Frida gadget mode.

## Pitfalls

1. **Terminal Emulator on Android-x86 runs as `untrusted_app`, not root.** `id` shows
   `uid=10xxx(u0_aXX)` with SELinux `untrusted_app`; `stop adbd` / `start adbd` fail with
   "must be root" and `/data/misc/adb/adb_keys` is not writable. Plan for a root path
   (debug boot entry, or patched initrd) before assuming shell-level control of adbd.
2. **adbd LISTEN on 0.0.0.0:5555 does not mean adb works.** A listener plus host
   `offline` means the RSA handshake failed — the host's adb public key is not in the
   guest's `adb_keys`. Diagnose with that pair of facts before re-installing anything.
3. **Vision model coordinates for small buttons are unreliable.** When a click misses,
   analyze the PPM pixels directly: scan the screenshot for the button text color
   (e.g. teal: `g>100 and b>80 and r<120 and g>r+40`), cluster x-columns, and use the
   cluster centers as click targets. This beat every vision estimate in-session.
4. **Android system dialogs are keyboard-navigable.** When mouse clicks miss a dialog
   (permission prompts, launcher chooser), use arrows + `ret` + `tab` — the VNC client
   sends real key events and focus follows the dialog's default order.
5. **Parse the RFB ServerInit as 24 bytes, not 20.** framebuffer w/h (4) + pixel format
   (16) + name length (4); reading 20 desyncs the stream and every later rect is garbage.
6. **Do not send TAB TAB RET blindly through the setup wizard.** It can land on a
   screen that blanks the display; navigate by screenshot -> targeted click instead.
7. **Guest-to-host networking is one-way under QEMU user mode.** The guest reaches the
   host at `10.0.2.2`; the host reaches the guest only through `hostfwd` ports. Set the
   emulator proxy to `10.0.2.2:<mitm_port>`, never to the host's LAN IP.
8. **Frida anti-detect:** rename `frida-server` on the device (e.g. to `svc`) because
   Meta apps scan the process list; gadget mode (`objection patchapk`) is the no-root
   alternative when the binary refuses the spawn hook.
