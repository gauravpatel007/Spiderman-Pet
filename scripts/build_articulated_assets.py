"""Author local cutout rigs and articulated sprite sequences from existing art.
No model, API, network, or third-party asset download is used.
"""
import json
import math
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SIZE = (512, 512)
RIGS = {
    'miles_morales': {
        'head': {'pivot': [258, 327], 'polygon': [[105, 15], [410, 15], [410, 310], [307, 343], [215, 343], [105, 296]]},
        'torso': {'pivot': [266, 381], 'polygon': [[223, 321], [306, 321], [325, 383], [294, 410], [223, 395]]},
        'arm_right': {'pivot': [308, 350], 'polygon': [[299, 319], [398, 305], [403, 392], [320, 396], [295, 369]]},
        'leg_left': {'pivot': [244, 391], 'polygon': [[225, 369], [274, 398], [236, 429], [201, 475], [199, 494], [103, 494], [107, 456], [159, 435], [176, 400]]},
        'leg_right': {'pivot': [290, 392], 'polygon': [[269, 388], [316, 372], [365, 403], [365, 432], [349, 443], [375, 495], [296, 499], [292, 452], [312, 424], [270, 416]]},
        'eyes': [[132, 171, 244, 300], [269, 166, 388, 299]],
        'lid': '#202329',
    },
    'tom_holland': {
        'head': {'pivot': [266, 205], 'polygon': [[184, 14], [378, 14], [381, 190], [295, 218], [232, 214], [182, 167]]},
        'torso': {'pivot': [267, 319], 'polygon': [[206, 192], [239, 201], [286, 202], [325, 231], [312, 273], [307, 320], [276, 346], [223, 324], [209, 251]]},
        'arm_left': {'pivot': [212, 215], 'polygon': [[128, 85], [198, 85], [193, 177], [230, 197], [230, 238], [188, 235], [131, 206]]},
        'arm_right': {'pivot': [317, 247], 'polygon': [[312, 232], [380, 246], [381, 295], [342, 332], [301, 326], [299, 293], [326, 293], [339, 273], [309, 273]]},
        'leg_left': {'pivot': [248, 331], 'polygon': [[221, 311], [273, 329], [261, 365], [230, 424], [210, 461], [211, 496], [146, 498], [149, 459], [183, 431], [199, 382]]},
        'leg_right': {'pivot': [291, 334], 'polygon': [[270, 325], [309, 312], [330, 373], [340, 420], [356, 454], [381, 467], [381, 495], [320, 494], [308, 443], [292, 390], [269, 367]]},
        'eyes': [[218, 88, 276, 146], [302, 123, 350, 169]],
        'lid': '#9b2632',
    },
}


def layer(source, polygon):
    mask = Image.new('L', SIZE)
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(.5))
    out = source.copy()
    out.putalpha(ImageChops.multiply(source.getchannel('A'), mask))
    return out


def transform(image, pivot, angle=0, dx=0, dy=0, scale_y=1):
    # Inverse affine mapping around the joint keeps each cutout attached.
    theta = math.radians(angle)
    c, s = math.cos(theta), math.sin(theta)
    px, py = pivot
    a, b, d, e = c, s, -s / scale_y, c / scale_y
    return image.transform(SIZE, Image.Transform.AFFINE,
        (a, b, px-a*(px+dx)-b*(py+dy), d, e, py-d*(px+dx)-e*(py+dy)),
        resample=Image.Resampling.BICUBIC)


def sleepy_head(head, rig, amount):
    if amount <= 0:
        return head
    out = head.copy()
    for x1, y1, x2, y2 in rig['eyes']:
        region = head.crop((x1,y1,x2,y2))
        # Limit eyelids to the original bright lens; preserve suit and eye rims.
        lens = Image.new('L', region.size)
        lens.putdata([255 if min(r,g,b)>100 and max(r,g,b)-min(r,g,b)<70 and a>200 else 0
                      for r,g,b,a in region.getdata()])
        lens = lens.filter(ImageFilter.GaussianBlur(.7))
        cover = Image.new('L', region.size)
        edge = round(region.height * amount * .85)
        ImageDraw.Draw(cover).rectangle((0,0,region.width,edge), fill=255)
        cover = ImageChops.multiply(lens, cover)
        color = Image.new('RGBA', region.size, rig['lid'])
        color.putalpha(cover)
        out.alpha_composite(color, (x1,y1))
    return out


