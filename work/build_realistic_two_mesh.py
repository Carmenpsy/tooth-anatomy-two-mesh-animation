import bpy
import math
import json
import sys
from collections import defaultdict
from mathutils import Vector
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "outputs"
SOURCE = (
    Path(sys.argv[sys.argv.index("--") + 1]).expanduser().resolve()
    if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1
    else PROJECT_DIR / "assets" / "textured.glb"
)
BLEND_PATH = OUTPUT_DIR / "tooth_gum_realistic_two_mesh_animation.blend"
GLB_PATH = OUTPUT_DIR / "tooth_gum_realistic_two_mesh_animation.glb"
ASSEMBLED_PREVIEW = OUTPUT_DIR / "tooth_gum_realistic_assembled.png"
DETACHED_PREVIEW = OUTPUT_DIR / "tooth_gum_realistic_detached.png"
REPORT_PATH = OUTPUT_DIR / "tooth_gum_realistic_report.json"


def point_at(obj, target=(0.0, 0.0, 0.0)):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def material(name, color, roughness=0.55):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    principled = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    principled.inputs["Base Color"].default_value = (*color, 1.0)
    principled.inputs["Roughness"].default_value = roughness
    return mat


def ring_mesh(name, levels, segments=64, crown_notch=False):
    vertices = []
    for z, center_x, center_y, radius_x, radius_y in levels:
        for segment in range(segments):
            angle = 2.0 * math.pi * segment / segments
            x = center_x + radius_x * math.cos(angle)
            y = center_y + radius_y * math.sin(angle)
            adjusted_z = z
            if crown_notch and z > 0.058:
                upper_weight = min(1.0, (z - 0.058) / 0.020)
                adjusted_z -= 0.0035 * upper_weight * math.exp(-((x / 0.009) ** 2))
            vertices.append((x, y, adjusted_z))
    faces = []
    for level_index in range(len(levels) - 1):
        base = level_index * segments
        next_base = (level_index + 1) * segments
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            faces.append((base + segment, base + next_segment, next_base + next_segment, next_base + segment))
    bottom_center = len(vertices)
    vertices.append((levels[0][1], levels[0][2], levels[0][0]))
    top_center = len(vertices)
    vertices.append((levels[-1][1], levels[-1][2], levels[-1][0]))
    for segment in range(segments):
        next_segment = (segment + 1) % segments
        faces.append((bottom_center, next_segment, segment))
        top_base = (len(levels) - 1) * segments
        faces.append((top_center, top_base + segment, top_base + next_segment))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def join_and_voxel(objects, name, voxel_size=0.001):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    result = bpy.context.object
    result.name = name
    result.data.remesh_voxel_size = voxel_size
    result.data.remesh_voxel_adaptivity = 0.0
    bpy.ops.object.voxel_remesh()
    return result


def build_crown_cutter(name, scale=1.0):
    cutter = ring_mesh(name, [
        (0.004, 0.000, -0.006, 0.031 * scale, 0.036 * scale),
        (0.018, 0.000, -0.005, 0.038 * scale, 0.041 * scale),
        (0.040, 0.000, -0.003, 0.044 * scale, 0.044 * scale),
        (0.060, 0.000, -0.002, 0.045 * scale, 0.043 * scale),
        (0.074, 0.000, -0.002, 0.039 * scale, 0.038 * scale),
        (0.081, 0.000, -0.002, 0.021 * scale, 0.021 * scale),
    ], crown_notch=True)
    cutter.data.remesh_voxel_size = 0.001
    cutter.data.remesh_voxel_adaptivity = 0.0
    bpy.context.view_layer.objects.active = cutter
    cutter.select_set(True)
    bpy.ops.object.voxel_remesh()
    cutter.select_set(False)
    return cutter


def build_socket_cutter(name):
    crown = build_crown_cutter(name + "_Crown", scale=1.06)
    socket = ring_mesh(name + "_Socket", [
        (-0.075, 0.000, -0.013, 0.034, 0.037),
        (-0.045, 0.000, -0.013, 0.038, 0.039),
        (-0.010, 0.000, -0.012, 0.041, 0.040),
        (0.026, 0.000, -0.009, 0.043, 0.041),
    ])
    return join_and_voxel([crown, socket], name, voxel_size=0.001)


def build_roots(root_material):
    left = ring_mesh("Root_Left", [
        (0.022, -0.019, -0.007, 0.014, 0.027),
        (-0.008, -0.020, -0.008, 0.012, 0.025),
        (-0.033, -0.022, -0.008, 0.010, 0.022),
        (-0.057, -0.024, -0.008, 0.007, 0.017),
        (-0.070, -0.025, -0.008, 0.003, 0.008),
    ])
    right = ring_mesh("Root_Right", [
        (0.022, 0.019, -0.007, 0.014, 0.027),
        (-0.008, 0.020, -0.008, 0.012, 0.025),
        (-0.033, 0.022, -0.008, 0.010, 0.022),
        (-0.057, 0.024, -0.008, 0.007, 0.017),
        (-0.070, 0.025, -0.008, 0.003, 0.008),
    ])
    for root in (left, right):
        root.data.materials.append(root_material)
        bpy.context.view_layer.objects.active = root
        root.select_set(True)
        bpy.ops.object.shade_smooth_by_angle()
        root.select_set(False)
    return left, right


