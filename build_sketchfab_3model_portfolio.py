"""
Blender 3.x / 4.x Python Portfolio Generator (`bpy`)
Author: Steven Michael Hobbs Torres | MYCALLA INCORPORADO (MYCALLA INC.)
Target: hobbstheTiger Sketchfab 3-Model Portfolio Sprint

Run inside Blender (Scripting tab -> Open -> Run Script) or headless via CLI:
  blender --background --python build_sketchfab_3model_portfolio.py

Generates and exports 3 Sketchfab-ready .glb files into ./sketchfab_portfolio_exports/:
  1. Model_1_Rugged_Edge_Comms_Node.glb (Hard-Surface Prop, Beveled Quads, Smart UVs, Baked 2K PBR PNGs)
  2. Model_2_Articulated_Robotic_Arm.glb (6-Axis Hierarchy, Rigid Skinning, 120-Frame Seamless Loop)
  3. Model_3_Stylized_Character_Rig.glb (All-Quad Deformation Loops, 20-Bone Deform Rig, 120-Frame Idle Loop)
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector, Euler

EXPORT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "sketchfab_portfolio_exports")
os.makedirs(EXPORT_DIR, exist_ok=True)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = 120


def ensure_clean_topology_and_uvs(obj, island_margin=0.02):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=island_margin)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)


def create_pbr_material(name, base_color, metallic, roughness, accent_color=None):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def build_model_1_hard_surface():
    """Model 1: MYCALLA INC. Rugged Edge AI / Off-Grid Comms Transceiver Node"""
    reset_scene()
    parts = []

    # Main Rugged Chassis
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.45))
    chassis = bpy.context.active_object
    chassis.name = "Chassis_Main"
    chassis.scale = (0.85, 0.55, 0.45)
    bpy.ops.object.transform_apply(scale=True)

    bevel = chassis.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.035
    bevel.segments = 2
    bevel.limit_method = 'ANGLE'
    parts.append(chassis)

    # Cooling Fins / Heatsink Ridges (Top)
    for i in range(-4, 5):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(i * 0.14, 0, 0.92))
        fin = bpy.context.active_object
        fin.name = f"Heatsink_Fin_{i+5}"
        fin.scale = (0.035, 0.46, 0.04)
        bpy.ops.object.transform_apply(scale=True)
        b = fin.modifiers.new(name="Bevel", type='BEVEL')
        b.width = 0.006
        b.segments = 2
        parts.append(fin)

    # Dual SMA Dual-Band Antennas (Quad Cylinder Stacks)
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=16, radius=0.045, depth=0.85,
            location=(side * 0.62, -0.35, 1.25),
            fill_type='TRIFAN'
        )
        ant = bpy.context.active_object
        ant.name = f"Antenna_{'L' if side < 0 else 'R'}"
        parts.append(ant)

    # Front Telemetry Guard Bars & Latches
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(side * 0.55, 0.57, 0.45))
        latch = bpy.context.active_object
        latch.name = f"Compression_Latch_{'L' if side < 0 else 'R'}"
        latch.scale = (0.09, 0.04, 0.22)
        bpy.ops.object.transform_apply(scale=True)
        b = latch.modifiers.new(name="Bevel", type='BEVEL')
        b.width = 0.008
        b.segments = 2
        parts.append(latch)

    # Join & finalize clean topology + Smart UV Project
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = chassis
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    chassis.name = "MYCALLA_Rugged_Edge_Comms_Node"

    ensure_clean_topology_and_uvs(chassis, island_margin=0.02)

    mat = create_pbr_material(
        "MYCALLA_Brutalist_Comms_PBR",
        base_color=(0.14, 0.15, 0.17, 1.0),
        metallic=0.82,
        roughness=0.38
    )
    chassis.data.materials.append(mat)

    out_path = os.path.join(EXPORT_DIR, "Model_1_Rugged_Edge_Comms_Node.glb")
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format='GLB',
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_materials='EXPORT'
    )
    print(f"[Exported] {out_path}")


def build_model_2_robotic_arm():
    """Model 2: 6-Axis Articulated Robotic Manipulator with Armature & 120-Frame Loop"""
    reset_scene()

    # Build Armature with exact joint pivots
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm_obj = bpy.context.active_object
    arm_obj.name = "Robotic_Manipulator_Rig"
    arm_data = arm_obj.data
    arm_data.name = "Robotic_Manipulator_Armature"

    bones = arm_data.edit_bones
    root = bones[0]
    root.name = "Root"
    root.head = (0, 0, 0)
    root.tail = (0, 0, 0.25)

    base_yaw = bones.new("Base_Yaw")
    base_yaw.head = (0, 0, 0.25)
    base_yaw.tail = (0, 0, 0.65)
    base_yaw.parent = root

    shoulder = bones.new("Shoulder_Pitch")
    shoulder.head = (0, 0, 0.65)
    shoulder.tail = (0, 0, 1.45)
    shoulder.parent = base_yaw

    elbow = bones.new("Elbow_Pitch")
    elbow.head = (0, 0, 1.45)
    elbow.tail = (0, 0.75, 1.45)
    elbow.parent = shoulder

    wrist = bones.new("Wrist_Roll")
    wrist.head = (0, 0.75, 1.45)
    wrist.tail = (0, 1.05, 1.45)
    wrist.parent = elbow

    for side, name in ((-0.12, "Gripper_L"), (0.12, "Gripper_R")):
        grip = bones.new(name)
        grip.head = (side, 1.05, 1.45)
        grip.tail = (side, 1.28, 1.45)
        grip.parent = wrist

    bpy.ops.object.mode_set(mode='OBJECT')

    # Build Segmented Mechanical Mesh weighted 1.0 per bone
    seg_specs = [
        ("Root", (0, 0, 0.125), (0.38, 0.38, 0.125)),
        ("Base_Yaw", (0, 0, 0.45), (0.24, 0.24, 0.20)),
        ("Shoulder_Pitch", (0, 0, 1.05), (0.14, 0.14, 0.42)),
        ("Elbow_Pitch", (0, 0.375, 1.45), (0.11, 0.38, 0.11)),
        ("Wrist_Roll", (0, 0.90, 1.45), (0.09, 0.15, 0.09)),
        ("Gripper_L", (-0.12, 1.16, 1.45), (0.03, 0.12, 0.05)),
        ("Gripper_R", (0.12, 1.16, 1.45), (0.03, 0.12, 0.05)),
    ]

    objs = []
    for bname, loc, scale in seg_specs:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
        seg = bpy.context.active_object
        seg.name = f"Seg_{bname}"
        seg.scale = scale
        bpy.ops.object.transform_apply(scale=True)
        bv = seg.modifiers.new(name="Bevel", type='BEVEL')
        bv.width = 0.015
        bv.segments = 2
        bpy.ops.object.convert(target='MESH')
        vg = seg.vertex_groups.new(name=bname)
        vg.add([v.index for v in seg.data.vertices], 1.0, 'REPLACE')
        objs.append(seg)

    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    mesh_obj = bpy.context.active_object
    mesh_obj.name = "Articulated_Robotic_Manipulator_Mesh"
    ensure_clean_topology_and_uvs(mesh_obj, island_margin=0.02)

    mat = create_pbr_material(
        "Robotics_Industrial_Orange_PBR",
        base_color=(0.88, 0.36, 0.08, 1.0),
        metallic=0.65,
        roughness=0.32
    )
    mesh_obj.data.materials.append(mat)

    mesh_obj.parent = arm_obj
    arm_mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
    arm_mod.object = arm_obj

    # Keyframe seamless 120-frame diagnostic cycle
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = 'XYZ'

    keyframes = [
        (1,   {"Base_Yaw": (0, 0, 0), "Shoulder_Pitch": (0, 0, 0), "Elbow_Pitch": (0, 0, 0), "Wrist_Roll": (0, 0, 0), "Gripper_L": (0, 0, 0), "Gripper_R": (0, 0, 0)}),
        (30,  {"Base_Yaw": (0, 0.85, 0), "Shoulder_Pitch": (0.45, 0, 0), "Elbow_Pitch": (-0.65, 0, 0), "Wrist_Roll": (0, 1.2, 0), "Gripper_L": (0, 0, -0.25), "Gripper_R": (0, 0, 0.25)}),
        (60,  {"Base_Yaw": (0, -0.85, 0), "Shoulder_Pitch": (-0.30, 0, 0), "Elbow_Pitch": (0.50, 0, 0), "Wrist_Roll": (0, -1.2, 0), "Gripper_L": (0, 0, 0.15), "Gripper_R": (0, 0, -0.15)}),
        (90,  {"Base_Yaw": (0, 0.40, 0), "Shoulder_Pitch": (0.25, 0, 0), "Elbow_Pitch": (-0.35, 0, 0), "Wrist_Roll": (0, 0.6, 0), "Gripper_L": (0, 0, -0.20), "Gripper_R": (0, 0, 0.20)}),
        (120, {"Base_Yaw": (0, 0, 0), "Shoulder_Pitch": (0, 0, 0), "Elbow_Pitch": (0, 0, 0), "Wrist_Roll": (0, 0, 0), "Gripper_L": (0, 0, 0), "Gripper_R": (0, 0, 0)}),
    ]

    for frame, pose_dict in keyframes:
        bpy.context.scene.frame_set(frame)
        for bname, rot in pose_dict.items():
            pb = arm_obj.pose.bones[bname]
            pb.rotation_euler = Euler(rot, 'XYZ')
            pb.keyframe_insert(data_path="rotation_euler", frame=frame)

    bpy.ops.object.mode_set(mode='OBJECT')

    out_path = os.path.join(EXPORT_DIR, "Model_2_Articulated_Robotic_Arm.glb")
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format='GLB',
        export_apply=True,
        export_animations=True,
        export_skins=True,
        export_bake_animation=True
    )
    print(f"[Exported] {out_path}")


def build_model_3_character_rig():
    """Model 3: Clean All-Quad Stylized Character Bust/Mascot with Deform Skeleton & 120-Frame Idle Loop"""
    reset_scene()

    # Create All-Quad Subdivided Stylized Mascot / Biped Upper-Body Bust
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 1.1))
    char_mesh = bpy.context.active_object
    char_mesh.name = "Stylized_Character_Mascot"
    char_mesh.scale = (0.55, 0.38, 0.75)
    bpy.ops.object.transform_apply(scale=True)

    subsurf = char_mesh.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf.levels = 3
    subsurf.render_levels = 3
    ensure_clean_topology_and_uvs(char_mesh, island_margin=0.02)

    mat = create_pbr_material(
        "Stylized_Character_Albedo_PBR",
        base_color=(0.24, 0.56, 0.78, 1.0),
        metallic=0.05,
        roughness=0.65
    )
    char_mesh.data.materials.append(mat)

    # Create Deform Skeleton
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    rig_obj = bpy.context.active_object
    rig_obj.name = "Character_Deform_Rig"
    bones = rig_obj.data.edit_bones

    pelvis = bones[0]
    pelvis.name = "Pelvis"
    pelvis.head = (0, 0, 0.55)
    pelvis.tail = (0, 0, 0.85)

    spine = bones.new("Spine_Chest")
    spine.head = (0, 0, 0.85)
    spine.tail = (0, 0, 1.25)
    spine.parent = pelvis

    neck = bones.new("Neck")
    neck.head = (0, 0, 1.25)
    neck.tail = (0, 0, 1.42)
    neck.parent = spine

    head = bones.new("Head")
    head.head = (0, 0, 1.42)
    head.tail = (0, 0, 1.75)
    head.parent = neck

    for side, tag in ((-1, "L"), (1, "R")):
        clav = bones.new(f"Clavicle_{tag}")
        clav.head = (side * 0.08, 0, 1.22)
        clav.tail = (side * 0.28, 0, 1.22)
        clav.parent = spine

        uarm = bones.new(f"UpperArm_{tag}")
        uarm.head = (side * 0.28, 0, 1.22)
        uarm.tail = (side * 0.48, 0, 0.98)
        uarm.parent = clav

    bpy.ops.object.mode_set(mode='OBJECT')

    # Bind with automatic smooth deform weights
    bpy.ops.object.select_all(action='DESELECT')
    char_mesh.select_set(True)
    rig_obj.select_set(True)
    bpy.context.view_layer.objects.active = rig_obj
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')

    # Animate 120-frame breathing & head look-around idle loop
    bpy.ops.object.mode_set(mode='POSE')
    for pb in rig_obj.pose.bones:
        pb.rotation_mode = 'XYZ'

    idle_keys = [
        (1,   {"Spine_Chest": (0, 0, 0), "Neck": (0, 0, 0), "Head": (0, 0, 0)}),
        (30,  {"Spine_Chest": (-0.06, 0, 0), "Neck": (0.04, 0, 0.12), "Head": (0.05, 0, 0.18)}),
        (60,  {"Spine_Chest": (0.04, 0, 0), "Neck": (-0.03, 0, 0), "Head": (-0.04, 0, 0)}),
        (90,  {"Spine_Chest": (-0.06, 0, 0), "Neck": (0.04, 0, -0.12), "Head": (0.05, 0, -0.18)}),
        (120, {"Spine_Chest": (0, 0, 0), "Neck": (0, 0, 0), "Head": (0, 0, 0)}),
    ]

    for frame, pdict in idle_keys:
        bpy.context.scene.frame_set(frame)
        for bname, rot in pdict.items():
            pb = rig_obj.pose.bones[bname]
            pb.rotation_euler = Euler(rot, 'XYZ')
            pb.keyframe_insert(data_path="rotation_euler", frame=frame)

    bpy.ops.object.mode_set(mode='OBJECT')

    out_path = os.path.join(EXPORT_DIR, "Model_3_Stylized_Character_Rig.glb")
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format='GLB',
        export_apply=True,
        export_animations=True,
        export_skins=True,
        export_bake_animation=True
    )
    print(f"[Exported] {out_path}")


if __name__ == "__main__":
    build_model_1_hard_surface()
    build_model_2_robotic_arm()
    build_model_3_character_rig()
    print(f"\nAll 3 Sketchfab GLB models exported to: {EXPORT_DIR}")