def pose(parts, rig, phase, state, progress):
    sin = math.sin(phase)
    arms, legs, head_angle, body_y, breath = {}, {}, 0, 0, 1
    closed = 0
    if state == 'idle':
        breath = 1 + .012 * sin
        head_angle = 1.5 * math.sin(phase / 1)
        arms = {'arm_right': 2*sin, 'arm_left': -2*sin}
    elif state in ('walk','run'):
        stride = 13 if state == 'walk' else 23
        legs = {'leg_left': stride*sin, 'leg_right': -stride*sin}
        arms = {'arm_left': -stride*.65*sin, 'arm_right': stride*.7*sin}
        body_y = -3*abs(sin) if state == 'walk' else -7*abs(sin)
        head_angle = -2*sin
    elif state in ('sleep','wake_up'):
        closed = 1 if state == 'sleep' else 1-progress
        breath = 1 + .025 * sin
        head_angle = 9 + 1.5*sin
        legs = {'leg_left': -18, 'leg_right': 22}
        arms = {'arm_left': -35, 'arm_right': 15}
    elif state in ('sit','stand_up'):
        amount = 1 if state == 'sit' else 1-progress
        legs = {'leg_left': -25*amount, 'leg_right': 30*amount}
        arms = {'arm_left': -20*amount, 'arm_right': 6*sin}
        body_y = 8*amount
        head_angle = 3*sin
    elif state in ('dance', 'celebrate'):
        arms = {'arm_left': -35+28*sin, 'arm_right': -45-28*sin}
        legs = {'leg_left': 12*sin, 'leg_right': -12*sin}
        body_y = -8*abs(sin)
        head_angle = 7*sin
    elif state == 'dragged':
        arms = {'arm_left': -22, 'arm_right': 20}
        legs = {'leg_left': 12*sin, 'leg_right': -12*sin}
        head_angle = 4*sin
    elif state == 'wave':
        arms = {'arm_left': 10*sin, 'arm_right': -20+16*sin}
        head_angle = 3*sin
    frame = Image.new('RGBA', SIZE)
    # Back limbs first; overlap at hips/shoulders hides joint seams.
    order = ['leg_left','leg_right','arm_left','torso','arm_right','head']
    for name in order:
        if name not in parts:
            continue
        part = parts[name]
        angle = legs.get(name, arms.get(name, head_angle if name=='head' else 0))
        if name == 'head':
            part = sleepy_head(part, rig, closed)
        moved = transform(part, rig[name]['pivot'], angle=angle,
            dy=body_y + (-2*sin if name=='head' else 0),
            scale_y=breath if name=='torso' else 1)
        frame.alpha_composite(moved)
    # Keep a common canvas and reserve room for the whole stride.
    if state in ('sleep','wake_up'):
        amount = 1 if state == 'sleep' else 1-progress
        frame = frame.rotate(78*amount, Image.Resampling.BICUBIC, expand=False)
    # Fixed scale across all clips; only resting poses change their baseline.
    frame = frame.resize((440,440),Image.Resampling.LANCZOS)
    out=Image.new('RGBA',SIZE)
    y=52
    if state in ('sleep','wake_up'):
        amount = 1 if state=='sleep' else 1-progress
        box=frame.getbbox()
        if box:
            y += round((440-box[3])*amount)
    out.alpha_composite(frame,(36,y))
    return out


def build(character, rig):
    root=ROOT/'characters'/character
    source=Image.open(root/'sprites'/'idle.png').convert('RGBA')
    rig_dir=root/'rig'
    rig_dir.mkdir(exist_ok=True)
    parts={name:layer(source, definition['polygon']) for name,definition in rig.items()
           if isinstance(definition,dict)}
    for name,part in parts.items():
        part.save(rig_dir/f'{name}.png')
    (rig_dir/'rig.json').write_text(json.dumps(rig,indent=2))
    specs={'idle':(24,12,True),'walk':(24,24,True),'run':(16,24,True),
           'sleep':(24,8,True),'wake_up':(18,12,False),'sit':(24,12,True),
           'stand_up':(12,12,False),'wave':(24,16,False),
           'dance':(48,16,False),'celebrate':(32,16,False),'dragged':(24,12,True)}
    manifest={'version':1,'canvas':[512,512],'source':'sprites/idle.png',
              'method':'local layered cutout rig','animations':{}}
    previews={}
    for state,(count,fps,loop) in specs.items():
        directory=root/'animations'/state
        directory.mkdir(parents=True,exist_ok=True)
        for old in directory.glob('frame_*.png'):
            old.unlink()
        frames=[]
        for i in range(count):
            frame=pose(parts,rig,2*math.pi*i/count,state,i/max(1,count-1))
            frame.save(directory/f'frame_{i:02d}.png')
            frames.append(frame)
        previews[state]=frames
        manifest['animations'][state]={'fps':fps,'loop':loop,'direction':'right',
            'mirror_allowed':True,'anchor':[256,488],
            'frames':[f'animations/{state}/frame_{i:02d}.png' for i in range(count)],
            'offsets':[[0,0] for _ in frames],'source':'rig/rig.json'}
    # Keep all three existing source poses; use the rig idle on selection cards.
    previews['idle'][0].save(root/'preview.png')
    profile=json.loads((root/'character.json').read_text(encoding='utf-8'))
    profile['base_size']=[512,512]
    profile['supported_animations']=list(dict.fromkeys(profile['supported_animations']+list(specs)))
    (root/'character.json').write_text(json.dumps(profile,indent=2,ensure_ascii=False),encoding='utf-8')
    (root/'animation_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    # Animated presentation of the actual delivered sequences, no test run.
    boards=[]
    for i in range(24):
        board=Image.new('RGB',(720,270),'#151923')
        draw=ImageDraw.Draw(board)
        for j,state in enumerate(('idle','walk','sleep')):
            thumb=previews[state][i%len(previews[state])].resize((240,240),Image.Resampling.LANCZOS)
            board.paste(thumb,(j*240,0),thumb)
            draw.text((j*240+100,247),state,fill='white')
        boards.append(board)
    destination=ROOT/'build'/f'{character}-phase2.gif'
    boards[0].save(destination,save_all=True,append_images=boards[1:],duration=85,loop=0)
    boards[6].save(ROOT/'build'/f'{character}-phase2.png')
    print(f'{character}: {sum(s[0] for s in specs.values())} articulated frames, {len(specs)} clips, editable rig saved')


def main():
    for character,rig in RIGS.items():
        build(character,rig)


if __name__=='__main__':
    main()
