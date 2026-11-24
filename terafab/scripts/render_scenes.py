#!/usr/bin/env python3
"""Render every shot in project/scene_manifest.json with WanGP's headless mode.

  python scripts/render_scenes.py --motion-test          # one 5 s wafer-handling test clip
  python scripts/render_scenes.py                        # all 36 shots (resumes; skips finished)
  python scripts/render_scenes.py --only s07a s07b       # specific shots
  python scripts/render_scenes.py --template my_settings.json   # base on settings exported from WanGP UI

Each shot is run through wgp.py --process <job.json> --output-dir clips/<id>/attempt_N.
After each render the clip is probed (duration, resolution, codec) and its motion is measured
with ffmpeg (mean absolute luma difference between consecutive frames, 0-255 scale). A clip
whose motion score is below --min-motion is treated as a failed (static) render and retried with
a new seed; GPU/VRAM failures step down the fallback ladder in the manifest. Static images are
never substituted. Progress is saved to the manifest after every attempt, so it can be resumed.
Credits spent: zero — everything runs on the local GPU.
"""
import argparse
import datetime as dt
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "project/scene_manifest.json"
CLIPS = ROOT / "clips"

MOTION_TEST_PROMPT = (
    "Close-up of a robotic arm picking up a polished silicon wafer from a wafer cassette and "
    "placing it onto a rotating inspection stage inside a semiconductor cleanroom, the wafer spins, "
    "the arm retracts, camera slowly pushes in, photorealistic cinematic documentary CGI, "
    "cool teal and amber lighting, no text, no logos")


def load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def save(m):
    tmp = MANIFEST.with_suffix(".tmp")
    tmp.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(MANIFEST)


def find_python(wangp: Path, override):
    if override:
        return override
    win = platform.system() == "Windows"
    for env in ("env_uv", "env_venv", "venv", ".venv", "env"):
        exe = wangp / env / ("Scripts/python.exe" if win else "bin/python")
        if exe.exists():
            return str(exe)
    # Conda env created by WanGP's installer is usually called wan2gp
    conda = shutil.which("conda")
    if conda:
        return f"conda run -n wan2gp python"
    return sys.executable


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=codec_name,width,height,r_frame_rate,nb_frames:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True)
    if out.returncode:
        return None
    j = json.loads(out.stdout)
    s = j["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return {"codec": s["codec_name"], "width": s["width"], "height": s["height"],
            "fps": round(int(num) / int(den), 3), "duration": round(float(j["format"]["duration"]), 3)}


def motion_score(path):
    """Mean |frame(n) - frame(n-1)| luma over the clip, plus the fraction of near-identical frames."""
    cmd = ["ffmpeg", "-v", "info", "-i", str(path), "-vf",
           "scale=320:-2,format=gray,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
           "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    vals = [float(v) for v in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", err)]
    if not vals:
        return 0.0, 1.0
    frozen = sum(v < 0.15 for v in vals) / len(vals)
    return round(sum(vals) / len(vals), 3), round(frozen, 3)


