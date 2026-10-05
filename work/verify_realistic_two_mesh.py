import bpy
import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
GLB_PATH = PROJECT_DIR / "outputs" / "tooth_gum_realistic_two_mesh_animation.glb"
VALIDATION_PATH = PROJECT_DIR / "outputs" / "tooth_gum_realistic_validation.json"


def translation(obj):
    return [round(value, 6) for value in obj.matrix_world.translation]


def world_z_bounds(obj):
    values = [(obj.matrix_world @ vertex.co).z for vertex in obj.data.vertices]
    return min(values), max(values)


def main():
    scene = bpy.context.scene
    meshes = sorted((obj for obj in scene.objects if obj.type == "MESH"), key=lambda obj: obj.name)
    names = [obj.name for obj in meshes]
    if names != ["Gum", "Teeth"]:
        raise RuntimeError(f"Expected exactly Gum and Teeth; found {names}")
    gum = bpy.data.objects["Gum"]
    teeth = bpy.data.objects["Teeth"]
    if gum.data is teeth.data:
        raise RuntimeError("Gum and Teeth share the same mesh datablock.")
    if teeth.parent is None or teeth.parent.name != "Teeth_Detach_Control":
        raise RuntimeError("Teeth are not attached to the animation control.")

    scene.frame_set(1)
    frame_1 = {"Teeth": translation(teeth), "Gum": translation(gum)}
    scene.frame_set(60)
    frame_60 = {"Teeth": translation(teeth), "Gum": translation(gum)}
    if frame_1["Teeth"] == frame_60["Teeth"]:
        raise RuntimeError("Teeth do not animate.")
    if frame_1["Gum"] != frame_60["Gum"]:
        raise RuntimeError("Gum is not static.")
    teeth_min_z, teeth_max_z = world_z_bounds(teeth)
    gum_min_z, gum_max_z = world_z_bounds(gum)
    clearance = teeth_min_z - gum_max_z
    if clearance <= 0:
        raise RuntimeError(f"Detached meshes still overlap vertically: clearance={clearance}")

    blend_result = {
        "mesh_object_count": 2,
        "mesh_names": names,
        "independent_mesh_datablocks": True,
        "frame_1_translation": frame_1,
        "frame_60_translation": frame_60,
        "detached_vertical_clearance_meters": round(clearance, 6),
        "faces": {"Teeth": len(teeth.data.polygons), "Gum": len(gum.data.polygons)},
    }

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(GLB_PATH))
    glb_meshes = sorted(obj.name for obj in bpy.context.scene.objects if obj.type == "MESH")
    animated_objects = [
        obj.name for obj in bpy.context.scene.objects
        if obj.animation_data is not None and obj.animation_data.action is not None
    ]
    if glb_meshes != ["Gum", "Teeth"]:
        raise RuntimeError(f"GLB expected exactly Gum and Teeth; found {glb_meshes}")
    if not bpy.data.actions or not animated_objects:
        raise RuntimeError("GLB animation was not preserved.")

    report = {
        "status": "passed",
        "blend": blend_result,
        "glb": {
            "mesh_object_count": 2,
            "mesh_names": glb_meshes,
            "action_count": len(bpy.data.actions),
            "animated_objects": animated_objects,
        },
    }
    VALIDATION_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("VALIDATION=" + json.dumps(report))


if __name__ == "__main__":
    main()
