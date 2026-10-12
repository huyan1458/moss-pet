"""Render selected client rows from the portable MOSS Blender model."""
import argparse
import json
import logging
import math
import shutil
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rig_validation import snapshot, verify

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)


def arguments():
    """Read arguments placed after Blender's double dash."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, default=ROOT / 'assets/model/MOSS.blend')
    parser.add_argument('--config', type=Path, default=ROOT / 'config/animation.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'build/frames')
    parser.add_argument('--rows', type=int, nargs='+', default=list(range(11)))
    values = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    result = parser.parse_args(values)
    if len(result.rows) != len(set(result.rows)) or any(row not in range(11) for row in result.rows):
        parser.error('--rows must contain distinct integers from 0 to 10')
    return result


def warning_material(lamp):
    """Tint only the separate status light for the two transport rows."""
    surface = lamp.data.materials[0].copy()
    surface.name = 'Transport warning indicator'
    nodes, links = surface.node_tree.nodes, surface.node_tree.links
    texture = next(node for node in nodes if node.type == 'TEX_IMAGE')
    emission = next(node for node in nodes if node.type == 'EMISSION')
    tint = nodes.new('ShaderNodeMixRGB')
    tint.blend_type = 'MULTIPLY'
    tint.inputs[0].default_value = 1
    tint.inputs[2].default_value = (1, .10, .045, 1)
    links.new(texture.outputs['Color'], tint.inputs[1])
    links.new(tint.outputs[0], emission.inputs['Color'])
    return surface


def prepare_scene(config):
    """Resolve controls and ensure joint limits include configured poses."""
    controls = {name: bpy.data.objects[name] for name in
                ['R3_body', 'J5_lower_yaw', 'J3_body_pitch', 'J4_lower_attachment_fold', 'FX_indicator']}
    for name, axis, field in [('J5_lower_yaw', 'z', 'yaw'), ('J3_body_pitch', 'x', 'pitch'),
                              ('J4_lower_attachment_fold', 'y', 'fold')]:
        angles = [pose[field] for row in config['rows'] for pose in row['poses']]
        for constraint in controls[name].constraints:
            if constraint.type == 'LIMIT_ROTATION':
                setattr(constraint, 'min_' + axis, min(getattr(constraint, 'min_' + axis), math.radians(min(angles))))
                setattr(constraint, 'max_' + axis, max(getattr(constraint, 'max_' + axis), math.radians(max(angles))))
    lamp = controls['FX_indicator']
    controls['normal_material'] = lamp.data.materials[0]
    controls['warning_material'] = warning_material(lamp)
    bpy.context.view_layer.update()
    return controls


def set_pose(controls, pose):
    """Set one rigid pose and lamp state without modifying geometry."""
    controls['J5_lower_yaw'].rotation_euler.z = math.radians(pose['yaw'])
    controls['J3_body_pitch'].rotation_euler.x = math.radians(pose['pitch'])
    controls['J4_lower_attachment_fold'].rotation_euler.y = math.radians(pose['fold'])
    controls['R3_body']['indicator_level'] = float(pose['light'])
    controls['R3_body']['scan_level'] = float(pose['scan'])
    surface = 'warning_material' if pose['warning'] else 'normal_material'
    controls['FX_indicator'].data.materials[0] = controls[surface]
    bpy.context.view_layer.update()


def render_frames(config, selection, output, controls):
    """Render exactly the requested rows and save their validation manifest."""
    reference = snapshot()
    report, cache = [], {}
    for row in selection:
        for col, pose in enumerate(config['rows'][row]['poses']):
            set_pose(controls, pose)
            errors = verify(reference)
            filename = f'{row}-{col}.png'
            destination = output / filename
            key = tuple(pose[field] for field in ('yaw', 'pitch', 'fold', 'light', 'scan', 'warning'))
            if key in cache:
                shutil.copy2(cache[key], destination)
            else:
                bpy.context.scene.render.filepath = str(destination)
                bpy.ops.render.render(write_still=True)
                cache[key] = destination
            report.append({'row': row, 'col': col, 'file': filename, 'pose': pose, 'errors': errors})
    result = {'schema': 1, 'rows': selection, 'frames': report,
              'geometry_hashes': reference['geometry'], 'blender_version': bpy.app.version_string}
    (output / 'render.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')


def main():
    """Open the packed model and render using only repository-relative resources."""
    args = arguments()
    config = json.loads(args.config.read_text(encoding='utf8'))
    bpy.ops.wm.open_mainfile(filepath=str(args.model.resolve()))
    for image in bpy.data.images:
        if image.source == 'FILE' and not image.packed_file:
            image.reload()
    controls = prepare_scene(config)
    args.out.mkdir(parents=True, exist_ok=True)
    render_frames(config, args.rows, args.out.resolve(), controls)
    LOGGER.info('Rendered %s rows to %s', len(args.rows), args.out)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
