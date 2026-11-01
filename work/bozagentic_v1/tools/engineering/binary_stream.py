"""
tools/engineering/binary_stream.py
BOZAGENTIC Framework — Binary-Safe I/O Pipeline
Prevents truncation, encoding corruption, and sanitization of raw exploit payloads, shellcodes, and hex streams.
"""

import sys
import base64
import binascii

def encode_payload(raw_bytes: bytes) -> dict:
    """Encodes raw bytecode/exploit payload into multiple safe transport representations."""
    return {
        "length_bytes": len(raw_bytes),
        "hex": binascii.hexlify(raw_bytes).decode("ascii"),
        "base64": base64.b64encode(raw_bytes).decode("ascii"),
        "escaped_c": "".join(f"\\x{b:02x}" for b in raw_bytes)
    }

def decode_payload(data_str: str) -> bytes:
    """Decodes hex or base64 representation back to raw bytes safely."""
    data_clean = data_str.strip().replace(" ", "").replace("\n", "")
    if data_clean.startswith("0x"):
        data_clean = data_clean[2:]
    
    # Try Hex
    try:
        return binascii.unhexlify(data_clean)
    except Exception:
        pass
    
    # Try Base64
    try:
        return base64.b64decode(data_clean)
    except Exception:
        pass
    
    return data_str.encode("utf-8")

def stream_raw(payload_bytes: bytes):
    """Directly stream uncorrupted binary data to stdout buffer."""
    sys.stdout.buffer.write(payload_bytes)
    sys.stdout.buffer.flush()

if __name__ == "__main__":
    sample = b"\x90\x90\x90\x31\xc0\x50\x68\x2f\x2f\x73\x68"
    enc = encode_payload(sample)
    print("Self-check binary stream encoder:")
    print(enc)
    assert decode_payload(enc["hex"]) == sample
    assert decode_payload(enc["base64"]) == sample
    print("Assertion tests passed.")
