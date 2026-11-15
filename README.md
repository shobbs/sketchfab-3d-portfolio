# Sketchfab 3D Generalist Portfolio (`shobbs/sketchfab-3d-portfolio`)

Automated Blender Python (`bpy`) and standalone binary glTF 2.0 (`.glb`) asset generation pipeline for the **hobbstheTiger** Sketchfab 3-Model Portfolio lineup. Designed for 3D Generalist and AI Evaluation workflows where reviewers inspect wireframes, UV layouts, PBR channels, and skeletal hierarchies directly in Sketchfab's 3D Inspector.

- **Author:** Steven Michael Hobbs Torres ([GitHub `@shobbs`](https://github.com/shobbs) | [LinkedIn](https://www.linkedin.com/in/steven-hobbs/) | [Sketchfab `@hobbstheTiger`](https://sketchfab.com/hobbstheTiger))
- **Organization:** [MYCALLA INCORPORADO (MYCALLA INC.)](https://mycallai.github.io/)

## Portfolio Lineup (3-Model Architecture)

| Slot | Asset File | Asset Type | Core Technical Specifications | Live on Sketchfab |
| :--- | :--- | :--- | :--- | :--- |
| **Model 1** | `Model_1_Rugged_Edge_Comms_Node.glb` | Hard-Surface Prop (MYCALLA INC. Rugged Edge AI / Off-Grid Comms Transceiver) | All-quad beveled topology, outward normals, non-overlapping UVs (`0.02` island margin), embedded PBR Metallic-Roughness & Tangent-Space Normal PNG maps | **[View in 3D ↗](https://skfb.ly/pQtVQ)** |
| **Model 2** | `Model_2_Articulated_Robotic_Arm.glb` | Rigged & Animated 6-DOF Robotic Manipulator | Hierarchical 7-bone armature (`Root`, `Base_Yaw`, `Shoulder_Pitch`, `Elbow_Pitch`, `Wrist_Roll`, `Gripper_L`, `Gripper_R`), rigid `1.0` joint skinning (`JOINTS_0` / `WEIGHTS_0`), seamless 120-frame (4.0s @ 30fps) diagnostic loop | **[View in 3D ↗](https://skfb.ly/pQtVY)** |
| **Model 3** | `Model_3_Stylized_Character_Rig.glb` | Stylized Character Bust / Mascot Rig & Idle Loop | Symmetrical all-quad deformation loops, 6-bone upper-body deform rig (`Pelvis`, `Spine_Chest`, `Neck`, `Head`, `UpperArm_L`, `UpperArm_R`) with blended joint weights, 120-frame breathing and look-around idle loop | **[View in 3D ↗](https://skfb.ly/pQtWr)** |

## Repository Structure

- `build_sketchfab_3model_portfolio.py` — Native Blender 3.x / 4.x Python (`bpy`) automation script that procedurally constructs all three assets, applies modifiers, runs Smart UV Projection (`0.02` margin), sets up Principled BSDF materials, rigs armatures, keyframes 120-frame seamless loops, and exports `.glb` binaries.
- `generate_glb_portfolio.py` — Standalone zero-Blender Python generator (`numpy` + `Pillow`) that packs spec-compliant binary glTF 2.0 (`.glb`) files complete with embedded PNG textures, `inverseBindMatrices`, vertex skinning (`JOINTS_0`/`WEIGHTS_0`), and quaternion keyframe animations.
- `.github/workflows/build_glb_release.yml` — Automated GitHub Actions workflow that runs `generate_glb_portfolio.py` on every push and publishes the three `.glb` binary files as downloadable build artifacts.

## Usage

### Option 1: Run Inside Blender (`bpy`)

```bash
blender --background --python build_sketchfab_3model_portfolio.py
```

Or open `build_sketchfab_3model_portfolio.py` inside Blender's **Scripting** workspace and click **Run Script**. All three `.glb` files will export to `~/Desktop/sketchfab_portfolio_exports/`.

### Option 2: Run Standalone Python Generator (No Blender Required)

```bash
pip install numpy pillow
python3 generate_glb_portfolio.py
```

## Sketchfab 3D Settings Checklist

1. Upload all three `.glb` files to [https://sketchfab.com/hobbstheTiger](https://sketchfab.com/hobbstheTiger).
2. Set **Visibility** to **Public** (Free download / Store disabled).
3. In **3D Settings → Scene**, enable **PBR (Metalness)** lighting, select a neutral studio HDRI, and enable **Ground Shadows**.
4. In **3D Settings → Animation** (Models 2 & 3), set the default animation to the `120f_Loop` track and toggle **Autoplay** on.
5. Open each link in an Incognito window and press `I` (**Model Inspector**) to verify **Wireframe**, **Base Color**, **Metalness**, **Roughness**, **Normal**, and **Bones**.