def render(shot, base, rung, seed, args, py):
    attempt_no = len(shot.get("attempts", [])) + 1
    out_dir = CLIPS / shot["id"] / f"attempt_{attempt_no}"
    out_dir.mkdir(parents=True, exist_ok=True)
    job = dict(base)
    job.update({
        "model_type": rung["model_type"],
        "prompt": shot["prompt"],
        "negative_prompt": shot["negative_prompt"],
        "resolution": rung["resolution"],
        "num_inference_steps": rung["num_inference_steps"],
        "video_length": args.frames,
        "seed": seed,
    })
    if "fastwan" in rung["model_type"]:
        job["guidance_scale"] = 1
    (out_dir / "job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    cmd = py.split() if py.startswith("conda ") else [py]
    cmd += ["wgp.py", "--process", str(out_dir / "job.json"), "--output-dir", str(out_dir)]
    if args.extra:
        cmd += args.extra.split()
    started = dt.datetime.now()
    print(f"\n=== {shot['id']} attempt {attempt_no}: {rung['model_type']} {rung['resolution']} "
          f"steps={rung['num_inference_steps']} seed={seed}", flush=True)
    log = out_dir / "wangp.log"
    with open(log, "w", encoding="utf-8", errors="replace") as lf:
        rc = subprocess.run(cmd, cwd=args.wangp, stdout=lf, stderr=subprocess.STDOUT).returncode
    secs = round((dt.datetime.now() - started).total_seconds(), 1)
    vids = sorted(out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    rec = {"n": attempt_no, "model_type": rung["model_type"], "resolution": rung["resolution"],
           "steps": rung["num_inference_steps"], "seed": seed, "exit_code": rc,
           "seconds": secs, "log": str(log.relative_to(ROOT))}
    if not vids:
        tail = log.read_text(encoding="utf-8", errors="replace")[-1500:]
        oom = bool(re.search(r"out of memory|CUDA error|OutOfMemory|allocat", tail, re.I))
        rec.update(result="no_output", oom=oom)
        print(f"  ✗ no video produced (exit {rc}{', VRAM' if oom else ''}). See {log}")
        return rec, None
    clip = vids[-1]
    info = probe(clip)
    score, frozen = motion_score(clip)
    rec.update(output=str(clip.relative_to(ROOT)), probe=info, motion_score=score, frozen_fraction=frozen)
    ok = info is not None and info["duration"] >= 4.5 and score >= args.min_motion and frozen < 0.5
    rec["result"] = "ok" if ok else "rejected_static_or_short"
    print(f"  {'✓' if ok else '✗'} {info} motion={score} frozen={frozen} in {secs}s")
    return rec, (clip if ok else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wangp", type=Path, default=Path.home() / "WanGP")
    ap.add_argument("--wangp-python")
    ap.add_argument("--template", type=Path, help="Settings JSON exported from the WanGP UI to use as base")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--motion-test", action="store_true")
    ap.add_argument("--start-rung", type=int, default=0, help="Index into the fallback ladder to start from")
    ap.add_argument("--frames", type=int, default=121, help="121 frames = 5 s at Wan 2.2's 24 fps")
    ap.add_argument("--max-attempts", type=int, default=5)
    ap.add_argument("--min-motion", type=float, default=0.5)
    ap.add_argument("--extra", default="", help="Extra wgp.py flags, e.g. '--attention sdpa'")
    ap.add_argument("--redo", action="store_true", help="Re-render shots already marked done")
    args = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found on PATH")
    if not (args.wangp / "wgp.py").exists():
        sys.exit(f"WanGP not found at {args.wangp} (pass --wangp)")
    py = find_python(args.wangp, args.wangp_python)
    print("WanGP python:", py)
    base = json.loads(args.template.read_text(encoding="utf-8")) if args.template else {}
    for k in ("prompt", "negative_prompt", "seed", "image_start", "image_end", "video_source"):
        base.pop(k, None)

    m = load()
    ladder = m["generator"]["fallback_ladder"]

    if args.motion_test:
        shot = {"id": "motion_test", "prompt": MOTION_TEST_PROMPT,
                "negative_prompt": m["scenes"][0]["shots"][0]["negative_prompt"], "attempts": []}
        for r in range(args.start_rung, len(ladder)):
            rec, clip = render(shot, base, ladder[r], 4242, args, py)
            shot["attempts"].append(rec)
            (CLIPS / "motion_test" / "result.json").write_text(json.dumps(shot, indent=2), encoding="utf-8")
            if clip:
                print(f"\nMOTION TEST PASSED on rung {r}: {ladder[r]}\nClip: {clip}\n"
                      f"Use --start-rung {r} for the full render.")
                return
            if rec["result"] == "no_output" and not rec.get("oom"):
                break
        sys.exit("\nMOTION TEST FAILED — see clips/motion_test/*/wangp.log. No static fallback is used.")

    todo = [sh for sc in m["scenes"] for sh in sc["shots"]
            if (not args.only or sh["id"] in args.only) and (args.redo or sh["status"] != "done")]
    print(f"{len(todo)} shot(s) to render")
    for sh in todo:
        rung, seed = args.start_rung, sh["seed"]
        for a in sh["attempts"]:
            a.pop("session", None)          # attempts from an interrupted earlier run
        sh["status"] = "rendering"
        save(m)
        while len([a for a in sh["attempts"] if a.get("session") == "current"]) < args.max_attempts:
            rec, clip = render(sh, base, ladder[rung], seed, args, py)
            rec["session"] = "current"
            sh["attempts"].append(rec)
            if clip:
                sh.update(status="done", output=rec["output"], motion_score=rec["motion_score"],
                          seed=seed, settings_used=ladder[rung])
                save(m)
                break
            if rec["result"] == "no_output" and rec.get("oom") and rung + 1 < len(ladder):
                rung += 1                      # VRAM: step down the ladder
            else:
                seed += 7919                   # static/short/other failure: new seed
            save(m)
        else:
            sh["status"] = "failed"
            save(m)
            print(f"  !! {sh['id']} failed after {args.max_attempts} attempts — fix and re-run; nothing is faked.")
        for a in sh["attempts"]:
            a.pop("session", None)
        save(m)

    done = sum(sh["status"] == "done" for sc in m["scenes"] for sh in sc["shots"])
    print(f"\n{done}/36 shots rendered with motion. Next: python scripts/assemble_movie.py")


if __name__ == "__main__":
    main()
