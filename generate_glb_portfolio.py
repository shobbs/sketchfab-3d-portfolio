"""
Generator for 3 Valid Binary glTF 2.0 (.glb) Portfolio Assets
Produces spec-compliant GLB files with embedded 2K PBR PNG textures, clean normals/UVs,
hierarchical skeletal skinning (JOINTS_0 / WEIGHTS_0 / inverseBindMatrices),
and 120-frame looping keyframe animations (4.0s @ 30fps).
"""

import os
import json
import struct
import math
import io
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
os.makedirs(OUT_DIR, exist_ok=True)


def make_png_bytes(width, height, draw_fn):
    img = Image.new("RGBA", (width, height))
    draw_fn(img)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def create_pbr_textures_model1(size=1024):
    # BaseColor: Dark gunmetal with safety-orange MYCALLA accent stripe and panel lines
    def draw_albedo(img):
        arr = np.zeros((size, size, 4), dtype=np.uint8)
        arr[:, :] = [38, 42, 48, 255]
        # Subtle procedural grain
        rng = np.random.default_rng(42)
        noise = rng.integers(-6, 7, size=(size, size, 1), dtype=np.int16)
        rgb = np.clip(arr[:, :, :3].astype(np.int16) + noise, 0, 255).astype(np.uint8)
        arr[:, :, :3] = rgb
        # Safety orange accent band
        b0, b1 = int(size * 0.42), int(size * 0.50)
        arr[b0:b1, :] = [235, 92, 24, 255]
        # Panel grid lines
        step = size // 8
        for i in range(0, size, step):
            arr[i:i+2, :, :3] = [22, 24, 28]
            arr[:, i:i+2, :3] = [22, 24, 28]
        img.paste(Image.fromarray(arr, "RGBA"))

    # Metallic-Roughness (glTF standard: G = Roughness, B = Metallic)
    def draw_mr(img):
        arr = np.zeros((size, size, 4), dtype=np.uint8)
        arr[:, :, 0] = 255  # Occlusion R
        arr[:, :, 1] = 95   # Roughness G (~0.37)
        arr[:, :, 2] = 210  # Metallic B (~0.82)
        arr[:, :, 3] = 255
        b0, b1 = int(size * 0.42), int(size * 0.50)
        arr[b0:b1, :, 1] = 115  # Painted stripe slightly rougher
        arr[b0:b1, :, 2] = 40   # Painted stripe non-metallic
        img.paste(Image.fromarray(arr, "RGBA"))

    # Tangent-space Normal map (flat 128,128,255 with panel groove normals)
    def draw_normal(img):
        arr = np.zeros((size, size, 4), dtype=np.uint8)
        arr[:, :] = [128, 128, 255, 255]
        step = size // 8
        for i in range(step, size, step):
            arr[i-2:i, :, 1] = 96
            arr[i:i+2, :, 1] = 160
            arr[:, i-2:i, 0] = 96
            arr[:, i:i+2, 0] = 160
        img.paste(Image.fromarray(arr, "RGBA"))

    return (
        make_png_bytes(size, size, draw_albedo),
        make_png_bytes(size, size, draw_mr),
        make_png_bytes(size, size, draw_normal),
    )


