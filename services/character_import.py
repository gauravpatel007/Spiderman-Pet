"""Transactional local character imports with artwork-specific animation clips."""
import json
import math
import re
import shutil
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps
from scripts.build_articulated_assets import pose


def load_artwork(path):
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert('RGBA')
    image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    # Remove only white connected to an outer edge; retain enclosed white lenses.
    if image.getchannel('A').getextrema()[0] == 255:
        white = image.convert('RGB').convert('L').point(lambda p: 255 if p > 235 else 0)
        mask = Image.new('L', (image.width+2, image.height+2), 255)
        mask.paste(white, (1, 1))
        ImageDraw.floodfill(mask, (0, 0), 128)
        background = mask.crop((1, 1, image.width+1, image.height+1)).point(lambda p: 255 if p == 128 else 0)
        image.putalpha(ImageChops.subtract(image.getchannel('A'), background))
    box = image.getchannel('A').getbbox()
    if not box:
        raise ValueError('Artwork is empty after background removal. Use a transparent character PNG.')
    image = image.crop(box)
    image.thumbnail((400, 440), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (512, 512))
    canvas.alpha_composite(image, ((512-image.width)//2, 492-image.height))
    return canvas


def build_artwork_clips(root, artwork, template):
    """Use a conservative cutout rig; never substitute template character pixels."""
    source = load_artwork(artwork)
    (root/'sprites').mkdir(exist_ok=True)
    source.save(root/'sprites'/'idle.png')
    x0, y0, x1, y1 = source.getbbox()
    w, h = x1-x0, y1-y0
    head = round(y0+h*.43)
    hip = round(y0+h*.73)
    left, right, center = round(x0+w*.28), round(x0+w*.72), round((x0+x1)/2)
    rectangles = {
        'head': (x0, y0, x1, head),
        'torso': (left, head, right, hip),
        'arm_left': (x0, head, left, hip), 'arm_right': (right, head, x1, hip),
        'leg_left': (x0, hip, center, y1), 'leg_right': (center, hip, x1, y1),
    }
    parts, rig = {}, {'eyes': [], 'lid': '#202329'}
    for name, box in rectangles.items():
        layer = Image.new('RGBA', source.size)
        layer.paste(source.crop(box), box[:2])
        parts[name] = layer
        pivot = [center, head] if name == 'head' else [(box[0]+box[2])/2, box[1]+4]
        rig[name] = {'pivot': pivot}
    manifest = {'version': 1, 'canvas': [512, 512], 'anchor': [256, 488],
                'method': 'procedural imported cutout', 'animations': {}}
    specs = {'idle': (24,12,True), 'walk': (24,24,True), 'run': (16,24,True),
             'sleep': (24,8,True), 'wake_up': (18,12,False), 'sit': (24,12,True),
             'stand_up': (12,12,False), 'wave': (24,16,False), 'dance': (48,16,False),
             'celebrate': (32,16,False), 'dragged': (24,12,True)}
    other = {'jump': 'run', 'fall': 'dragged', 'land': 'sit', 'climb_up': 'walk',
             'climb_down': 'walk', 'wall_slide': 'dragged', 'perch': 'sit',
             'swing': 'dragged', 'hang': 'dragged', 'interact': 'wave'}
    for name in template['supported_animations']:
        count, fps, loop = specs.get(name, (12,12,name not in ('jump','land','interact')))
        folder = root/'generated'/name
        folder.mkdir(parents=True, exist_ok=True)
        frames = []
        for i in range(count):
            frame = pose(parts, rig, 2*math.pi*i/count, other.get(name,name), i/max(1,count-1))
            relative = f'generated/{name}/frame_{i:02d}.png'
            frame.save(root/relative)
            frames.append(relative)
            if name == 'idle' and i == 0:
                frame.save(root/'preview.png')
        manifest['animations'][name] = dict(frames=frames, fps=fps, loop=loop, mirror_allowed=True)
    (root/'animation_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return list(manifest['animations'])


def create_character(destination_root, template_root, cid, name, suit, artwork=None):
    if not re.fullmatch(r'[a-z0-9_]+', cid) or cid in ('con','prn','aux','nul') or re.fullmatch(r'(com|lpt)[0-9]', cid):
        raise ValueError('Choose a valid character identifier (letters, numbers and underscores).')
    destination_root, template_root = Path(destination_root), Path(template_root)
    target = destination_root/cid
    if target.exists():
        raise ValueError('This character identifier already exists. Choose another.')
    template = json.loads((template_root/'character.json').read_text(encoding='utf-8'))
    destination_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.import-', dir=destination_root))
    try:
        if artwork:
            supported = build_artwork_clips(stage, artwork, template)
        else:
            for child in template_root.iterdir():
                if child.is_dir():
                    shutil.copytree(child, stage/child.name)
                elif child.name != 'character.json':
                    shutil.copy2(child, stage/child.name)
            supported = template['supported_animations']
        data = dict(template, id=cid, name=name, display_name=name, suit=suit,
                    personality=template.get('personality', template['id']),
                    supported_animations=supported, custom_character=True,
                    animation_source='imported_artwork' if artwork else 'template_copy')
        (stage/'character.json').write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        stage.rename(target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return target
