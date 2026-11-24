#!/usr/bin/env python3
"""Builds the complete 180 s audio track for the Terafab documentary — no GPU needed.

* Narration: Kokoro-82M TTS (Apache-2.0 weights) via kokoro-onnx, synthesised sentence by
  sentence so every subtitle cue uses the measured audio timing (not a guess).
* Score + sound effects: synthesised from scratch here (original, no third-party samples).
* Mix: music side-chain ducked under the voice, loudness-normalised to -14 LUFS (YouTube).

Outputs: audio/vo/sceneNN.flac, audio/{narration,music_score,sfx}.flac, audio/terafab_mix.wav,
         output/terafab_captions.srt, project/vo_timings.json

Requires: pip install kokoro-onnx soundfile numpy ; ffmpeg on PATH ;
          kokoro-v1.0.onnx + voices-v1.0.bin (github.com/thewh1teagle/kokoro-onnx releases)
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
SR = 48000
TOTAL = 180.0
VO_OFFSET = 0.45      # narration starts this long after each scene cut
VO_MAX = 9.1          # narration must end before the next scene (sound bridge room)
rng = np.random.default_rng(7)


# ---------------------------------------------------------------- narration
def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()]


def resample(x, sr_in):
    if sr_in == SR:
        return x
    n = int(round(len(x) * SR / sr_in))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def trim_silence(x, thr=0.004):
    idx = np.where(np.abs(x) > thr)[0]
    if not len(idx):
        return x
    return x[max(idx[0] - int(0.02 * SR), 0): idx[-1] + int(0.06 * SR)]


def synth_scene(kokoro, text, voice, speed):
    parts, cues, t = [], [], 0.0
    gap = np.zeros(int(0.28 * SR), np.float32)
    for k, sent in enumerate(split_sentences(text)):
        audio, sr = kokoro.create(sent, voice=voice, speed=speed, lang="en-us")
        a = trim_silence(resample(np.asarray(audio, np.float32), sr))
        if k:
            parts.append(gap)
            t += len(gap) / SR
        cues.append({"text": sent, "start": t, "end": t + len(a) / SR})
        parts.append(a)
        t += len(a) / SR
    return np.concatenate(parts), cues


def wrap_caption(text, width=42):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return lines


def split_cue(cue):
    """Long sentences -> several caption cues (<=2 lines of 42 chars), timed by character share."""
    lines = wrap_caption(cue["text"])
    if len(lines) <= 2:
        return [{"start": cue["start"], "end": cue["end"], "lines": lines}]
    chunks = [lines[i:i + 2] for i in range(0, len(lines), 2)]
    total_chars = sum(len(" ".join(c)) for c in chunks)
    out, t = [], cue["start"]
    for c in chunks:
        d = (cue["end"] - cue["start"]) * len(" ".join(c)) / total_chars
        out.append({"start": t, "end": t + d, "lines": c})
        t += d
    return out


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


# ---------------------------------------------------------------- synthesis helpers
def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def env_adsr(n, a, r):
    e = np.ones(n, np.float32)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(x, cutoff):
    # one-pole low-pass, vectorised via lfilter-equivalent recursion in numpy (chunked)
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(0, len(x), 4096):
        seg = x[i:i + 4096]
        out = np.empty_like(seg)
        for j, v in enumerate(seg):
            acc = (1 - a) * v + a * acc
            out[j] = acc
        y[i:i + 4096] = out
    return y


def fast_lowpass(x, cutoff):
    """FFT brick-ish low-pass (fast for long buffers)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x)).astype(np.float32)


def bandpass_noise(dur, lo, hi):
    n = int(dur * SR)
    X = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, n)
    return (y / (np.abs(y).max() + 1e-9)).astype(np.float32)


def place(buf, clip, t, gain=1.0):
    i = int(t * SR)
    j = min(i + len(clip), len(buf))
    if i < len(buf):
        buf[i:j] += clip[: j - i] * gain


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


