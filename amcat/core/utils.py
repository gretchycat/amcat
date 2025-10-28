
def hex_preview(b: bytes, max_len: int = 8) -> str:
    return " ".join(f"{x:02X}" for x in b[:max_len])

def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))

def seconds_per_quarter(bpm: int) -> float:
    return 60.0 / max(1, bpm)

def duration_from_length(bpm: int, length_den: int, dotted: bool) -> float:
    base = (4.0 / max(1, length_den)) * seconds_per_quarter(bpm)
    return base * 1.5 if dotted else base
