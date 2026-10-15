"""Phase 2 technical gate: detect missing or translation-only pose sequences.

This audit can reject insufficient assets; it cannot certify visual quality or
natural articulation. Those require reviewing the animations themselves.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def inspect_sequence(directory):
    frames = sorted(directory.glob("*.png")) + sorted(directory.glob("*.webp"))
    fingerprints = set()
    sizes = set()
    problems = []
    for path in frames:
        with Image.open(path) as image:
            if image.mode != "RGBA":
                problems.append(f"{path.name}: missing RGBA alpha")
            frame = image.convert("RGBA")
            sizes.add(frame.size)
            alpha = frame.getchannel("A")
            box = alpha.getbbox()
            if box is None:
                problems.append(f"{path.name}: empty frame")
                continue
            if alpha.getextrema()[0] != 0:
                problems.append(f"{path.name}: background is not transparent")
            # Cropping removes whole-body translation: bobbing one still image
            # must not pass as a genuine walking cycle.
            cropped = frame.crop(box)
            fingerprints.add(hashlib.sha256(str(cropped.size).encode() + cropped.tobytes()).hexdigest())
    if not frames:
        problems.append("No frames supplied")
    if len(sizes) > 1:
        problems.append("Inconsistent frame dimensions")
    if any(w < 512 or h < 512 for w, h in sizes):
        problems.append("Source resolution is below 512px")
    if len(frames) < 2:
        problems.append("Only a static pose; an animated sequence is required")
    if len(fingerprints) < 2:
        problems.append("No pose variation after removing whole-image translation")
    return {"frame_count": len(frames), "distinct_cropped_poses": len(fingerprints),
            "dimensions": sorted(sizes), "problems": problems}


def audit(root=ROOT):
    result = {"phase": 2, "technical_gate_passed": True,
              "visual_review_required": True, "characters": {}}
    for character in ("miles_morales", "tom_holland"):
        result["characters"][character] = {}
        for state in ("idle", "walk", "sleep"):
            record = inspect_sequence(root / "characters" / character / "animations" / state)
            result["characters"][character][state] = record
            if record["problems"]:
                result["technical_gate_passed"] = False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "phase2_asset_audit.json")
    args = parser.parse_args()
    report = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["technical_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
