"""Assemble Blender frames or check a ready-to-import MOSS sprite sheet."""
import argparse
import hashlib
import json
import logging
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
CELL = (192, 208)
COUNTS = (6, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8)
SIZE = (1536, 2288)
MAX_BYTES = 20 * 1024 * 1024
LOGGER = logging.getLogger(__name__)


def cell_box(row, col):
    """Return the fixed pixel rectangle for one client cell."""
    return (col * CELL[0], row * CELL[1], (col + 1) * CELL[0], (row + 1) * CELL[1])


def verify_atlas(path):
    """Check encoding, occupied cells, unused cells and cell-edge clipping."""
    with Image.open(path) as source:
        if source.format not in ('PNG', 'WEBP') or source.size != SIZE:
            raise ValueError('Expected a 1536x2288 PNG or WebP')
        atlas = source.convert('RGBA')
    if not 0 < path.stat().st_size <= MAX_BYTES:
        raise ValueError('Encoded file exceeds 20 MiB or is empty')
    for row, count in enumerate(COUNTS):
        for col in range(8):
            alpha = atlas.crop(cell_box(row, col)).getchannel('A')
            bounds = alpha.getbbox()
            if col >= count and bounds is not None:
                raise ValueError(f'Unused cell is not transparent: {row}:{col}')
            if col < count:
                if bounds is None:
                    raise ValueError(f'Missing cell: {row}:{col}')
                if not (0 < bounds[0] < bounds[2] < CELL[0] and 0 < bounds[1] < bounds[3] < CELL[1]):
                    raise ValueError(f'Visible pixels touch cell edge: {row}:{col}')
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size,
            'size': list(SIZE), 'used_cells': sum(COUNTS), 'empty_cells': 15,
            'structure_ok': True, 'visual_or_client_acceptance': False}


def clean_frame(path):
    """Apply a shared scale and clear invisible RGB, without per-frame recentering."""
    frame = Image.open(path).convert('RGBA').resize(CELL, Image.Resampling.LANCZOS)
    pixels = [(0, 0, 0, 0) if pixel[3] == 0 else pixel for pixel in frame.getdata()]
    frame.putdata(pixels)
    return frame


def assemble(frames, base, output):
    """Replace rendered cells; preserve other cells exactly when a base is supplied."""
    manifest = json.loads((frames / 'render.json').read_text(encoding='utf8'))
    if base:
        verify_atlas(base)
        atlas = Image.open(base).convert('RGBA')
    else:
        atlas = Image.new('RGBA', SIZE)
    seen = set()
    for item in manifest['frames']:
        row, col = item['row'], item['col']
        if row not in range(11) or col not in range(COUNTS[row]) or (row, col) in seen:
            raise ValueError(f'Invalid or repeated rendered cell: {row}:{col}')
        seen.add((row, col))
        atlas.paste(clean_frame(frames / item['file']), cell_box(row, col)[:2])
    if not base and len(seen) != sum(COUNTS):
        raise ValueError('Partial render requires --base MOSS.png')
    output.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(output)
    report = verify_atlas(output)
    report['changed_cells'] = sorted(seen)
    output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    return atlas


def previews(atlas, output):
    """Save a labeled contact sheet and native-size loops for all nine states."""
    config = json.loads((ROOT / 'config/animation.json').read_text(encoding='utf8'))
    contact = Image.new('RGB', (SIZE[0], 11 * 232), '#eaf0f5')
    draw = ImageDraw.Draw(contact)
    for row, count in enumerate(COUNTS):
        images = []
        for col in range(count):
            frame = atlas.crop(cell_box(row, col))
            contact.paste(frame, (col * CELL[0], row * 232 + 24), frame)
            draw.text((col * CELL[0] + 4, row * 232 + 4), f'{row}:{col}', fill='#202934')
            canvas = Image.new('RGB', CELL, '#eaf0f5')
            canvas.paste(frame, (0, 0), frame)
            images.append(canvas)
        if row < 9:
            images[0].save(output.parent / f'state-{row}.gif', save_all=True, append_images=images[1:],
                           duration=config['rows'][row]['durations_ms'], loop=0, disposal=2)
    contact.save(output.parent / 'contact.png')


def main():
    """Validate an existing release or assemble and preview a customization."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=Path, default=ROOT / 'build/frames')
    parser.add_argument('--base', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT / 'build/MOSS-custom.png')
    parser.add_argument('--check', type=Path)
    args = parser.parse_args()
    if args.check:
        LOGGER.info('%s', json.dumps(verify_atlas(args.check)))
        return
    atlas = assemble(args.frames, args.base, args.out)
    previews(atlas, args.out)
    LOGGER.info('Created %s', args.out)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
