"""Check fixed mesh geometry and permitted rigid joint motion in Blender."""
import hashlib
from array import array

import bpy

ALLOWED_AXES = {'J5_lower_yaw': 2, 'J3_body_pitch': 0, 'J4_lower_attachment_fold': 1}
FIXED_OBJECTS = ('R0_mount', 'R1_upper')
TOLERANCE = 1e-5


def matrix_error(first, second):
    """Return the largest component difference between two matrices."""
    return max(abs(first[row][col] - second[row][col]) for row in range(4) for col in range(4))


def geometry_hash(obj):
    """Return a hash of one mesh's fixed local vertices."""
    values = array('f', [0.0]) * (len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get('co', values)
    return hashlib.sha256(values.tobytes()).hexdigest()


def snapshot():
    """Capture geometry, local bindings, fixed objects and the camera."""
    meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    return {
        'geometry': {obj.name: geometry_hash(obj) for obj in meshes},
        'local': {obj.name: obj.matrix_basis.copy() for obj in meshes},
        'joints': {name: bpy.data.objects[name].location.copy() for name in ALLOWED_AXES},
        'fixed': {name: bpy.data.objects[name].matrix_world.copy() for name in FIXED_OBJECTS},
        'camera': bpy.context.scene.camera.matrix_world.copy(),
    }


def verify(reference):
    """Reject mesh deformation, moved bindings, fixed parts or off-axis motion."""
    errors = {'local_transform': 0.0, 'fixed_world': 0.0, 'joint_translation': 0.0,
              'off_axis_rotation': 0.0, 'rigidity': 0.0}
    for name, expected in reference['geometry'].items():
        obj = bpy.data.objects[name]
        if geometry_hash(obj) != expected:
            raise ValueError(f'Animated geometry changed: {name}')
        errors['local_transform'] = max(errors['local_transform'],
                                        matrix_error(obj.matrix_basis, reference['local'][name]))
        gram = obj.matrix_world.to_3x3().transposed() @ obj.matrix_world.to_3x3()
        errors['rigidity'] = max(errors['rigidity'],
                                max(abs(gram[row][col] - (row == col))
                                    for row in range(3) for col in range(3)))
    for name, matrix in reference['fixed'].items():
        errors['fixed_world'] = max(errors['fixed_world'], matrix_error(bpy.data.objects[name].matrix_world, matrix))
    for name, axis in ALLOWED_AXES.items():
        obj = bpy.data.objects[name]
        errors['joint_translation'] = max(errors['joint_translation'],
                                          (obj.location - reference['joints'][name]).length)
        errors['off_axis_rotation'] = max(errors['off_axis_rotation'],
                                          max(abs(obj.rotation_euler[index]) for index in range(3) if index != axis))
    if matrix_error(bpy.context.scene.camera.matrix_world, reference['camera']) != 0:
        raise ValueError('Camera changed between frames')
    if max(errors.values()) >= TOLERANCE:
        raise ValueError(f'Rigid motion validation failed: {errors}')
    return errors
