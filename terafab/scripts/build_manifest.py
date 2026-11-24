#!/usr/bin/env python3
"""Source of truth for the Terafab documentary. Writes project/scene_manifest.json.

Re-running keeps render status/attempts already recorded in the manifest.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "project" / "scene_manifest.json"

STYLE = ("photorealistic cinematic documentary CGI, cool teal and warm amber highlights, "
         "dynamic purposeful camera movement, continuous natural motion, physically plausible, "
         "16:9 widescreen, no text, no captions, no logos, no watermark")
NEGATIVE = ("text, letters, words, captions, subtitles, watermark, logo, brand name, signage text, "
            "static image, still frame, frozen, slideshow, blurry, low quality, distorted, deformed hands, "
            "extra limbs, cartoon, anime, sparks, fire, explosion")

# Each scene: narration, sound design, editor overlay, and two 5-second motion shots (A, B).
SCENES = [
    ("THE OPENING QUESTION",
     "Artificial intelligence is growing faster than the factories that make its chips. So what happens when demand outruns supply?",
     "Deep synthetic bass hit, rising mechanical hum", None,
     ["High aerial night shot of a vast modern metropolis, camera dives forward and down between illuminated skyscrapers, thousands of lit windows, car headlights streaming along streets, light pulses travelling along roads",
      "Fast forward tracking shot into a high-density AI data center corridor, rows of server racks, cooling fans spinning, blue and amber LED indicators flickering, camera pushes forward steadily"]),
    ("THE BOTTLENECK",
     "Every robot, self-driving system, and AI server needs silicon. But advanced chips are among humanity's hardest products to manufacture.",
     "Rhythmic machine ticks, glassy chime", None,
     ["Smooth lateral dolly through an industrial semiconductor factory, camera weaves between precision machines, robotic overhead carriers move sealed wafer pods along rails, transfer arms actively moving",
      "Close-up of a polished silicon wafer rotating on a motorized precision stage inside an automated tool, reflections of light sweep across its mirror surface, a robotic arm retracts, cleanroom lighting"]),
    ("INTRODUCING TERAFAB",
     "Enter Terafab: a proposed giant chipmaking project backed by Tesla and SpaceX, built around one ambitious idea. Scale.",
     "Wind, distant construction, swelling strings", "TERAFAB — CONCEPT VISUALIZATION",
     ["Aerial drone flyover revealing a vast futuristic semiconductor manufacturing campus in flat Texas landscape emerging from morning fog and low clouds, warm sunrise, enormous interconnected white buildings, conceptual architectural visualization",
      "Aerial orbit over a huge chip factory construction site at sunrise, tall construction cranes rotating, trucks driving on site roads, dust drifting, clouds moving, conceptual architectural visualization"]),
    ("WHY NOW?",
     "The bet is simple. If computing becomes the engine of everything, controlling more chip production could change the race.",
     "Server fan whoosh, low pulse", None,
     ["Steadicam moves quickly through a working AI data center, endless rows of dense server racks receding into the distance, a technician walks and inspects equipment, cooling fans visibly spinning",
      "Low angle tracking shot along server rack doors, subtle translucent visualization of cool airflow streaming through the racks, blinking status lights, camera glides sideways"]),
    ("THE RAW MATERIAL",
     "The journey begins with silicon, refined into extremely pure crystals, then sliced into almost impossibly precise wafers.",
     "Fine saw whine, soft metallic resonance", None,
     ["Extreme macro moving shot of a large cylindrical monocrystalline silicon ingot slowly rotating in an industrial wafer production machine, precision wire saw guides moving, metallic grey surface reflections",
      "Macro shot of thin mirror-polished silicon wafers being lifted one by one by a robotic handler and placed into a wafer cassette, smooth mechanical motion, clean industrial light"]),
    ("THE CLEANROOM",
     "Inside a chip fab, even a tiny particle can ruin a circuit. Cleanrooms protect an astonishingly delicate process.",
     "Air handler hiss, soft footsteps", None,
     ["Continuous steadicam shot walking alongside engineers in white full-body cleanroom suits through a semiconductor fab corridor, they walk naturally, bright even lighting, yellow-tinted lithography bay light in distance",
      "Looking up at automated overhead wafer transport pods gliding quickly along ceiling rails in a large cleanroom, pods stop and lower on hoists to tools, camera tilts and tracks with them"]),
    ("PRINTING CIRCUITS",
     "Lithography transfers intricate patterns onto silicon. Layer after layer, microscopic structures begin to become real computing devices.",
     "Precise servo ticks, deep resonant tone", "MICROSCOPIC PROCESS — VISUALIZATION",
     ["Close-up of a semiconductor lithography machine operating, a wafer stage scans rapidly left and right under a large optical lens assembly, precision actuators adjust, cool light reflects on the wafer",
      "Educational microscopic visualization of a silicon chip cross-section, layered nanoscale structures grow upward step by step, metal interconnect layers forming, camera slowly orbits, scientific style"]),
    ("BEYOND A SINGLE STEP",
     "A finished chip takes many repeated steps: deposition, etching, inspection, and meticulous control of each microscopic layer.",
     "Valve clicks, vacuum pump hum", None,
     ["Inside an advanced semiconductor fab, a robot arm transfers a wafer into a process chamber, chamber door slides shut, mechanical valves operate, faint violet plasma glow through viewport",
      "Precision inspection optics move over a spinning wafer surface, rainbow diffraction shimmering across the wafer, microscope head sweeps, controlled manufacturing choreography"]),
    ("PACKAGING THE POWER",
     "Manufacturing is only part of the challenge. Advanced packaging connects complex chips, memory, and communication pathways into powerful systems.",
     "Tiny mechanical clicks, soft hum", None,
     ["Macro orbiting shot of an advanced semiconductor packaging line, a micro-assembly robot with tiny grippers picks up small chiplets and places them precisely onto a green substrate, shallow depth of field",
      "Close-up of a package alignment system, camera heads and gantries move above substrates with chiplets and memory stacks, conveyor advances, continuous slow orbital camera move"]),
    ("THE DESIGN DREAM",
     "Terafab's vision links chip design, manufacturing, packaging, and testing more closely. Whether it can deliver remains an open question.",
     "Conveyor rumble, scanning beeps", "PROPOSED INTEGRATED WORKFLOW",
     ["Tracking shot following a small semiconductor package carried on an automated conveyor through inspection stations, cameras and lights inspect it, robotic arm moves, futuristic yet plausible production line",
      "Wide tracking shot of an automated chip testing line, packages move between test stations, robotic handlers insert them into test sockets, engineers walking in the background, filmic lighting"]),
    ("ELECTRIC VEHICLES",
     "One possible destination: advanced computing for electric vehicles, where every decision depends on fast, reliable processing.",
     "Electric motor whine, tire hiss", None,
     ["Dynamic tracking shot from a parallel camera car of a sleek unbranded futuristic electric sedan driving fast through a modern closed test track, wheels turning realistically, reflections sliding on bodywork",
      "Close-up moving shot of a generic automotive computer module on a lab test bench, cooling fan spinning, status LEDs blinking, technician hand connects a cable, camera slowly pushes in"]),
    ("ROBOTICS",
     "Another: humanoid robots. Real-world autonomy demands sensing, computation, motion control, and split-second decisions.",
     "Servo whirs, footsteps on concrete", None,
     ["Full-body humanoid industrial robot walks forward with believable weight across a research warehouse floor, smooth tracking camera following beside it, practical laboratory lighting, unbranded robot",
      "Humanoid robot uses articulated hands to pick up a light cardboard box from a shelf, turns its torso and places the box on a table, grounded physics, camera orbits slowly"]),
    ("THE AI DATA CENTER",
     "And then there's AI infrastructure: rooms of machines running models, training systems, and serving millions of requests.",
     "Dense fan roar, electrical hum", None,
     ["Long forward dolly down a wide AI supercomputer data center hallway, countless active cooling fans and blinking LED lights, overhead cable trays, camera glides steadily forward",
      "A technician in safety gear slides a server sled out of a rack and examines it, cables and lights, fans spinning, camera arcs around the technician, documentary realism"]),
    ("A HUGE AMBITION",
     "The proposed scale is extraordinary. But scaling a semiconductor fab takes equipment, skilled teams, reliable yields, and years of execution.",
     "Forklift beeps, crane motors, heavy thuds", None,
     ["Ground-level tracking shot at a large chip factory construction site, forklifts transporting big wooden crates, workers in hard hats and safety vests walking, overhead crane moving slowly",
      "Engineers carefully guide a large piece of semiconductor equipment being installed with a crane inside a new factory building, they check tablets, camera moves past them"]),
    ("THE REAL RISKS",
     "Money alone won't guarantee success. Precision machines, energy, water, talent, and manufacturing yield all determine what is possible.",
     "Tense pulse, keyboard clicks", None,
     ["Handheld moving shot through a semiconductor factory control room, technicians at desks review abstract non-legible charts on screens, one points at a display, monitors glow teal",
      "Technician calibrates a precision machine with tools, panels open, mechanical parts adjust, water pipes and power conduits visible, camera moves around purposefully"]),
    ("THE FUTURE IN SPACE",
     "The boldest longer-term vision goes beyond Earth: specialized chips that could someday support computing in orbit.",
     "Airless hum, soft cosmic swell", "FUTURE CONCEPT — NOT AN EXISTING TERAFAB SYSTEM",
     ["Speculative space visualization, a future orbital computing satellite with large solar arrays slowly unfolding, Earth rotating below with clouds, smooth camera flyby, realistic sunlight",
      "Wide shot of a satellite constellation in low Earth orbit passing over the night side of Earth, city lights below, solar panels glinting, slow camera drift, scientific concept visualization"]),
    ("WHAT'S ACTUALLY CONFIRMED",
     "As of late 2026, Terafab is still a project in development. Its ambitious production targets are plans, not completed milestones.",
     "Single piano note, low drone", "PLANS ≠ COMPLETED PRODUCTION",
     ["Continuous orbital camera movement around a shining silicon wafer held on a clean automated robotic inspection stage, light reflections sweeping across its surface",
      "Aerial shot at dusk of a vast proposed industrial campus under construction, construction vehicles driving, cranes moving, work lights turning on, conceptual architectural visualization"]),
    ("THE FINAL QUESTION",
     "If Terafab succeeds, it could reshape how AI hardware is made. If it doesn't, the challenge remains. What's your prediction?",
     "Bass swell, final hit, silence", "TERAFAB — THE FUTURE OF AI CHIPS?",
     ["Camera pulls back from glowing status lights on a mounted computing board, retreating backward through an active data center aisle with blinking servers and spinning fans",
      "Camera rises and pulls back to a wide night city skyline, alive with moving traffic and glowing windows, atmospheric haze, epic finishing aerial move"]),
]


def build():
    old = {}
    if MANIFEST.exists():
        for s in json.loads(MANIFEST.read_text(encoding="utf-8"))["scenes"]:
            for sh in s["shots"]:
                old[sh["id"]] = sh
    scenes = []
    for i, (title, vo, sfx, overlay, shots) in enumerate(SCENES, 1):
        start = (i - 1) * 10
        sc = {
            "scene": i, "title": title, "start": start, "end": start + 10, "duration": 10,
            "narration": vo, "sound": sfx, "overlay": overlay,
            "narration_audio": f"audio/vo/scene{i:02d}.flac",
            "shots": [],
        }
        for j, p in enumerate(shots):
            sid = f"s{i:02d}{'ab'[j]}"
            sh = {
                "id": sid, "duration": 5,
                "prompt": f"{p}, {STYLE}",
                "negative_prompt": NEGATIVE,
                "seed": 1000 + i * 10 + j,
                "status": "pending", "attempts": [], "output": None,
            }
            if sid in old:  # keep render progress
                for k in ("seed", "status", "attempts", "output", "motion_score", "settings_used"):
                    if k in old[sid]:
                        sh[k] = old[sid][k]
            sc["shots"].append(sh)
        scenes.append(sc)
    data = {
        "title": "TERAFAB — THE FACTORY THAT COULD POWER THE AI FUTURE",
        "runtime_seconds": 180, "delivery": {"width": 1920, "height": 1080, "fps": 30,
                                              "video_codec": "h264", "audio_codec": "aac"},
        "generator": {
            "tool": "WanGP (Wan2GP) headless: wgp.py --process <settings.json>",
            "model_type": "ti2v_2_2", "model": "Wan2.2 TextImage2Video 5B (Apache-2.0 weights)",
            "fallback_ladder": [
                {"model_type": "ti2v_2_2", "resolution": "1280x720", "num_inference_steps": 40},
                {"model_type": "ti2v_2_2", "resolution": "1280x704", "num_inference_steps": 30},
                {"model_type": "ti2v_2_2_fastwan", "resolution": "1280x720", "num_inference_steps": 3},
                {"model_type": "ti2v_2_2_fastwan", "resolution": "960x544", "num_inference_steps": 3},
            ],
            "video_length_frames": 121, "native_fps": 24,
            "plan": "36 x 5-second motion clips edited into 18 x 10-second chapters",
        },
        "scenes": scenes,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {MANIFEST} ({len(scenes)} scenes, {sum(len(s['shots']) for s in scenes)} shots)")


if __name__ == "__main__":
    build()
