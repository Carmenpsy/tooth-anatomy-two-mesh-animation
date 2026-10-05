# Tooth Anatomy — Two-Mesh Detachment Animation

Corrected version of Aholo Lux3D asset **7313**, organized as exactly two independent mesh objects:

- `Teeth` — detailed crown and clean anatomical roots; animated.
- `Gum` — textured gum/bone exterior and recessed gum backing; static.

The animation runs for 72 frames at 24 fps. The teeth move upward from the assembled position and are fully detached by frame 60.

## Files

- `outputs/tooth_gum_realistic_two_mesh_animation.blend` — editable Blender scene with packed resources.
- `outputs/tooth_gum_realistic_two_mesh_animation.glb` — portable animated model.
- `outputs/tooth_gum_realistic_assembled.png` — frame 1 preview.
- `outputs/tooth_gum_realistic_detached.png` — frame 60 preview.
- `outputs/tooth_gum_realistic_validation.json` — verification results.
- `work/build_realistic_two_mesh.py` — reproducible Blender build script.
- `work/verify_realistic_two_mesh.py` — validation script.

## Rebuild

Use Blender in background mode and pass the original Aholo Lux3D GLB after `--`:

```powershell
blender --background --python work/build_realistic_two_mesh.py -- C:\path\to\textured.glb
```

If no source path is supplied, the builder looks for `assets/textured.glb`.

## Verify

```powershell
blender outputs/tooth_gum_realistic_two_mesh_animation.blend --background --python work/verify_realistic_two_mesh.py
```

The checked output contains exactly `Teeth` and `Gum`, uses independent mesh datablocks, keeps the gum static, preserves the tooth-detachment animation in the GLB, and has positive clearance at the detached pose.