def apply_boolean(target, cutter, operation):
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    modifier = target.modifiers.new(name=f"{operation}_{cutter.name}", type="BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    target.select_set(False)


def trim_crown_below(crown, z_min=0.017):
    mesh = crown.data
    bpy.context.view_layer.objects.active = crown
    crown.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for polygon in mesh.polygons:
        center = polygon.center
        polygon.select = center.z < z_min
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    crown.select_set(False)


def keep_crown_components(crown, minimum_top=0.050):
    mesh = crown.data
    parents = list(range(len(mesh.vertices)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left, right):
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for polygon in mesh.polygons:
        for vertex_index in polygon.vertices[1:]:
            union(polygon.vertices[0], vertex_index)
    component_faces = defaultdict(list)
    component_vertices = defaultdict(set)
    for polygon in mesh.polygons:
        root = find(polygon.vertices[0])
        component_faces[root].append(polygon.index)
        component_vertices[root].update(polygon.vertices)
    remove = set()
    for root, faces in component_faces.items():
        zmax = max(mesh.vertices[index].co.z for index in component_vertices[root])
        if len(faces) < 12 or zmax < minimum_top:
            remove.update(faces)
    bpy.context.view_layer.objects.active = crown
    crown.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for polygon in mesh.polygons:
        polygon.select = polygon.index in remove
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    crown.select_set(False)


def remove_central_islands(gum):
    mesh = gum.data
    parents = list(range(len(mesh.vertices)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left, right):
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for polygon in mesh.polygons:
        for vertex_index in polygon.vertices[1:]:
            union(polygon.vertices[0], vertex_index)
    component_faces = defaultdict(list)
    component_vertices = defaultdict(set)
    for polygon in mesh.polygons:
        root = find(polygon.vertices[0])
        component_faces[root].append(polygon.index)
        component_vertices[root].update(polygon.vertices)
    remove = set()
    for root, faces in component_faces.items():
        coords = [mesh.vertices[index].co for index in component_vertices[root]]
        xmin, xmax = min(co.x for co in coords), max(co.x for co in coords)
        zmax = max(co.z for co in coords)
        if len(faces) < 12 or (xmin > -0.044 and xmax < 0.044 and zmax < 0.030):
            remove.update(faces)
    bpy.context.view_layer.objects.active = gum
    gum.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for polygon in mesh.polygons:
        polygon.select = polygon.index in remove
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    gum.select_set(False)


def remove_socket_residue(gum):
    mesh = gum.data
    bpy.context.view_layer.objects.active = gum
    gum.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for polygon in mesh.polygons:
        center = polygon.center
        polygon.select = (
            abs(center.x) < 0.048
        )
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    gum.select_set(False)


def assign_socket_material(gum, socket_material):
    gum.data.materials.append(socket_material)
    index = len(gum.data.materials) - 1
    for polygon in gum.data.polygons:
        center = polygon.center
        if abs(center.x) < 0.047 and center.z < 0.030 and center.y < 0.025:
            polygon.material_index = index


def add_recessed_gum_backing(gum, gum_material):
    bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.039, -0.026))
    backing = bpy.context.object
    backing.name = "Recessed_Gum_Backing"
    backing.scale = (0.066, 0.010, 0.044)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = backing.modifiers.new(name="Organic_Rounding", type="BEVEL")
    bevel.width = 0.008
    bevel.segments = 6
    bpy.context.view_layer.objects.active = backing
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    backing.data.materials.append(gum_material)
    bpy.ops.object.shade_smooth_by_angle()

    bpy.ops.object.select_all(action="DESELECT")
    gum.select_set(True)
    backing.select_set(True)
    bpy.context.view_layer.objects.active = gum
    bpy.ops.object.join()


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    source = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
    original_material = source.data.materials[0]

    crown = source.copy()
    crown.data = source.data.copy()
    crown.name = "Original_Crown"
    bpy.context.scene.collection.objects.link(crown)
    gum = source.copy()
    gum.data = source.data.copy()
    gum.name = "Gum"
    bpy.context.scene.collection.objects.link(gum)
    bpy.data.objects.remove(source, do_unlink=True)

    crown_cutter = build_crown_cutter("Crown_Cutter")
    socket_cutter = build_socket_cutter("Full_Tooth_Socket")
    apply_boolean(crown, crown_cutter, "INTERSECT")
    apply_boolean(gum, socket_cutter, "DIFFERENCE")
    trim_crown_below(crown)
    keep_crown_components(crown)
    bpy.data.objects.remove(crown_cutter, do_unlink=True)
    bpy.data.objects.remove(socket_cutter, do_unlink=True)
    remove_central_islands(gum)
    remove_socket_residue(gum)

    root_material = material("Natural_Root_Dentin", (0.60, 0.39, 0.19), 0.48)
    socket_material = material("Socket_Interior", (0.14, 0.012, 0.018), 0.72)
    gum_backing_material = material("Recessed_Healthy_Gum", (0.35, 0.035, 0.055), 0.68)
    roots = build_roots(root_material)
    assign_socket_material(gum, socket_material)
    add_recessed_gum_backing(gum, gum_backing_material)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in (crown, *roots):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = crown
    bpy.ops.object.join()
    teeth = bpy.context.object
    teeth.name = "Teeth"

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.0, 0.0, 0.0))
    control = bpy.context.object
    control.name = "Teeth_Detach_Control"
    teeth.parent = control
    teeth.matrix_parent_inverse = control.matrix_world.inverted()
    print(f"TEETH_FACES={len(teeth.data.polygons)} GUM_FACES={len(gum.data.polygons)}")

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 700
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.018, 0.018, 0.018)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.2
    scene.frame_start = 1
    scene.frame_end = 72
    scene.render.fps = 24
    scene.timeline_markers.new("Assembled", frame=1)
    scene.timeline_markers.new("Lift-off", frame=25)
    scene.timeline_markers.new("Detached", frame=60)

    poses = {
        1: ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        25: ((0.0, 0.0, 0.012), (0.0, math.radians(-1.0), 0.0)),
        60: ((0.0, 0.0, 0.105), (math.radians(2.0), math.radians(-5.0), math.radians(1.0))),
        72: ((0.0, 0.0, 0.105), (math.radians(2.0), math.radians(-5.0), math.radians(1.0))),
    }
    for frame, (location, rotation) in poses.items():
        scene.frame_set(frame)
        control.location = location
        control.rotation_euler = rotation
        control.keyframe_insert(data_path="location", frame=frame)
        control.keyframe_insert(data_path="rotation_euler", frame=frame)
    bpy.ops.object.light_add(type="AREA", location=(-0.15, -0.25, 0.20))
    key = bpy.context.object
    key.data.energy = 7
    key.data.size = 0.30
    point_at(key, (0.0, 0.0, 0.025))
    bpy.ops.object.light_add(type="AREA", location=(0.16, -0.18, 0.10))
    fill = bpy.context.object
    fill.data.energy = 3
    fill.data.size = 0.25
    point_at(fill, (0.0, 0.0, 0.020))
    bpy.ops.object.camera_add(location=(0.0, -0.48, 0.035))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.29
    point_at(camera, (0.0, 0.0, 0.035))
    scene.camera = camera

    scene.frame_set(1)
    scene.render.filepath = str(ASSEMBLED_PREVIEW)
    bpy.ops.render.render(write_still=True)
    scene.frame_set(60)
    scene.render.filepath = str(DETACHED_PREVIEW)
    bpy.ops.render.render(write_still=True)

    scene.frame_set(1)
    mesh_names = sorted(obj.name for obj in scene.objects if obj.type == "MESH")
    if mesh_names != ["Gum", "Teeth"]:
        raise RuntimeError(f"Expected exactly two mesh objects; found {mesh_names}")

    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in (control, teeth, gum):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = teeth
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT",
        export_animations=True,
        export_current_frame=False,
        export_cameras=False,
        export_lights=False,
    )

    report = {
        "source_asset": "Aholo Lux3D Tooth Anatomy Model",
        "source_asset_id": 7313,
        "mesh_object_count": 2,
        "mesh_objects": [
            {
                "name": "Teeth",
                "faces": len(teeth.data.polygons),
                "animated": True,
                "construction": "original detailed crown with clean anatomical roots",
            },
            {
                "name": "Gum",
                "faces": len(gum.data.polygons),
                "animated": False,
                "construction": "original textured gum/bone exterior with recessed gum backing",
            },
        ],
        "duration_seconds": 3.0,
        "frame_range": [1, 72],
        "frames_per_second": 24,
        "blend_file": str(BLEND_PATH.relative_to(PROJECT_DIR)),
        "animated_glb_file": str(GLB_PATH.relative_to(PROJECT_DIR)),
        "assembled_preview": str(ASSEMBLED_PREVIEW.relative_to(PROJECT_DIR)),
        "detached_preview": str(DETACHED_PREVIEW.relative_to(PROJECT_DIR)),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("FINAL_REPORT=" + json.dumps(report))


if __name__ == "__main__":
    main()