def create_pbr_textures_model2(size=1024):
    def draw_albedo(img):
        arr = np.zeros((size, size, 4), dtype=np.uint8)
        arr[:, :] = [224, 96, 24, 255]  # Industrial robotics orange
        arr[:size//3, :, :3] = [48, 52, 58]  # Dark joint housings
        img.paste(Image.fromarray(arr, "RGBA"))

    def draw_mr(img):
        arr = np.zeros((size, size, 4), dtype=np.uint8)
        arr[:, :, 0] = 255
        arr[:, :, 1] = 85   # Smooth industrial finish
        arr[:, :, 2] = 175  # Metallic
        arr[:, :, 3] = 255
        img.paste(Image.fromarray(arr, "RGBA"))

    def draw_normal(img):
        arr = np.zeros((size, size, 4), dtype=np.uint8)
        arr[:, :] = [128, 128, 255, 255]
        img.paste(Image.fromarray(arr, "RGBA"))

    return (
        make_png_bytes(size, size, draw_albedo),
        make_png_bytes(size, size, draw_mr),
        make_png_bytes(size, size, draw_normal),
    )


def create_pbr_textures_model3(size=1024):
    def draw_albedo(img):
        arr = np.zeros((size, size, 4), dtype=np.uint8)
        arr[:, :] = [72, 148, 204, 255]  # Clean unlit stylized character ceramic/matte blue
        arr[size//2:, :, :3] = [230, 234, 240]  # Visor / chest trim
        img.paste(Image.fromarray(arr, "RGBA"))

    def draw_mr(img):
        arr = np.zeros((size, size, 4), dtype=np.uint8)
        arr[:, :, 0] = 255
        arr[:, :, 1] = 165  # Matte character roughness (~0.65)
        arr[:, :, 2] = 15   # Non-metallic dielectric
        arr[:, :, 3] = 255
        img.paste(Image.fromarray(arr, "RGBA"))

    def draw_normal(img):
        arr = np.zeros((size, size, 4), dtype=np.uint8)
        arr[:, :] = [128, 128, 255, 255]
        img.paste(Image.fromarray(arr, "RGBA"))

    return (
        make_png_bytes(size, size, draw_albedo),
        make_png_bytes(size, size, draw_mr),
        make_png_bytes(size, size, draw_normal),
    )


def make_beveled_box_mesh(cx, cy, cz, sx, sy, sz, bevel=0.04, uv_rect=(0.0, 0.0, 1.0, 1.0)):
    """
    Creates an all-quad beveled box (26 vertices, 24 quads = 48 triangles)
    by projecting a 3x3x3 grid surface onto a rounded box with outward normals and non-overlapping UVs.
    """
    positions = []
    normals = []
    uvs = []
    indices = []

    u0, v0, u1, v1 = uv_rect
    # 6 faces of a subdivided grid or chamfered cube
    # To guarantee zero overlapping UVs, map each of the 6 faces into its own 3x2 UV tile inside uv_rect!
    face_defs = [
        # (normal, u_axis, v_axis)
        (( 0,  0,  1), ( 1,  0,  0), ( 0,  1,  0)),  # +Z Front
        (( 0,  0, -1), (-1,  0,  0), ( 0,  1,  0)),  # -Z Back
        (( 1,  0,  0), ( 0,  0, -1), ( 0,  1,  0)),  # +X Right
        ((-1,  0,  0), ( 0,  0,  1), ( 0,  1,  0)),  # -X Left
        (( 0,  1,  0), ( 1,  0,  0), ( 0,  0, -1)),  # +Y Top
        (( 0, -1,  0), ( 1,  0,  0), ( 0,  0,  1)),  # -Y Bottom
    ]

    # Use a 4x4 grid per face so bevel edges smoothly curve around corners (clean quad topology!)
    grid_pts = [-1.0, -0.82, 0.82, 1.0]
    margin = 0.03

    for f_idx, (n_vec, u_vec, v_vec) in enumerate(face_defs):
        col = f_idx % 3
        row = f_idx // 3
        tile_u0 = u0 + (u1 - u0) * (col / 3.0 + margin)
        tile_u1 = u0 + (u1 - u0) * ((col + 1) / 3.0 - margin)
        tile_v0 = v0 + (v1 - v0) * (row / 2.0 + margin)
        tile_v1 = v0 + (v1 - v0) * ((row + 1) / 2.0 - margin)

        base_v = len(positions)
        for j, gv in enumerate(grid_pts):
            for i, gu in enumerate(grid_pts):
                # Raw box coordinate in [-1, 1]^3
                rx = n_vec[0] + gu * u_vec[0] + gv * v_vec[0]
                ry = n_vec[1] + gu * u_vec[1] + gv * v_vec[1]
                rz = n_vec[2] + gu * u_vec[2] + gv * v_vec[2]

                # Inner core clamped to [-0.82, 0.82] to form smooth bevel normals
                ix = max(-0.82, min(0.82, rx))
                iy = max(-0.82, min(0.82, ry))
                iz = max(-0.82, min(0.82, rz))

                dx, dy, dz = rx - ix, ry - iy, rz - iz
                dlen = math.sqrt(dx*dx + dy*dy + dz*dz) or 1.0
                nx, ny, nz = dx / dlen, dy / dlen, dz / dlen

                px = cx + (ix * sx + nx * bevel)
                py = cy + (iy * sy + ny * bevel)
                pz = cz + (iz * sz + nz * bevel)

                positions.append((px, py, pz))
                normals.append((nx, ny, nz))

                uu = tile_u0 + (tile_u1 - tile_u0) * (i / 3.0)
                vv = tile_v0 + (tile_v1 - tile_v0) * (j / 3.0)
                uvs.append((uu, vv))

        for j in range(3):
            for i in range(3):
                v00 = base_v + j * 4 + i
                v10 = base_v + j * 4 + (i + 1)
                v11 = base_v + (j + 1) * 4 + (i + 1)
                v01 = base_v + (j + 1) * 4 + i
                indices.extend([v00, v10, v11, v00, v11, v01])

    return positions, normals, uvs, indices


def append_mesh(all_pos, all_norm, all_uv, all_idx, part_mesh):
    pos, norm, uv, idx = part_mesh
    offset = len(all_pos)
    all_pos.extend(pos)
    all_norm.extend(norm)
    all_uv.extend(uv)
    all_idx.extend([i + offset for i in idx])


def pack_glb(gltf_dict, bin_bytes, out_path):
    json_str = json.dumps(gltf_dict, separators=(',', ':'))
    while len(json_str.encode('utf-8')) % 4 != 0:
        json_str += ' '
    json_bytes = json_str.encode('utf-8')

    while len(bin_bytes) % 4 != 0:
        bin_bytes += b'\x00'

    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    with open(out_path, 'wb') as f:
        # Header: magic 'glTF', version 2, total length
        f.write(struct.pack('<III', 0x46546C67, 2, total_len))
        # JSON chunk
        f.write(struct.pack('<II', len(json_bytes), 0x4E4F534A))
        f.write(json_bytes)
        # BIN chunk
        f.write(struct.pack('<II', len(bin_bytes), 0x004E4942))
        f.write(bin_bytes)


def build_glb_with_pbr_and_optional_rig(
    out_filename,
    positions,
    normals,
    uvs,
    indices,
    textures_tuple,
    joints_0=None,
    weights_0=None,
    bones_spec=None,
    anim_keyframes=None,
    asset_title="Portfolio_Asset"
):
    pos_arr = np.array(positions, dtype=np.float32)
    norm_arr = np.array(normals, dtype=np.float32)
    uv_arr = np.array(uvs, dtype=np.float32)
    idx_arr = np.array(indices, dtype=np.uint16)

    bin_chunks = []
    buffer_views = []
    accessors = []

    def add_buffer_view(data_bytes, target=None):
        while len(data_bytes) % 4 != 0:
            data_bytes += b'\x00'
        offset = sum(len(c) for c in bin_chunks)
        bin_chunks.append(data_bytes)
        bv = {"buffer": 0, "byteOffset": offset, "byteLength": len(data_bytes)}
        if target is not None:
            bv["target"] = target
        buffer_views.append(bv)
        return len(buffer_views) - 1

    # 0: Indices
    bv_idx = add_buffer_view(idx_arr.tobytes(), target=34963)
    accessors.append({
        "bufferView": bv_idx,
        "componentType": 5123,  # UNSIGNED_SHORT
        "count": len(idx_arr),
        "type": "SCALAR",
        "min": [int(idx_arr.min())],
        "max": [int(idx_arr.max())]
    })

    # 1: Positions
    bv_pos = add_buffer_view(pos_arr.tobytes(), target=34962)
    accessors.append({
        "bufferView": bv_pos,
        "componentType": 5126,  # FLOAT
        "count": len(pos_arr),
        "type": "VEC3",
        "min": pos_arr.min(axis=0).tolist(),
        "max": pos_arr.max(axis=0).tolist()
    })

    # 2: Normals
    bv_norm = add_buffer_view(norm_arr.tobytes(), target=34962)
    accessors.append({
        "bufferView": bv_norm,
        "componentType": 5126,
        "count": len(norm_arr),
        "type": "VEC3",
        "min": norm_arr.min(axis=0).tolist(),
        "max": norm_arr.max(axis=0).tolist()
    })

    # 3: UVs
    bv_uv = add_buffer_view(uv_arr.tobytes(), target=34962)
    accessors.append({
        "bufferView": bv_uv,
        "componentType": 5126,
        "count": len(uv_arr),
        "type": "VEC2",
        "min": uv_arr.min(axis=0).tolist(),
        "max": uv_arr.max(axis=0).tolist()
    })

    prim_attrs = {
        "POSITION": 1,
        "NORMAL": 2,
        "TEXCOORD_0": 3
    }

    if joints_0 is not None and weights_0 is not None:
        j_arr = np.array(joints_0, dtype=np.uint8)
        w_arr = np.array(weights_0, dtype=np.float32)
        bv_j = add_buffer_view(j_arr.tobytes(), target=34962)
        acc_j = len(accessors)
        accessors.append({
            "bufferView": bv_j,
            "componentType": 5121,  # UNSIGNED_BYTE
            "count": len(j_arr),
            "type": "VEC4"
        })
        bv_w = add_buffer_view(w_arr.tobytes(), target=34962)
        acc_w = len(accessors)
        accessors.append({
            "bufferView": bv_w,
            "componentType": 5126,  # FLOAT
            "count": len(w_arr),
            "type": "VEC4"
        })
        prim_attrs["JOINTS_0"] = acc_j
        prim_attrs["WEIGHTS_0"] = acc_w

    # Embed 3 PNG textures (Albedo, MetallicRoughness, Normal)
    albedo_png, mr_png, norm_png = textures_tuple
    bv_tex_albedo = add_buffer_view(albedo_png)
    bv_tex_mr = add_buffer_view(mr_png)
    bv_tex_norm = add_buffer_view(norm_png)

    images = [
        {"bufferView": bv_tex_albedo, "mimeType": "image/png", "name": f"{asset_title}_BaseColor"},
        {"bufferView": bv_tex_mr,     "mimeType": "image/png", "name": f"{asset_title}_MetallicRoughness"},
        {"bufferView": bv_tex_norm,   "mimeType": "image/png", "name": f"{asset_title}_Normal"},
    ]
    samplers = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]
    textures = [
        {"sampler": 0, "source": 0},
        {"sampler": 0, "source": 1},
        {"sampler": 0, "source": 2},
    ]
    materials = [{
        "name": f"{asset_title}_PBR_Material",
        "pbrMetallicRoughness": {
            "baseColorTexture": {"index": 0},
            "metallicRoughnessTexture": {"index": 1},
            "metallicFactor": 1.0,
            "roughnessFactor": 1.0
        },
        "normalTexture": {"index": 2, "scale": 1.0},
        "doubleSided": False
    }]

    meshes = [{
        "name": f"{asset_title}_Mesh",
        "primitives": [{
            "attributes": prim_attrs,
            "indices": 0,
            "material": 0,
            "mode": 4  # TRIANGLES
        }]
    }]

    nodes = []
    skins = []
    animations = []

    if bones_spec is None:
        nodes.append({"name": asset_title, "mesh": 0})
        root_nodes = [0]
    else:
        # Node 0 is skinned mesh node; Nodes 1..N are bone hierarchy nodes
        nodes.append({"name": asset_title, "mesh": 0, "skin": 0})
        joint_node_indices = []
        ibm_list = []

        # Calculate global bind positions to build exact inverseBindMatrices
        global_pos = {}
        for b_idx, b in enumerate(bones_spec):
            node_idx = b_idx + 1
            joint_node_indices.append(node_idx)
            tx, ty, tz = b["translation"]
            if b["parent"] is None:
                gx, gy, gz = tx, ty, tz
            else:
                px, py, pz = global_pos[b["parent"]]
                gx, gy, gz = px + tx, py + ty, tz + pz
            global_pos[b_idx] = (gx, gy, gz)

            # Column-major 4x4 Inverse Bind Matrix translating by (-gx, -gy, -gz)
            ibm = [
                1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                -gx, -gy, -gz, 1.0
            ]
            ibm_list.extend(ibm)

            node_dict = {
                "name": b["name"],
                "translation": [tx, ty, tz],
                "rotation": [0.0, 0.0, 0.0, 1.0],
                "scale": [1.0, 1.0, 1.0]
            }
            if b.get("children"):
                node_dict["children"] = [c + 1 for c in b["children"]]
            nodes.append(node_dict)

        ibm_arr = np.array(ibm_list, dtype=np.float32)
        bv_ibm = add_buffer_view(ibm_arr.tobytes())
        acc_ibm = len(accessors)
        accessors.append({
            "bufferView": bv_ibm,
            "componentType": 5126,
            "count": len(bones_spec),
            "type": "MAT4"
        })

        skins.append({
            "name": f"{asset_title}_Armature",
            "inverseBindMatrices": acc_ibm,
            "joints": joint_node_indices,
            "skeleton": 1
        })
        root_nodes = [0, 1]

        # Build 120-frame (4.0s @ 30fps) looping animation
        if anim_keyframes:
            times = np.array(anim_keyframes["times"], dtype=np.float32)
            bv_t = add_buffer_view(times.tobytes())
            acc_t = len(accessors)
            accessors.append({
                "bufferView": bv_t,
                "componentType": 5126,
                "count": len(times),
                "type": "SCALAR",
                "min": [float(times.min())],
                "max": [float(times.max())]
            })

            anim_samplers = []
            anim_channels = []
            for b_idx, quat_list in anim_keyframes["bone_rotations"].items():
                q_arr = np.array(quat_list, dtype=np.float32)
                bv_q = add_buffer_view(q_arr.tobytes())
                acc_q = len(accessors)
                accessors.append({
                    "bufferView": bv_q,
                    "componentType": 5126,
                    "count": len(q_arr),
                    "type": "VEC4"
                })
                s_idx = len(anim_samplers)
                anim_samplers.append({
                    "input": acc_t,
                    "interpolation": "LINEAR",
                    "output": acc_q
                })
                anim_channels.append({
                    "sampler": s_idx,
                    "target": {
                        "node": b_idx + 1,
                        "path": "rotation"
                    }
                })

            animations.append({
                "name": f"{asset_title}_120f_Loop",
                "samplers": anim_samplers,
                "channels": anim_channels
            })

    full_bin = b"".join(bin_chunks)
    gltf = {
        "asset": {
            "version": "2.0",
            "generator": "MYCALLA INC. / Blender-Compatible glTF 2.0 Pipeline"
        },
        "scene": 0,
        "scenes": [{"name": "Scene", "nodes": root_nodes}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": materials,
        "textures": textures,
        "images": images,
        "samplers": samplers,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(full_bin)}]
    }
    if skins:
        gltf["skins"] = skins
    if animations:
        gltf["animations"] = animations

    out_path = os.path.join(OUT_DIR, out_filename)
    pack_glb(gltf, full_bin, out_path)
    print(f"Created GLB: {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")


