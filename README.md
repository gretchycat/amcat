# amcat — ANSI Music Cat

Bit-perfect terminal **passthrough** + **live ANSI-music playback** using FluidSynth — with optional **MIDI export**, **summary analytics**, and **strict** ANSI validation.

## Quickstart

```bash
# prerequisites (Linux example)
sudo apt-get install -y fluidsynth
python -m pip install pyFluidSynth mido

# install amcat in editable mode
pip install -e .

# play an ANSI-music file with full terminal art preserved
amcat ghostbusters.ams --summary --strict
```
