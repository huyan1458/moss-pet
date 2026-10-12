"""Build README demonstrations from the published atlas without changing its poses."""
import argparse
import json
import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from assemble_atlas import CELL, ROOT, cell_box, verify_atlas

BACKGROUND = '#edf1f5'
INK = '#172432'
MUTED = '#607184'
CARD = (384, 488)
LOGGER = logging.getLogger(__name__)


def font(size):
    """Use an available UI font, with Pillow's bundled font as fallback."""
    for name in ('arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def card(atlas, slot, title, detail):
    """Show a fixed atlas cell at 2x size with a descriptive caption."""
    canvas = Image.new('RGB', CARD, BACKGROUND)
    frame = atlas.crop(cell_box(*slot)).resize((CELL[0] * 2, CELL[1] * 2), Image.Resampling.NEAREST)
    canvas.paste(frame, (0, 12), frame)
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 430), title, font=font(22), fill=INK)
    draw.text((24, 460), detail, font=font(14), fill=MUTED)
    return canvas


def row_sequence(config, row, cycles=1):
    """Return cell coordinates and observed frame durations for one state."""
    return [((row, col), duration) for _ in range(cycles)
            for col, duration in enumerate(config['rows'][row]['durations_ms'])]


def demonstrations(config):
    """Define faithful loops and explicitly labeled pose comparisons."""
    idle_hold = [((0, 0), 1000)]
    sequences = {
        'idle': ('IDLE', 'Slow yaw + status indicator', row_sequence(config, 0)),
        'hover': ('HOVER', '3 cycles, then return to idle',
                  idle_hold + row_sequence(config, 4, 3) + idle_hold),
        'drag': ('TRANSPORT', 'Same pose for left / right drag',
                 idle_hold + row_sequence(config, 1, 3) + idle_hold),
        'greeting': ('GREETING', 'Small yaw + indicator response', row_sequence(config, 3)),
        'failed': ('FAILED', 'Status indicator pulse', row_sequence(config, 5)),
        'waiting': ('WAITING', 'Status indicator hold / dim', row_sequence(config, 6)),
        'working': ('WORKING', 'Status indicator alternation', row_sequence(config, 7)),
        'review': ('REVIEW', 'Status indicator fade steps', row_sequence(config, 8)),
        'scan': ('INPUT ATTENTION', 'Pose comparison; timing is illustrative',
                 idle_hold + [((9, 5), 2400)] + idle_hold),
        'look-directions': ('LOOK SLOTS', '16 static slots; illustrative sequence',
                            [((row, col), 500) for row in (9, 10) for col in range(8)]),
    }
    return sequences


def save_gif(frames, durations, destination):
    """Save a looping display GIF while retaining each scheduled duration."""
    frames[0].save(destination, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, disposal=2, optimize=False)


def make_showcase(atlas, sequences, output):
    """Combine idle, hover and scan pose demonstrations into a README banner."""
    keys = ('idle', 'hover', 'scan')
    length = sum(duration for _, duration in sequences['idle'][2])
    interval = 20
    frames = []
    for timestamp in range(0, length, interval):
        banner = Image.new('RGB', (CARD[0] * len(keys), CARD[1]), BACKGROUND)
        for index, key in enumerate(keys):
            title, detail, sequence = sequences[key]
            elapsed = timestamp % sum(duration for _, duration in sequence)
            for slot, duration in sequence:
                if elapsed < duration:
                    break
                elapsed -= duration
            banner.paste(card(atlas, slot, title, detail), (CARD[0] * index, 0))
        frames.append(banner)
    save_gif(frames, [interval] * len(frames), output / 'idle-hover.gif')


def main():
    """Generate display GIFs from a validated atlas."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--atlas', type=Path, default=ROOT / 'MOSS.png')
    parser.add_argument('--out', type=Path, default=ROOT / 'assets/previews')
    args = parser.parse_args()
    verify_atlas(args.atlas)
    atlas = Image.open(args.atlas).convert('RGBA')
    config = json.loads((ROOT / 'config/animation.json').read_text(encoding='utf8'))
    args.out.mkdir(parents=True, exist_ok=True)
    sequences = demonstrations(config)
    for name, (title, detail, sequence) in sequences.items():
        frames = [card(atlas, slot, title, detail) for slot, _ in sequence]
        save_gif(frames, [duration for _, duration in sequence], args.out / f'{name}.gif')
    make_showcase(atlas, sequences, args.out)
    LOGGER.info('Generated %s GIFs in %s', len(sequences) + 1, args.out)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
