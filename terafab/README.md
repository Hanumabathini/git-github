# TERAFAB: The Factory That Could Power the AI Future

This is the production package for a 3:00 documentary for YouTube: 1920×1080, 30 fps, H.264 video with AAC audio. The footage is generated as full-motion WanGP video on a local NVIDIA GPU. No credits are spent.

## Status

| Part | Status |
|---|---|
| Scene manifest (18 scenes, 36 × 5 s shots, prompts, seeds, fallback settings) | ✅ `project/scene_manifest.json` |
| Narration (18 clips, each fits its 10 s slot) | ✅ `audio/vo/`, `audio/narration.flac` |
| Original score and sound effects | ✅ `audio/music_score.flac`, `audio/sfx.flac` |
| Final audio mix (180.0 s, -14 LUFS, -1.5 dBTP, music ducked under voice) | ✅ `audio/terafab_mix.wav` |
| Subtitles (sentence timings measured from the narration audio) | ✅ `output/terafab_captions.srt` |
| YouTube metadata and fact-check | ✅ `output/metadata.md` |
| **Video renders (36 WanGP clips)** | ⏳ Not done: these must run on the RTX 5070 PC |
| Final movie, thumbnail, render report | ⏳ Made by `scripts/assemble_movie.py` once the clips exist |

The editing step was tested end to end with dummy moving clips: it produced 1920×1080 at 30 fps, AAC 48 kHz, exactly 180.00 s, with no black frames. The motion check scored moving footage at 2.9 and a still image at 0.0, which it rejects.

## Run it on the GPU PC (Windows cmd)

```cmd
cd %USERPROFILE%\git-github
git pull
cd terafab
run_all.bat
```

`run_all.bat` runs these steps:

1. **`scripts\check_system.bat`** prints the GPU, driver, VRAM, RAM, free disk, Python, Git, ffmpeg, WanGP version and the downloaded models. It changes nothing.
2. **Motion test.** It renders one 5 s robot-and-wafer clip with Wan2.2 TI2V 5B. If it fails, it reports the exact log and stops.
3. **Render.** It renders all 36 shots with `wgp.py --process`. You can stop it and run it again at any time; finished shots are skipped.
   - On a VRAM error it steps down the fallback settings: 1280×720 with 40 steps, then 1280×704 with 30 steps, then FastWan 3-step at 720p, then FastWan at 960×544.
   - A static, frozen or short clip is re-rendered with a new seed.
   - **It never substitutes still images.** Every attempt is logged in the manifest.
4. **Assemble.** It grades and upscales the clips with Lanczos, adds the concept labels and end title, muxes the mix, and writes `output/terafab_full_movie.mp4`, `output/thumbnail.png` and `output/render_report.md`.

**Expected time:** each 5 s clip at 720p takes about 4–12 minutes on an 8 GB RTX 5070 with standard steps, so the full render is likely several hours. The first run also downloads the model, about 10–20 GB. To go faster, use `python scripts\render_scenes.py --start-rung 2` (FastWan). It is quicker, at somewhat lower quality.

Useful options for `scripts\render_scenes.py`:
- `--only s07a s07b` renders just those shots.
- `--redo` re-renders shots that are already finished.
- `--template my_settings.json` starts from settings exported from the WanGP app.
- `--extra "--attention sdpa"` passes flags through to WanGP.
- `--wangp-python PATH` points to WanGP's Python if it isn't found automatically.

## Re-making the audio (optional)

The audio is already built. To change the narration or the mix:
```
pip install kokoro-onnx soundfile numpy
# download kokoro-v1.0.onnx + voices-v1.0.bin from github.com/thewh1teagle/kokoro-onnx releases into a folder
python scripts/build_manifest.py           # after editing scene text in this file
python scripts/make_audio.py --model-dir <folder> [--voice af_heart]
```

## Labels and honesty

These are added in editing, never generated inside the video:
- A persistent "AI-GENERATED VISUALIZATION" notice.
- "TERAFAB — CONCEPT VISUALIZATION" in scene 3.
- "MICROSCOPIC PROCESS — VISUALIZATION" in scene 7.
- "PROPOSED INTEGRATED WORKFLOW" in scene 10.
- "FUTURE CONCEPT — NOT AN EXISTING TERAFAB SYSTEM" in scene 16.
- "PLANS ≠ COMPLETED PRODUCTION" in scene 17.

When you upload, tick YouTube's **altered or synthetic content** box. **Nothing is uploaded automatically.**

## Licences (for monetized YouTube)

| Component | Licence | Monetized use |
|---|---|---|
| WanGP software | WanGP Community License 2.0 | Outputs may be used and sold. Credit WanGP only if you sell the output itself. |
| Wan2.2 TI2V-5B weights | Apache-2.0 (Wan-AI) | Allowed |
| FastWan LoRA (fallback only) | Check its Hugging Face card before using that fallback | Verify |
| Kokoro-82M narration voice | Apache-2.0 | Allowed. The voice is synthetic, so disclose it. |
| Music and sound effects | Original, synthesized by `make_audio.py` | Allowed |
| Overlay font | Arial (Windows) | Allowed for rendered text in video |

On the PC, `check_system.bat` lists the model files that were actually downloaded. If a different model gets used, check its licence before publishing.
