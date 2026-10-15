"""Build additional cutout clips and original synthesized WAV cues locally."""
import json
import math
import struct
import wave
from PIL import Image
from build_articulated_assets import ROOT, RIGS, pose


def main():
    for character in RIGS:
        root = ROOT/'characters'/character
        rig = json.loads((root/'rig/rig.json').read_text())
        parts = {name: Image.open(root/'rig'/f'{name}.png').convert('RGBA')
                 for name, entry in rig.items() if isinstance(entry, dict)}
        manifest = json.loads((root/'animation_manifest.json').read_text())
        specs = {'dance': (48, 16, False), 'celebrate': (32, 16, False),
                 'dragged': (24, 12, True)}
        for state, (count, fps, loop) in specs.items():
            folder = root/'animations'/state
            folder.mkdir(parents=True, exist_ok=True)
            frames = []
            for i in range(count):
                path = f'animations/{state}/frame_{i:02d}.png'
                pose(parts, rig, 4*math.pi*i/count, state, i/(count-1)).save(root/path)
                frames.append(path)
            manifest['animations'][state] = dict(fps=fps, loop=loop,
                mirror_allowed=True, anchor=[256,488], frames=frames,
                source='rig/rig.json')
        (root/'animation_manifest.json').write_text(json.dumps(manifest, indent=2))
        profile = json.loads((root/'character.json').read_text(encoding='utf-8'))
        profile['supported_animations'] = list(dict.fromkeys(profile['supported_animations']+list(specs)))
        (root/'character.json').write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'{character}: built dance, celebration and dragging clips')
    folder = ROOT/'assets'/'sounds'
    folder.mkdir(parents=True, exist_ok=True)
    for name, start, end, duration in [('jump',300,850,.18), ('swing',1200,240,.24),
                                      ('land',180,60,.12), ('sleep',240,180,.45),
                                      ('reaction',520,780,.22)]:
        rate = 22050
        samples = bytearray()
        phase = 0.0
        for i in range(round(rate*duration)):
            t = i/rate/duration
            phase += 2*math.pi*(start+(end-start)*t)/rate
            value = int(7000*math.sin(math.pi*t)**2*math.sin(phase))
            samples.extend(struct.pack('<h', value))
        with wave.open(str(folder/f'{name}.wav'), 'wb') as output:
            output.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
            output.writeframes(samples)


if __name__ == '__main__':
    main()
