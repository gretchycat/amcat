
import time, os
from typing import List, Optional

try:
    import fluidsynth  # type: ignore
except Exception:
    fluidsynth = None

try:
    import mido  # type: ignore
except Exception:
    mido = None

from .parser import Event

class SynthEngine:
    def __init__(self, sf2: Optional[str] = None):
        if fluidsynth is None:
            raise RuntimeError("pyFluidSynth not available. Install with: pip install pyFluidSynth")
        self.fs = fluidsynth.Synth()
        self.fs.start()  # auto driver
        self.sfid = None
        if sf2:
            if not os.path.exists(sf2):
                raise RuntimeError(f"SoundFont not found: {sf2}")
            self.sfid = self.fs.sfload(sf2)
            for ch in range(16):
                self.fs.program_select(ch, self.sfid, 0, 0)

    def play_events(self, events: List[Event], t_offset: float, origin: float):
        shifted = [(e.t + t_offset, e.typ, e.ch, e.note, e.vel) for e in events]
        shifted.sort(key=lambda x: (x[0], 0 if x[1]=='off' else 1))
        idx = 0
        N = len(shifted)
        while idx < N:
            t_ev, typ, ch, note, vel = shifted[idx]
            now = time.time() - origin
            if now < t_ev:
                time.sleep(max(0.0, t_ev - now))
                continue
            while idx < N and abs(shifted[idx][0] - t_ev) < 1e-4:
                _, typ, ch, note, vel = shifted[idx]
                if typ == 'on':
                    self.fs.noteon(ch, note, vel if vel>0 else 100)
                else:
                    self.fs.noteoff(ch, note)
                idx += 1

    def test_blip(self):
        for ch, key in [(0,60),(1,64),(2,67)]:
            self.fs.noteon(ch, key, 95)
        time.sleep(0.25)
        for ch, key in [(0,60),(1,64),(2,67)]:
            self.fs.noteoff(ch, key)

    def close(self):
        self.fs.delete()

class MidiWriter:
    def __init__(self, path: str):
        if mido is None:
            raise RuntimeError("MIDI export requested but 'mido' is not installed. pip install mido")
        self.path = path
        self.mid = mido.MidiFile(ticks_per_beat=480)
        self.tracks = [mido.MidiTrack() for _ in range(16)]
        for tr in self.tracks:
            self.mid.tracks.append(tr)
        self.last_ticks = [0]*16
        self.tempo_us_per_beat = 500000

    def set_tempo(self, bpm: int):
        self.tempo_us_per_beat = int(60_000_000 / max(1, bpm))
        for tr in self.tracks:
            tr.append(mido.MetaMessage('set_tempo', tempo=self.tempo_us_per_beat, time=0))

    def _sec_to_ticks(self, sec: float) -> int:
        beats_per_sec = 1.0 / (self.tempo_us_per_beat / 1_000_000.0)
        return max(0, int(round(sec * self.mid.ticks_per_beat * beats_per_sec)))

    def add_events(self, events: List[Event], t_offset: float = 0.0):
        abs_events = [(e.t + t_offset, e) for e in events]
        abs_events.sort(key=lambda x: (x[0], 0 if x[1].typ=='off' else 1))
        for abs_t, e in abs_events:
            tr = self.tracks[e.ch]
            ticks = self._sec_to_ticks(abs_t)
            delta = ticks - self.last_ticks[e.ch]
            self.last_ticks[e.ch] = ticks
            if e.typ == 'on':
                tr.append(mido.Message('note_on', channel=e.ch, note=e.note, velocity=max(1,e.vel), time=delta))
            else:
                tr.append(mido.Message('note_off', channel=e.ch, note=e.note, velocity=0, time=delta))

    def save(self):
        self.mid.save(self.path)
