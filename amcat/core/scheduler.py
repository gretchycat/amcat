
import re, sys, time
from typing import List, Tuple, Optional

from .parser import AnsiMusicParser, Event, BlockReport
from .synth import SynthEngine, MidiWriter

class ByteScanner:
    BLOCK_RE = re.compile(rb'\x1b\[(?:[0-9;?]*[A-Za-z])*M(?:F)?\s*', re.DOTALL)

    def __init__(self, strict: bool=False):
        self.strict = strict

    def iter_segments(self, data: bytes):
        cursor = 0
        for m in self.BLOCK_RE.finditer(data):
            if m.start() > cursor:
                yield (data[cursor:m.start()], None)
            p_start = m.end()
            next_esc = data.find(b'\x1b', p_start)
            if next_esc == -1:
                payload = data[p_start:]
                cursor = len(data)
            else:
                payload = data[p_start:next_esc]
                cursor = next_esc
            yield (None, payload)
        if cursor < len(data):
            yield (data[cursor:], None)

class MusicScheduler:
    def __init__(self, sf2: Optional[str], verbose: bool, summary: bool,
                 midi_path: Optional[str], strict: bool):
        self.verbose = verbose
        self.summary = summary
        self.strict = strict

        self.parser = AnsiMusicParser()
        self.synth = SynthEngine(sf2) if not self._dry() else None
        self.midi = MidiWriter(midi_path) if midi_path else None

        self.global_offset = 0.0
        self.block_reports: List[BlockReport] = []
        self.intervals_global: List[Tuple[float,float,int]] = []
        self.tempos_global: List[int] = []

    def _dry(self) -> bool:
        return False

    def log(self, msg: str):
        if self.verbose:
            print(msg, file=sys.stderr)

    def process_stream(self, data: bytes):
        scanner = ByteScanner(strict=self.strict)
        start_wall = time.time()
        block_idx = 0

        for non_music, payload in scanner.iter_segments(data):
            if non_music:
                sys.stdout.buffer.write(non_music)
                sys.stdout.buffer.flush()

            if payload is None:
                continue

            self.parser.reset_block_states()
            events, rep = self.parser.parse_block(payload)
            rep.index = block_idx
            rep.start_time = self.global_offset
            rep.end_time = self.global_offset + (rep.end_time - 0.0)

            if self.verbose:
                self.log(f"[block {block_idx}] notes={rep.notes} events={rep.events} "
                         f"duration={rep.end_time - rep.start_time:.3f}s "
                         f"voices={sorted(rep.voices_used) if rep.voices_used else [0]} "
                         f"tempos={rep.tempos_seen or ['(default)']}")

            if self.synth and events:
                self.synth.play_events(events, t_offset=self.global_offset, origin=start_wall)

            if self.midi and events:
                if block_idx == 0:
                    self.midi.set_tempo(rep.tempos_seen[0] if rep.tempos_seen else 120)
                self.midi.add_events(events, t_offset=self.global_offset)

            self.tempos_global.extend(rep.tempos_seen or [])
            for (s,e,v) in rep.intervals:
                self.intervals_global.append((s + self.global_offset, e + self.global_offset, v))

            self.global_offset = rep.end_time
            self.block_reports.append(rep)
            block_idx += 1

        if self.midi:
            self.midi.save()
            self.log(f"[midi] wrote {self.midi.path}")

    def summarize(self):
        if not self.summary:
            return

        blocks = len(self.block_reports)
        notes  = sum(r.notes for r in self.block_reports)
        events = sum(r.events for r in self.block_reports)
        duration = self.global_offset

        voices_used = set()
        for r in self.block_reports:
            voices_used |= r.voices_used or set([0])

        tempos = self.tempos_global or [120]
        tempo_min, tempo_max = min(tempos), max(tempos)
        tempo_avg = sum(tempos)/len(tempos) if tempos else 0.0

        points = []
        for (s,e,_v) in self.intervals_global:
            points.append((s, +1))
            points.append((e, -1))
        points.sort(key=lambda x: (x[0], -x[1]))
        active=0; poly_max=0; area=0.0
        last_t = points[0][0] if points else 0.0
        for t,delta in points:
            dt = max(0.0, t-last_t)
            area += active*dt
            active += delta
            poly_max = max(poly_max, active)
            last_t = t
        poly_avg = (area/duration) if duration>0 else 0.0

        print("\n--- ANSI Music Summary ---", file=sys.stderr)
        print(f"Blocks:     {blocks}", file=sys.stderr)
        print(f"Notes:      {notes}", file=sys.stderr)
        print(f"Events:     {events}", file=sys.stderr)
        print(f"Duration:   {duration:.3f} s", file=sys.stderr)
        print(f"Voices:     {len(voices_used)} declared ({', '.join('V'+str(v) for v in sorted(voices_used))})", file=sys.stderr)
        print(f"Polyphony:  {poly_avg:.3f} avg | {poly_max} max", file=sys.stderr)
        print(f"Tempo:      {tempo_min}–{tempo_max} bpm (avg {tempo_avg:.2f})", file=sys.stderr)

        if duration > 0 and self.intervals_global:
            buckets = 40
            width = duration / buckets
            hist = []
            for i in range(buckets):
                tmid = (i+0.5)*width
                c=0
                for (s,e,_v) in self.intervals_global:
                    if s <= tmid < e:
                        c += 1
                hist.append(c)
            max_c = max(hist) if hist else 0
            if max_c > 0:
                print("Polyphony over time:", file=sys.stderr)
                scale = 20 / max_c
                for level in range(20,0,-1):
                    row = ''.join('#' if h*scale >= level else ' ' for h in hist)
                    print(row, file=sys.stderr)
                print('-'*len(hist), file=sys.stderr)
                print(''.join(str((i//10)%10) if i%10==0 else ' ' for i in range(len(hist))), file=sys.stderr)
