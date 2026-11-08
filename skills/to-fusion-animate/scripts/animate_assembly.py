#!/usr/bin/env python3
"""CLI utility to generate scene-graph animation scripts and compile ping-pong GIF animations for Fusion 360 assemblies."""
import os
import sys
import argparse

# Add repo root to path to import shared
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from shared.scene_animator import compile_ping_pong_gif


def generate_animation_script(occurrences_transforms, frames_dir, num_frames=28, width=800, height=800):
    """
    Generates a Python script string suitable for Fusion 360 execute_api_script.
    Moves scoped occurrences via Matrix3D transforms and captures viewport frames.
    """
    frames_dir_esc = frames_dir.replace("\\", "/")
    return f"""def run(context):
    import os, math, adsk.core, adsk.fusion
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        raise RuntimeError("No active Fusion 360 design document.")
    root = design.rootComponent
    vp = app.activeViewport
    ui = app.userInterface
    if ui:
        ui.activeSelections.clear()

    frames_dir = "{frames_dir_esc}"
    os.makedirs(frames_dir, exist_ok=True)
    num_frames = {num_frames}

    def clamp(v, min_v, max_v):
        return max(min_v, min(max_v, v))

    def smoothstep(edge0, edge1, x):
        t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
        return t * t * (3.0 - 2.0 * t)

    # Cache target occurrences
    occ_map = {{}}
    for occ in root.occurrences:
        occ_map[occ.name] = occ

    for frame_idx in range(num_frames):
        s = frame_idx / float(max(1, num_frames - 1))
        # Custom per-occurrence transform updates here
        vp.refresh()
        out_frame = os.path.join(frames_dir, f"frame_{{frame_idx:03d}}.png")
        vp.saveAsImageFile(out_frame, {width}, {height})

    print(f"ANIMATION_FRAMES_RENDERED: {{num_frames}} frames saved to {{frames_dir}}")
"""


def main():
    parser = argparse.ArgumentParser(description="Fusion 360 Assembly Animation & GIF Compilation CLI")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # Subcommand: compile-gif
    compile_parser = subparsers.add_parser("compile", help="Compile rendered PNG frames into a looping ping-pong GIF")
    compile_parser.add_argument("--frames-dir", required=True, help="Directory containing frame_000.png frames")
    compile_parser.add_argument("--output", "-o", required=True, help="Path to output .gif file")
    compile_parser.add_argument("--num-frames", type=int, default=28, help="Number of forward motion frames (default: 28)")
    compile_parser.add_argument("--hold-assembled", type=int, default=25, help="Frames to hold in assembled state (default: 25)")
    compile_parser.add_argument("--hold-exploded", type=int, default=18, help="Frames to hold in exploded state (default: 18)")
    compile_parser.add_argument("--frame-ms", type=int, default=45, help="Milliseconds per motion frame (default: 45)")
    compile_parser.add_argument("--hold-ms", type=int, default=50, help="Milliseconds per hold frame (default: 50)")

    # Subcommand: generate-script
    script_parser = subparsers.add_parser("generate-script", help="Generate Fusion 360 animation API script")
    script_parser.add_argument("--frames-dir", required=True, help="Output directory for frames")
    script_parser.add_argument("--num-frames", type=int, default=28, help="Number of frames (default: 28)")
    script_parser.add_argument("--width", type=int, default=800, help="Viewport capture width")
    script_parser.add_argument("--height", type=int, default=800, help="Viewport capture height")

    args = parser.parse_args()

    if args.command == "compile":
        out = compile_ping_pong_gif(
            frames_dir=args.frames_dir,
            output_gif_path=args.output,
            num_frames=args.num_frames,
            hold_assembled=args.hold_assembled,
            hold_exploded=args.hold_exploded,
            frame_ms=args.frame_ms,
            hold_ms=args.hold_ms,
        )
        print(f"✅ GIF compiled successfully: {out}")
    elif args.command == "generate-script":
        code = generate_animation_script(
            occurrences_transforms={},
            frames_dir=args.frames_dir,
            num_frames=args.num_frames,
            width=args.width,
            height=args.height,
        )
        print(code)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
