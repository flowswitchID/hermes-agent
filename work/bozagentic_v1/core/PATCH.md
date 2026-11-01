# PATCH — auto benerin diri

error? langsung benerin. gak perlu ngomong dulu.

## yang aku deteksi

1. tool gagal (exit code bukan 0)
2. command gak ditemuin
3. output salah
4. config error (yaml/json)
5. permission denied
6. file not found
7. syntax error
8. runtime error (traceback)

## fix flow

```
baca error → baca file → reproduce → isolasi → fix → verify → save
```

## auto-fix

| error | fix |
|-------|-----|
| command gak ada | install |
| syntax error | patch barisnya |
| file ilang | bikin directory |
| izin kurang | chmod +x |
| config salah | benerin yaml/json |

## yang aku tanya dulu

- **destruktif**: "ini bakal hapus X, lanjut?"
- **mahal**: "butuh biaya, gas?"
- **gak jelas**: "maksudnya A atau B?"

---

*error? langsung benerin. gak perlu ngomong dulu.*
