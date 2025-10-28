
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set

from .utils import clamp, duration_from_length

NOTE_BASE = {'c':0,'d':2,'e':4,'f':5,'g':7,'a':9,'b':11}

@dataclass
class VoiceState:
    tempo: int = 120
    octave: int = 4
    dlen: int = 8
    time: float = 0.0

@dataclass
class Event:
    t: float
    typ: str  # 'on' or 'off'
    ch: int
    note: int
    vel: int

@dataclass
class BlockReport:
    index: int
    events: int
    notes: int
    start_time: float
    end_time: float
    voices_used: Set[int]
    tempos_seen: List[int]
    intervals: List[Tuple[float, float, int]]

class AnsiMusicParser:
    TOKEN_RE = re.compile(
        r'(V([0-9]|1[0-5]))|'
        r'(T\d+)|'
        r'(O\d+)|'
        r'(L\d+)|'
        r'([<>])|'
        r'(R(\d+)?\.?)|'
        r'([A-Ga-g](?:[#\+\-])?\d*\.?)'
    )

    def __init__(self):
        self.reset_block_states()

    def reset_block_states(self):
        self.voices: Dict[int, VoiceState] = {i: VoiceState() for i in range(16)}
        self.cur_voice: int = 0
        self.tempos_seen: List[int] = []
        self.voices_used: Set[int] = set()
        self.intervals: List[Tuple[float, float, int]] = []

    def parse_block(self, payload_bytes: bytes):
        text = payload_bytes.decode('latin-1', errors='ignore')
        events: List[Event] = []
        notes_count = 0

        for m in self.TOKEN_RE.finditer(text):
            tok = m.group(0)

            if tok.startswith('V') and tok[1:].isdigit():
                v = int(tok[1:])
                if 0 <= v <= 15:
                    self.cur_voice = v
                    self.voices_used.add(v)
                continue

            if tok.startswith('T') and tok[1:].isdigit():
                bpm = clamp(int(tok[1:]), 1, 1000)
                self.voices[self.cur_voice].tempo = bpm
                self.tempos_seen.append(bpm)
                continue

            if tok.startswith('O') and tok[1:].isdigit():
                self.voices[self.cur_voice].octave = clamp(int(tok[1:]), 0, 9)
                continue

            if tok.startswith('L') and tok[1:].isdigit():
                dlen = int(tok[1:]) or 4
                self.voices[self.cur_voice].dlen = dlen
                continue

            if tok in ('<', '>'):
                if tok == '<':
                    self.voices[self.cur_voice].octave = clamp(self.voices[self.cur_voice].octave - 1, 0, 9)
                else:
                    self.voices[self.cur_voice].octave = clamp(self.voices[self.cur_voice].octave + 1, 0, 9)
                continue

            if tok[0] in ('R','r'):
                dotted = tok.endswith('.')
                digits = ''.join(ch for ch in tok[1:] if ch.isdigit())
                Lden = int(digits) if digits else self.voices[self.cur_voice].dlen
                from .utils import duration_from_length
                d = duration_from_length(self.voices[self.cur_voice].tempo, Lden, dotted)
                self.voices[self.cur_voice].time += d
                continue

            # note
            n = tok
            dotted = n.endswith('.')
            if dotted: n = n[:-1]
            letters = ''.join(ch for ch in n if ch.isalpha() or ch in '#+-')
            digits = ''.join(ch for ch in n if ch.isdigit())
            if not letters: continue
            name = letters[0].lower()
            if name not in NOTE_BASE: continue
            accidental = 0
            if len(letters) > 1:
                acc = letters[1]
                if acc in ('#','+'): accidental = 1
                elif acc == '-': accidental = -1

            Lden = int(digits) if digits else self.voices[self.cur_voice].dlen
            from .utils import duration_from_length
            d = duration_from_length(self.voices[self.cur_voice].tempo, Lden, dotted)
            midi = NOTE_BASE[name] + accidental + (self.voices[self.cur_voice].octave + 1) * 12
            start = self.voices[self.cur_voice].time
            end = start + d
            ch = self.cur_voice
            events.append(Event(start, 'on', ch, midi, 100))
            events.append(Event(end, 'off', ch, midi, 0))
            self.intervals.append((start, end, ch))
            notes_count += 1
            self.voices[self.cur_voice].time = end
            self.voices_used.add(ch)

        end_time = max((v.time for v in self.voices.values()), default=0.0)
        report = BlockReport(
            index=-1, events=len(events), notes=notes_count,
            start_time=0.0, end_time=end_time,
            voices_used=set(self.voices_used),
            tempos_seen=list(self.tempos_seen),
            intervals=list(self.intervals),
        )
        return events, report
