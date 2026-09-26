import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=False)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--subtitle", default=None)
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is required")
    source = Path(args.input)
    output = Path(args.output)
    if not source.exists():
        raise SystemExit(f"Input does not exist: {source}")
    if args.duration <= 0 or args.duration > 180:
        raise SystemExit("duration must be between 0 and 180 seconds")

    # Vertical 9:16, centered crop. The factory can later replace this
    # base recipe with learned per-creator recipes.
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    if args.subtitle:
        subtitle = Path(args.subtitle)
        if not subtitle.exists():
            raise SystemExit(f"Subtitle file does not exist: {subtitle}")
        subtitle_filter = subtitle.as_posix().replace(":", "\\\\:")
        vf += f",subtitles={subtitle_filter}"

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(args.start),
        "-i", str(source),
        "-t", str(args.duration),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "21",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output),
    ]
    result = run(cmd)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit(result.returncode)

    print(f"Rendered: {output}")

if __name__ == "__main__":
    main()
