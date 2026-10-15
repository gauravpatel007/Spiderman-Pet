from PIL import Image, ImageDraw

from scripts.audit_character_assets import inspect_sequence


def test_translation_is_not_articulation(tmp_path):
    for i in range(3):
        frame = Image.new("RGBA", (512, 512))
        ImageDraw.Draw(frame).rectangle((100, 100 + i, 200, 200 + i), fill="red")
        frame.save(tmp_path / f"{i}.png")
    report = inspect_sequence(tmp_path)
    assert report["frame_count"] == 3
    assert report["distinct_cropped_poses"] == 1
    assert report["problems"]


def test_pose_variation_passes_technical_gate(tmp_path):
    for i in range(3):
        frame = Image.new("RGBA", (512, 512))
        ImageDraw.Draw(frame).rectangle((100, 100, 200 + i, 200), fill="red")
        frame.save(tmp_path / f"{i}.png")
    report = inspect_sequence(tmp_path)
    assert report["distinct_cropped_poses"] == 3
    assert not report["problems"]
