# Shorts Kit: WanGP to Instagram Reels and YouTube Shorts

This kit turns your text prompts into vertical videos (1080×1920, 30 fps, H.264 + AAC, up to 59 s) that you can upload straight to **Instagram Reels** and **YouTube Shorts**. The AI clips are made with [WanGP](https://github.com/deepbeepmeep/Wan2GP) on your own NVIDIA GPU (8 GB+ VRAM recommended).

## 1. Install (once)
Copy this `shorts-kit` folder to your PC and double-click **`install_wangp.bat`**. It:
- checks your NVIDIA GPU
- installs Git, Python 3.11 and ffmpeg with `winget`
- downloads WanGP to `%USERPROFILE%\WanGP`
- runs WanGP's official installer. Pick **Auto Install** when it asks.

If it says git isn't found, close the window and run it again; a new window picks up the newly installed tools.

## 2. Make one test video in the WanGP app
1. Double-click **`start_wangp.bat`** and open http://localhost:7860.
2. Pick a text-to-video model. For 8–12 GB of VRAM, start with a small or fast one, such as a Wan 2.2 5B or LTX model.
3. Choose a **vertical (portrait) resolution**, such as 480x832 or 720x1280. Set about 5 seconds and press **Generate**.
4. When you like the result, click **Export Settings** and save the file as `my_settings.json` in this folder. It becomes the template for every shot: the model, resolution, steps and length are reused, and only the prompt changes.

The first run downloads the model weights, which can be many GB.

## 3. Write your content: `shorts.json`
```json
{
  "music": "music/background.mp3",
  "videos": [
    {
      "name": "my_first_short",
      "shots": ["prompt for clip 1", "prompt for clip 2", "prompt for clip 3"],
      "captions": ["Text shown first", "Then this", "Follow for more"]
    }
  ]
}
```
- **shots**: one AI clip for each prompt, joined in order. 3–6 shots of about 5 s make a 15–30 s Short.
- **captions**: shown at the bottom, spread evenly over the video. Keep each one short (under 25 characters) so it fits on one line.
- **music**: optional. Each video can also set its own `"music"`. Without music, a silent track is added.
- Only use music you have the rights to. You can also leave it empty and add trending audio in the Instagram or YouTube app.

## 4. Render
Double-click **`render_shorts.bat`**, or run:
```
python make_shorts.py --template my_settings.json
python make_shorts.py --template my_settings.json --only my_first_short
python make_shorts.py --assemble-only      # re-cut captions/music without regenerating clips
```
The finished files are in **`output\`**. The raw AI clips stay in `clips\`.

Useful options: `--resolution 720x1280` overrides the template resolution, `--wangp-python PATH` points to WanGP's Python if auto-detect fails, and `--font C:/Windows/Fonts/Nirmala.ttc` gives a font that supports Telugu and Hindi text.

## Upload tips
- Instagram Reels: 9:16, up to 90 s. YouTube Shorts: 9:16, up to 60 s for the Shorts shelf.
- Keep important text out of the bottom 20% and the right edge, where the app buttons sit.
- Add `#Shorts` to the YouTube title or description.
