"""Make chronological reference sheets without copying source video files.

The sheets support visual review; decoding and making a sheet does not itself
certify a sign, or imply continuous viewing of every source video frame.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

cv2.setNumThreads(1)
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bank', type=Path, default=ROOT / 'assets/motions/manifest.json',
                        help='Use the motion bank medoid, so visual review matches the animation timebase.')
    args = parser.parse_args()
    words = json.loads(args.manifest.read_text('utf8'))['words']
    bank = {e['id']: e for e in json.loads(args.bank.read_text('utf8'))['entries']}
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 20)
    small = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 14)
    args.output.mkdir(parents=True, exist_ok=True)
    inventory = {'schema': 'clinic-source-sheet-inventory-v2',
                 'scope': 'Twelve chronological upper-body samples from each motion medoid; visual review recorded separately.',
                 'bank_sha256': hashlib.sha256(args.bank.read_bytes()).hexdigest(), 'words': []}
    for i, word in enumerate(words):
        medoid = bank.get(word['id'], {}).get('medoid_id')
        row = next((r for r in word['references'] if r['video_id'] == medoid), None)
        if row is None:
            raise ValueError(f"{word['id']}: motion medoid {medoid!r} has no source reference")
        source = Path(row['path'])
        if hashlib.sha256(source.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Source changed: ' + str(source))
        cap = cv2.VideoCapture(str(source))
        fps, count = cap.get(cv2.CAP_PROP_FPS), cap.get(cv2.CAP_PROP_FRAME_COUNT)
        window = row.get('source_window_ms', [0, (count - 1) / fps * 1000])
        sheet = Image.new('RGB', (1120, 880), '#f5f6f3')
        draw = ImageDraw.Draw(sheet)
        draw.text((12, 7), f"{word['id']} · {word['label']} · {row['video_id']}", font=font, fill='#163d32')
        stamps=np.linspace(*window,14)[1:-1]
        picks=np.rint(stamps*fps/1000).astype(int)
        selected={};frame_index=0
        while frame_index <= picks[-1]:
            ok, frame = cap.read()
            if not ok:
                raise ValueError('Decode failed: ' + str(source))
            if frame_index in picks:selected[frame_index]=frame
            frame_index+=1
        for tile,(t,frame_index) in enumerate(zip(stamps,picks)):
            frame=selected[frame_index]
            h, w = frame.shape[:2]
            # Include both elbows and the lower hand space. The square local
            # recordings are already tight; do not infer an anatomical crop.
            frame = frame[int(h * .05):int(h * .88), int(w * .05):int(w * .95)]
            im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            im.thumbnail((276, 256))
            x, y = tile % 4 * 280, 38 + tile // 4 * 280
            sheet.paste(im, (x + (280-im.width)//2, y))
            draw.text((x+7, y+257), f'{t/1000:.2f}s', font=small, fill='#254337')
        cap.release()
        target = args.output / (word['id'] + '.jpg')
        sheet.save(target, quality=91)
        inventory['words'].append({'id': word['id'], 'label': word['label'], 'source_id': row['video_id'],
                                   'selection': 'motion-medoid', 'path': str(source), 'sha256': row['sha256'],
                                   'source_window_ms': window, 'sample_times_ms': stamps.tolist(),
                                   'sheet': str(target), 'visual_review': 'pending'})
        print(f"SHEET {i+1}/{len(words)} {word['label']}", flush=True)
    (args.output / 'inventory.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), 'utf8')


if __name__ == '__main__':
    main()