# ---------------------------------------------------------------- music (original score)
def make_music():
    n = int(TOTAL * SR)
    L = np.zeros(n, np.float32)
    R = np.zeros(n, np.float32)
    # D minor cinematic progression, one chord per 5 s: Dm Bb F C | Dm Bb Gm A
    prog = [[50, 57, 62, 65], [46, 53, 58, 62], [41, 53, 57, 60], [48, 55, 60, 64],
            [50, 57, 62, 65], [46, 53, 58, 62], [43, 55, 58, 62], [45, 52, 57, 61]]
    # intensity per scene (1..18): builds, dips for "risks"/"confirmed", lifts at the end
    inten = [0.55, 0.6, 0.8, 0.7, 0.6, 0.6, 0.7, 0.75, 0.75, 0.7, 0.85, 0.85, 0.9, 0.9,
             0.55, 0.7, 0.5, 1.0]
    for c in range(int(TOTAL // 5)):
        t0 = c * 5.0
        chord = prog[c % len(prog)]
        lvl = inten[min(int(t0 // 10), 17)]
        dur = 5.8
        tt = t_axis(dur)
        e = env_adsr(len(tt), 1.2, 1.6)
        pad_l = np.zeros(len(tt), np.float32)
        pad_r = np.zeros(len(tt), np.float32)
        for note in chord:
            f = midi(note)
            for det, pan in ((-0.12, 0.8), (0.12, 0.2), (0.0, 0.5)):
                ff = f * 2 ** (det / 12)
                w = (np.sin(2 * np.pi * ff * tt) + 0.35 * np.sin(2 * np.pi * 2 * ff * tt)
                     + 0.12 * np.sin(2 * np.pi * 3 * ff * tt))
                pad_l += w * pan
                pad_r += w * (1 - pan)
        # sub bass on root
        sub = np.sin(2 * np.pi * midi(chord[0] - 12) * tt) * 0.9
        place(L, (pad_l * 0.045 + sub * 0.10) * e * lvl, t0)
        place(R, (pad_r * 0.045 + sub * 0.10) * e * lvl, t0)
        # amber arpeggio pulse (8th notes at 96 bpm) from scene 2, except scene 17
        sc = int(t0 // 10) + 1
        if sc >= 2 and sc != 17:
            step = 60 / 96 / 2
            arp = [chord[1] + 12, chord[2] + 12, chord[3] + 12, chord[2] + 12]
            for k in range(int(5 / step)):
                f = midi(arp[k % 4])
                tn = t_axis(0.35)
                note = np.sin(2 * np.pi * f * tn) * np.exp(-tn * 9) + \
                    0.3 * np.sin(2 * np.pi * 2 * f * tn) * np.exp(-tn * 14)
                pan = 0.3 + 0.4 * (k % 2)
                g = 0.05 * lvl * (0.6 if sc in (15, 16) else 1)
                place(L, note * g * pan, t0 + k * step)
                place(R, note * g * (1 - pan), t0 + k * step)
    # soft fade in/out
    fi, fo = int(1.5 * SR), int(3.0 * SR)
    for ch in (L, R):
        ch[:fi] *= np.linspace(0, 1, fi)
        ch[-fo:] *= np.linspace(1, 0, fo)
    m = np.stack([fast_lowpass(L, 6000), fast_lowpass(R, 6000)], 1)
    return m / (np.abs(m).max() + 1e-9) * 0.5


# ---------------------------------------------------------------- sound effects (original)
def sfx_bass_hit():
    t = t_axis(2.5)
    f = 70 * np.exp(-t * 1.2) + 32
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * np.exp(-t * 1.6)).astype(np.float32)


def sfx_hum(dur):
    t = t_axis(dur)
    h = sum(np.sin(2 * np.pi * 60 * k * t) / k for k in (1, 2, 3, 5)) * 0.4
    h += bandpass_noise(dur, 80, 400) * 0.3
    return (h * env_adsr(len(t), dur * 0.6, 1.0)).astype(np.float32)


def sfx_tick():
    t = t_axis(0.05)
    return (bandpass_noise(0.05, 2000, 7000) * np.exp(-t * 120)).astype(np.float32)


def sfx_chime():
    t = t_axis(2.5)
    return sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) * a
               for f, d, a in ((1318.5, 2.2, 1), (2637, 3.5, .4), (3520, 5, .2))).astype(np.float32)


def sfx_whoosh(dur=1.4):
    t = t_axis(dur)
    e = np.sin(np.pi * t / dur) ** 2
    return (bandpass_noise(dur, 300, 3000) * e).astype(np.float32)


def sfx_bed(dur, lo, hi):
    t = t_axis(dur)
    return (bandpass_noise(dur, lo, hi) * env_adsr(len(t), 0.8, 1.2)).astype(np.float32)


def make_sfx(manifest):
    n = int(TOTAL * SR)
    out = np.zeros(n, np.float32)
    for sc in manifest["scenes"]:
        t0, kw = sc["start"], sc["sound"].lower()
        if "bass hit" in kw or "final hit" in kw:
            place(out, sfx_bass_hit(), t0 + (8.6 if "final" in kw else 0.0), 0.8)
        if "hum" in kw or "rumble" in kw or "drone" in kw:
            place(out, sfx_hum(10.4), t0, 0.12)
        if "tick" in kw or "click" in kw:
            for k in range(36):
                place(out, sfx_tick(), t0 + 0.3 + k * 0.27, 0.10)
        if "chime" in kw or "piano" in kw or "beeps" in kw:
            place(out, sfx_chime(), t0 + 6.5, 0.10)
        if "whoosh" in kw or "wind" in kw or "air" in kw or "swell" in kw:
            place(out, sfx_whoosh(), t0 - 0.6 if t0 else 0, 0.18)
        if any(k in kw for k in ("fan", "hiss", "vacuum", "motor", "tire", "servo", "saw", "forklift", "crane")):
            place(out, sfx_bed(10.4, 200, 2500), t0, 0.05)
        # sound bridge: soft whoosh leading into every cut
        if t0:
            place(out, sfx_whoosh(0.8), t0 - 0.5, 0.07)
    return np.stack([out, out], 1)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", type=Path, required=True)
    ap.add_argument("--voice", default="af_heart")
    a = ap.parse_args()

    from kokoro_onnx import Kokoro
    kokoro = Kokoro(str(a.model_dir / "kokoro-v1.0.onnx"), str(a.model_dir / "voices-v1.0.bin"))
    manifest = json.loads((ROOT / "project/scene_manifest.json").read_text(encoding="utf-8"))

    (ROOT / "audio/vo").mkdir(parents=True, exist_ok=True)
    (ROOT / "output").mkdir(exist_ok=True)
    narration = np.zeros(int(TOTAL * SR), np.float32)
    timings, srt_cues = [], []
    for sc in manifest["scenes"]:
        speed = 1.0
        while True:
            vo, cues = synth_scene(kokoro, sc["narration"], a.voice, speed)
            dur = len(vo) / SR
            if dur <= VO_MAX or speed >= 1.25:
                break
            speed = round(min(speed * dur / VO_MAX + 0.01, 1.25), 3)
        if dur > VO_MAX:
            raise SystemExit(f"Scene {sc['scene']} narration is {dur:.2f}s even at speed {speed}; shorten it.")
        sf.write(ROOT / sc["narration_audio"], vo, SR)
        start = sc["start"] + VO_OFFSET
        place(narration, vo, start)
        for c in cues:
            c["start"] += start
            c["end"] += start
            srt_cues += split_cue(c)
        timings.append({"scene": sc["scene"], "speed": speed, "vo_start": round(start, 3),
                        "vo_duration": round(dur, 3),
                        "sentences": [{**c, "start": round(c["start"], 3), "end": round(c["end"], 3)} for c in cues]})
        print(f"scene {sc['scene']:02d}: {dur:5.2f}s at speed {speed}")

    with open(ROOT / "output/terafab_captions.srt", "w", encoding="utf-8") as f:
        for i, c in enumerate(srt_cues, 1):
            f.write(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'] + 0.15)}\n" + "\n".join(c["lines"]) + "\n\n")
    (ROOT / "project/vo_timings.json").write_text(json.dumps(
        {"voice": f"Kokoro-82M {a.voice}", "vo_offset": VO_OFFSET, "scenes": timings}, indent=2), encoding="utf-8")

    music = make_music()
    sfx = make_sfx(manifest)

    # side-chain duck: music down ~9 dB while narration is speaking (smoothed envelope)
    env = np.abs(narration)
    win = int(0.25 * SR)
    env = np.convolve(env, np.ones(win) / win, mode="same")
    duck = 1 - 0.65 * np.clip(env / 0.02, 0, 1)
    duck = np.convolve(duck, np.ones(int(0.3 * SR)) / int(0.3 * SR), mode="same")[:, None]

    voice = np.stack([narration, narration], 1)
    mix = voice * 1.0 + music * duck * 0.55 + sfx * 0.6
    sf.write(ROOT / "audio/narration.flac", voice, SR)
    sf.write(ROOT / "audio/music_score.flac", music, SR)
    sf.write(ROOT / "audio/sfx.flac", sfx, SR)
    raw = ROOT / "audio/_mix_raw.wav"
    sf.write(raw, mix / max(1.0, np.abs(mix).max() / 0.9), SR)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), "-t", str(TOTAL),
                    str(ROOT / "audio/terafab_mix.wav")], check=True)
    raw.unlink()
    print("wrote audio/terafab_mix.wav and output/terafab_captions.srt")


if __name__ == "__main__":
    main()