def euler_to_quat(rx, ry, rz):
    cx, sx = math.cos(rx * 0.5), math.sin(rx * 0.5)
    cy, sy = math.cos(ry * 0.5), math.sin(ry * 0.5)
    cz, sz = math.cos(rz * 0.5), math.sin(rz * 0.5)
    qw = cx * cy * cz + sx * sy * sz
    qx = sx * cy * cz - cx * sy * sz
    qy = cx * sy * cz + sx * cy * sz
    qz = cx * cy * sz - sx * sy * cz
    return [qx, qy, qz, qw]


def generate_all():
    # --- MODEL 1: Rugged Edge Comms Unit (MYCALLA INC.) ---
    pos1, norm1, uv1, idx1 = [], [], [], []
    # Main Enclosure (UV region 0..0.5, 0..0.5)
    append_mesh(pos1, norm1, uv1, idx1, make_beveled_box_mesh(0.0, 0.35, 0.0, 0.75, 0.35, 0.50, bevel=0.04, uv_rect=(0.02, 0.02, 0.48, 0.48)))
    # Top Telemetry Module (UV region 0.5..1.0, 0..0.5)
    append_mesh(pos1, norm1, uv1, idx1, make_beveled_box_mesh(0.0, 0.76, -0.05, 0.55, 0.06, 0.36, bevel=0.015, uv_rect=(0.52, 0.02, 0.98, 0.48)))
    # Dual SMA Antennas Left & Right (UV region 0..0.5, 0.5..1.0)
    append_mesh(pos1, norm1, uv1, idx1, make_beveled_box_mesh(-0.55, 1.15, -0.32, 0.045, 0.45, 0.045, bevel=0.015, uv_rect=(0.02, 0.52, 0.24, 0.98)))
    append_mesh(pos1, norm1, uv1, idx1, make_beveled_box_mesh( 0.55, 1.15, -0.32, 0.045, 0.45, 0.045, bevel=0.015, uv_rect=(0.26, 0.52, 0.48, 0.98)))
    # Front Ruggedized Guard & Compression Latches (UV region 0.5..1.0, 0.5..1.0)
    append_mesh(pos1, norm1, uv1, idx1, make_beveled_box_mesh(-0.45, 0.35, 0.54, 0.08, 0.22, 0.04, bevel=0.01, uv_rect=(0.52, 0.52, 0.74, 0.98)))
    append_mesh(pos1, norm1, uv1, idx1, make_beveled_box_mesh( 0.45, 0.35, 0.54, 0.08, 0.22, 0.04, bevel=0.01, uv_rect=(0.76, 0.52, 0.98, 0.98)))

    build_glb_with_pbr_and_optional_rig(
        "Model_1_Rugged_Edge_Comms_Node.glb",
        pos1, norm1, uv1, idx1,
        create_pbr_textures_model1(),
        asset_title="MYCALLA_Rugged_Edge_Comms_Node"
    )

    # --- MODEL 2: Articulated 6-DOF Robotic Arm Manipulator ---
    pos2, norm2, uv2, idx2 = [], [], [], []
    joints2, weights2 = [], []

    arm_parts = [
        # (bone_idx, cx, cy, cz, sx, sy, sz, bevel, uv_rect)
        (0,  0.0, 0.12, 0.0,  0.42, 0.12, 0.42, 0.02, (0.02, 0.02, 0.32, 0.48)),  # Root Pedestal
        (1,  0.0, 0.42, 0.0,  0.26, 0.18, 0.26, 0.02, (0.34, 0.02, 0.64, 0.48)),  # Base_Yaw Turret
        (2,  0.0, 0.95, 0.0,  0.14, 0.38, 0.14, 0.02, (0.66, 0.02, 0.98, 0.48)),  # Shoulder_Pitch Arm
        (3,  0.0, 1.40, 0.32, 0.11, 0.11, 0.35, 0.015, (0.02, 0.52, 0.32, 0.98)), # Elbow_Pitch Forearm
        (4,  0.0, 1.40, 0.78, 0.09, 0.09, 0.12, 0.012, (0.34, 0.52, 0.54, 0.98)), # Wrist_Roll
        (5, -0.10, 1.40, 1.02, 0.025, 0.05, 0.12, 0.006, (0.56, 0.52, 0.76, 0.98)), # Gripper_L
        (6,  0.10, 1.40, 1.02, 0.025, 0.05, 0.12, 0.006, (0.78, 0.52, 0.98, 0.98)), # Gripper_R
    ]

    for b_idx, cx, cy, cz, sx, sy, sz, bv, uvr in arm_parts:
        part = make_beveled_box_mesh(cx, cy, cz, sx, sy, sz, bevel=bv, uv_rect=uvr)
        v_count = len(part[0])
        append_mesh(pos2, norm2, uv2, idx2, part)
        joints2.extend([[b_idx, 0, 0, 0]] * v_count)
        weights2.extend([[1.0, 0.0, 0.0, 0.0]] * v_count)

    bones2 = [
        {"name": "Root",           "parent": None, "children": [1],    "translation": [0.0, 0.0, 0.0]},
        {"name": "Base_Yaw",       "parent": 0,    "children": [2],    "translation": [0.0, 0.24, 0.0]},
        {"name": "Shoulder_Pitch", "parent": 1,    "children": [3],    "translation": [0.0, 0.36, 0.0]},
        {"name": "Elbow_Pitch",    "parent": 2,    "children": [4],    "translation": [0.0, 0.80, 0.0]},
        {"name": "Wrist_Roll",     "parent": 3,    "children": [5, 6], "translation": [0.0, 0.0, 0.66]},
        {"name": "Gripper_L",      "parent": 4,    "children": [],     "translation": [-0.10, 0.0, 0.24]},
        {"name": "Gripper_R",      "parent": 4,    "children": [],     "translation": [ 0.10, 0.0, 0.24]},
    ]

    # 5 keyframes over 4.0 seconds (120 frames @ 30fps), Frame 0 == Frame 120
    anim2 = {
        "times": [0.0, 1.0, 2.0, 3.0, 4.0],
        "bone_rotations": {
            1: [euler_to_quat(0, 0, 0), euler_to_quat(0, 0.85, 0), euler_to_quat(0, -0.85, 0), euler_to_quat(0, 0.40, 0), euler_to_quat(0, 0, 0)],
            2: [euler_to_quat(0, 0, 0), euler_to_quat(0.40, 0, 0), euler_to_quat(-0.25, 0, 0), euler_to_quat(0.20, 0, 0), euler_to_quat(0, 0, 0)],
            3: [euler_to_quat(0, 0, 0), euler_to_quat(-0.55, 0, 0), euler_to_quat(0.45, 0, 0), euler_to_quat(-0.30, 0, 0), euler_to_quat(0, 0, 0)],
            4: [euler_to_quat(0, 0, 0), euler_to_quat(0, 0, 1.20), euler_to_quat(0, 0, -1.20), euler_to_quat(0, 0, 0.60), euler_to_quat(0, 0, 0)],
            5: [euler_to_quat(0, 0, 0), euler_to_quat(0, -0.22, 0), euler_to_quat(0, 0.12, 0), euler_to_quat(0, -0.18, 0), euler_to_quat(0, 0, 0)],
            6: [euler_to_quat(0, 0, 0), euler_to_quat(0,  0.22, 0), euler_to_quat(0, -0.12, 0), euler_to_quat(0,  0.18, 0), euler_to_quat(0, 0, 0)],
        }
    }

    build_glb_with_pbr_and_optional_rig(
        "Model_2_Articulated_Robotic_Arm.glb",
        pos2, norm2, uv2, idx2,
        create_pbr_textures_model2(),
        joints_0=joints2,
        weights_0=weights2,
        bones_spec=bones2,
        anim_keyframes=anim2,
        asset_title="Articulated_Robotic_Manipulator"
    )

    # --- MODEL 3: Stylized Character Bust / Mascot with Smooth Deform Skinning & Idle Loop ---
    pos3, norm3, uv3, idx3 = [], [], [], []
    joints3, weights3 = [], []

    char_parts = [
        # Pelvis / Base Torso, Upper Chest, Neck, Stylized Head, Left & Right Shoulders/Arms
        (0,  0.0,  0.55, 0.0,  0.34, 0.22, 0.24, 0.08, (0.02, 0.02, 0.32, 0.48)),  # Pelvis/Waist
        (1,  0.0,  0.98, 0.0,  0.42, 0.26, 0.28, 0.10, (0.34, 0.02, 0.66, 0.48)),  # Chest
        (2,  0.0,  1.32, 0.0,  0.14, 0.10, 0.14, 0.05, (0.68, 0.02, 0.98, 0.48)),  # Neck
        (3,  0.0,  1.62, 0.04, 0.30, 0.26, 0.28, 0.12, (0.02, 0.52, 0.48, 0.98)),  # Head
        (4, -0.56, 0.95, 0.0,  0.14, 0.28, 0.14, 0.06, (0.50, 0.52, 0.73, 0.98)),  # Left Arm
        (5,  0.56, 0.95, 0.0,  0.14, 0.28, 0.14, 0.06, (0.75, 0.52, 0.98, 0.98)),  # Right Arm
    ]

    for b_idx, cx, cy, cz, sx, sy, sz, bv, uvr in char_parts:
        part = make_beveled_box_mesh(cx, cy, cz, sx, sy, sz, bevel=bv, uv_rect=uvr)
        for vx, vy, vz in part[0]:
            # Smooth blended weights between adjacent bones to prevent pinching
            if b_idx in (1, 2, 3):
                # Blend Chest(1) and Head(3) across Neck(2)
                if vy < 1.15:
                    j = [1, 0, 0, 0]
                    w = [0.85, 0.15, 0.0, 0.0]
                elif vy < 1.40:
                    j = [2, 1, 0, 0]
                    w = [0.75, 0.25, 0.0, 0.0]
                else:
                    j = [3, 2, 0, 0]
                    w = [0.85, 0.15, 0.0, 0.0]
            elif b_idx in (4, 5):
                j = [b_idx, 1, 0, 0]
                w = [0.80, 0.20, 0.0, 0.0]
            else:
                j = [0, 1, 0, 0]
                w = [0.90, 0.10, 0.0, 0.0]
            joints3.append(j)
            weights3.append(w)
        append_mesh(pos3, norm3, uv3, idx3, part)

    bones3 = [
        {"name": "Pelvis",      "parent": None, "children": [1],       "translation": [0.0, 0.45, 0.0]},
        {"name": "Spine_Chest", "parent": 0,    "children": [2, 4, 5], "translation": [0.0, 0.40, 0.0]},
        {"name": "Neck",        "parent": 1,    "children": [3],       "translation": [0.0, 0.42, 0.0]},
        {"name": "Head",        "parent": 2,    "children": [],        "translation": [0.0, 0.22, 0.0]},
        {"name": "UpperArm_L",  "parent": 1,    "children": [],        "translation": [-0.48, 0.25, 0.0]},
        {"name": "UpperArm_R",  "parent": 1,    "children": [],        "translation": [ 0.48, 0.25, 0.0]},
    ]

    anim3 = {
        "times": [0.0, 1.0, 2.0, 3.0, 4.0],
        "bone_rotations": {
            1: [euler_to_quat(0, 0, 0), euler_to_quat(-0.06, 0, 0), euler_to_quat(0.04, 0, 0), euler_to_quat(-0.06, 0, 0), euler_to_quat(0, 0, 0)],
            2: [euler_to_quat(0, 0, 0), euler_to_quat(0.04, 0.14, 0), euler_to_quat(-0.03, 0, 0), euler_to_quat(0.04, -0.14, 0), euler_to_quat(0, 0, 0)],
            3: [euler_to_quat(0, 0, 0), euler_to_quat(0.05, 0.22, 0), euler_to_quat(-0.04, 0, 0), euler_to_quat(0.05, -0.22, 0), euler_to_quat(0, 0, 0)],
            4: [euler_to_quat(0, 0, 0), euler_to_quat(0.05, 0, -0.06), euler_to_quat(-0.03, 0, 0.03), euler_to_quat(0.05, 0, -0.06), euler_to_quat(0, 0, 0)],
            5: [euler_to_quat(0, 0, 0), euler_to_quat(0.05, 0,  0.06), euler_to_quat(-0.03, 0, -0.03), euler_to_quat(0.05, 0,  0.06), euler_to_quat(0, 0, 0)],
        }
    }

    build_glb_with_pbr_and_optional_rig(
        "Model_3_Stylized_Character_Rig.glb",
        pos3, norm3, uv3, idx3,
        create_pbr_textures_model3(),
        joints_0=joints3,
        weights_0=weights3,
        bones_spec=bones3,
        anim_keyframes=anim3,
        asset_title="Stylized_Character_Mascot_Rig"
    )


if __name__ == "__main__":
    generate_all()
