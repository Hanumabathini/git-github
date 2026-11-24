#!/usr/bin/env python3
"""Generate Instagram Reels / YouTube Shorts with WanGP, then finish them with ffmpeg.

For every video in shorts.json:
  1. each "shot" prompt is rendered by WanGP in headless mode (wgp.py --process)
  2. the clips are cropped/scaled to 1080x1920 @ 30 fps and joined
  3. captions are burned in, music (or a silent track) is added, length is capped at 59 s
Output: output/<name>.mp4, ready to upload.

Usage (Windows, from the shorts-kit folder):
  python make_shorts.py --template my_settings.json
  python make_shorts.py --assemble-only        # skip AI generation, reuse clips/ folder
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent
W, H, FPS, MAX_SECONDS = 1080, 1920, 30, 59


def run(cmd, **kw):
    print(">", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def find_wangp_python(wangp: Path, override: str | None) -> str:
    if override:
        return override
    win = platform.system() == "Windows"
    for env in ("env_uv", "venv", ".venv", "env"):
        exe = wangp / env / ("Scripts/python.exe" if win else "bin/python")
        if exe.exists():
            return str(exe)
    print("! Could not find WanGP's Python environment; using current Python. "
          "Pass --wangp-python if generation fails with missing modules.")
    return sys.executable


def generate_clip(prompt, template, wangp, py, out_dir: Path, overrides):
    out_dir.mkdir(parents=True, exist_ok=True)
    settings = dict(template)
    settings["prompt"] = prompt
    settings.update(overrides)
    job = out_dir / "job.json"
    job.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    run([py, "wgp.py", "--process", job, "--output-dir", out_dir], cwd=wangp)
    clips = sorted(out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if not clips:
        raise RuntimeError(f"WanGP produced no video in {out_dir}")
    return clips[-1]


def default_font():
    for f in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/Nirmala.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf"):
        if Path(f).exists():
            return f
    return None


def ff_path(p) -> str:
    """Escape a path for use inside an ffmpeg filter argument."""
    return str(p).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def probe_duration(path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def assemble(name, clips, captions, music, font, out_path: Path):
    tmp = Path(tempfile.mkdtemp(prefix="shorts_"))
    try:
        # 1. normalise every clip to vertical 1080x1920 @ 30fps (crop to fill, no black bars)
        norm = []
        for i, c in enumerate(clips):
            n = tmp / f"n{i:02d}.mp4"
            vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                  f"fps={FPS},setsar=1,format=yuv420p")
            run(["ffmpeg", "-y", "-v", "error", "-i", c, "-vf", vf, "-an",
                 "-c:v", "libx264", "-preset", "medium", "-crf", "18", n])
            norm.append(n)
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in norm), encoding="utf-8")
        joined = tmp / "joined.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
             "-c", "copy", joined])
        total = min(probe_duration(joined), MAX_SECONDS)

        # 2. captions: split evenly over the video, bold white text with outline
        filters = []
        if captions and font:
            seg = total / len(captions)
            for i, text in enumerate(captions):
                tf = tmp / f"cap{i}.txt"
                tf.write_text(text, encoding="utf-8")
                filters.append(
                    f"drawtext=fontfile='{ff_path(font)}':textfile='{ff_path(tf)}':"
                    f"fontcolor=white:fontsize=72:borderw=6:bordercolor=black@0.85:"
                    f"x=(w-text_w)/2:y=h*0.70:"
                    f"enable='between(t,{i * seg:.2f},{(i + 1) * seg:.2f})'")
        elif captions:
            print("! No font found, captions skipped. Pass --font PATH.")
        vf = ",".join(filters) or "null"

        # 3. audio: music trimmed + faded, or silence (platforms prefer an audio track)
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", joined]
        if music:
            cmd += ["-stream_loop", "-1", "-i", music]
            af = f"[1:a]atrim=0:{total:.2f},afade=t=out:st={max(total - 1.5, 0):.2f}:d=1.5,volume=0.8[a]"
        else:
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            af = f"[1:a]atrim=0:{total:.2f}[a]"
        cmd += ["-filter_complex", f"[0:v]{vf}[v];{af}", "-map", "[v]", "-map", "[a]",
                "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", out_path]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        run(cmd)
        print(f"✓ {name}: {out_path} ({total:.1f}s, {W}x{H})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content", default=KIT / "shorts.json", type=Path)
    ap.add_argument("--template", type=Path,
                    help="Settings JSON exported from WanGP ('Export Settings') with the model/resolution you like")
    ap.add_argument("--wangp", default=Path.home() / "WanGP", type=Path)
    ap.add_argument("--wangp-python")
    ap.add_argument("--resolution", help="Override the template resolution, e.g. 480x832 or 720x1280 (vertical)")
    ap.add_argument("--font", default=default_font())
    ap.add_argument("--assemble-only", action="store_true", help="Reuse clips already in clips/<name>/")
    ap.add_argument("--only", help="Render just this video name")
    a = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found. Install it (winget install Gyan.FFmpeg) and open a new terminal.")
    content = json.loads(a.content.read_text(encoding="utf-8"))
    music = content.get("music") or None
    if music and not Path(music).is_absolute():
        music = str((a.content.parent / music).resolve())

    template, py = {}, None
    if not a.assemble_only:
        if not a.template:
            sys.exit("Pass --template my_settings.json (see README step 3), or use --assemble-only.")
        template = json.loads(a.template.read_text(encoding="utf-8"))
        py = find_wangp_python(a.wangp, a.wangp_python)
    overrides = {"resolution": a.resolution} if a.resolution else {}

    for v in content["videos"]:
        if a.only and v["name"] != a.only:
            continue
        clip_root = KIT / "clips" / v["name"]
        clips = []
        for i, shot in enumerate(v["shots"]):
            d = clip_root / f"shot{i + 1:02d}"
            if a.assemble_only:
                found = sorted(d.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
                if not found:
                    sys.exit(f"No clip in {d}")
                clips.append(found[-1])
            else:
                print(f"\n=== {v['name']} shot {i + 1}/{len(v['shots'])} ===")
                clips.append(generate_clip(shot, template, a.wangp, py, d, overrides))
        vmusic = v.get("music")
        if vmusic and not Path(vmusic).is_absolute():
            vmusic = str((a.content.parent / vmusic).resolve())
        assemble(v["name"], clips, v.get("captions", []), vmusic or music,
                 a.font, KIT / "output" / f"{v['name']}.mp4")


if __name__ == "__main__":
    main()
