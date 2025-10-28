
import sys, argparse, traceback
from typing import Optional
from .core.scheduler import MusicScheduler

def main(argv: Optional[list] = None):
    ap = argparse.ArgumentParser(prog="amcat", description="ANSI Music cat (byte-accurate passthrough + live playback)")
    ap.add_argument("file", nargs="?", help="Input file (or read stdin)")
    ap.add_argument("--sf2", help="Path to SoundFont (.sf2); if omitted, FluidSynth default is used")
    ap.add_argument("--midi", help="Export parsed stream to MIDI file")
    ap.add_argument("--verbose", action="store_true", help="Per-block diagnostics to stderr")
    ap.add_argument("--summary", action="store_true", help="Show summary stats")
    ap.add_argument("--strict", action="store_true", help="Warn about suspicious ESC sequences")
    ap.add_argument("--test", action="store_true", help="Audio self-test and exit")
    args = ap.parse_args(argv)

    # Read bytes raw
    if not sys.stdin.isatty() and args.file is None:
        data = sys.stdin.buffer.read()
    elif args.file:
        with open(args.file, "rb") as f:
            data = f.read()
    else:
        print("Usage:\n  amcat <file>\n  cat file | amcat\nOptions: --sf2 PATH --midi out.mid --verbose --summary --strict --test", file=sys.stderr)
        return 2

    sched = MusicScheduler(sf2=args.sf2, verbose=args.verbose, summary=args.summary, midi_path=args.midi, strict=args.strict)

    if args.test:
        try:
            if sched.synth:
                sched.synth.test_blip()
                print("[✓] Audio self-test OK", file=sys.stderr)
            else:
                print("[!] No synth available", file=sys.stderr)
        finally:
            if sched.synth: sched.synth.close()
        return 0

    try:
        sched.process_stream(data)
        sched.summarize()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[!] Runtime error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1
    finally:
        if sched.synth:
            sched.synth.close()
    return 0
