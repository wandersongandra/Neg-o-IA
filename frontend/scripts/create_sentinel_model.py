"""Generate the original articulated Neg-o-IA sentinel avatar as a GLB asset."""
import bpy
import math
from mathutils import Vector
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "public" / "models" / "sentinel.glb"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    pass

def material(name, color, metallic=0.0, roughness=0.35, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    if metallic > 0.4:
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 72.0
        noise.inputs["Detail"].default_value = 2.5
        noise.inputs["Roughness"].default_value = .72
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .12
        bump.inputs["Distance"].default_value = .009
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        bsdf.inputs["Coat Weight"].default_value = .22
        bsdf.inputs["Coat Roughness"].default_value = .24
    return mat

steel = material("Graphite titanium", (0.075, 0.088, 0.095), .82, .27)
light_steel = material("Brushed titanium", (0.34, 0.36, 0.35), .88, .23)
dark = material("Recessed ceramic", (0.009, 0.012, 0.014), .52, .32)
red = material("Optical crimson", (0.18, 0.006, 0.003), .35, .22, (.8, .008, .001), 2.5)
black_glass = material("Optic glass", (0.008, 0.004, 0.004), .28, .16, (.18, .001, .001), .8)

head = bpy.data.objects.new("HeadPivot", None)
bpy.context.collection.objects.link(head)
head.empty_display_type = "PLAIN_AXES"
head.empty_display_size = .12

def attach(obj, mat, bevel=0.04, parent=head):
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("Machined edge", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        mod2 = obj.modifiers.new("Corner normals", "WEIGHTED_NORMAL")
        obj.parent = parent
    return obj

def cube(name, loc, scale, mat, bevel=.04):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return attach(ob, mat, bevel)

def uv(name, loc, scale, mat, parent=head, segments=48):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=24, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    for face in ob.data.polygons:
        face.use_smooth = True
    return attach(ob, mat, 0, parent)

def cyl(name, loc, radius, depth, mat, rotation=(math.pi/2, 0, 0), parent=head):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=depth, location=loc, rotation=rotation)
    ob = bpy.context.object
    ob.name = name
    bevel = ob.modifiers.new("Machined edge", "BEVEL")
    bevel.width = .018
    bevel.segments = 3
    ob.modifiers.new("Corner normals", "WEIGHTED_NORMAL")
    return attach(ob, mat, 0, parent)

def face_plate(name, outline, center_z, front_y, depth, mat, bevel_width):
    count = len(outline)
    vertices = [(x, front_y, center_z + z) for x, z in outline]
    vertices += [(x, front_y + depth, center_z + z) for x, z in outline]
    faces = [tuple(range(count)), tuple(range(count * 2 - 1, count - 1, -1))]
    faces += [
        (index, (index + 1) % count, (index + 1) % count + count, index + count)
        for index in range(count)
    ]
    mesh = bpy.data.meshes.new(name + " geometry")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(ob)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for face in mesh.polygons:
        face.use_smooth = False
    return attach(ob, mat, bevel_width)

# Armor shell, face plane, side cheek plates and rear head cap.
uv("Cranial armored shell", (0, 0, .15), (.70, .46, .91), steel, segments=64)
mask_outline = [(-.49, .57), (-.43, .83), (-.23, .99), (0, 1.04), (.23, .99), (.43, .83), (.49, .57), (.43, .08), (.32, -.43), (.18, -.70), (0, -.82), (-.18, -.70), (-.32, -.43), (-.43, .08)]
face_plate("Face shield", mask_outline, -.02, -.43, .11, light_steel, .035)
inner_outline = [(x * .79, z * .82) for x, z in mask_outline]
face_plate("Recessed face", inner_outline, -.05, -.555, .035, dark, .012)
for side in (-1, 1):
    cube("Temple armor", (side*.59, -.16, -.02), (.18, .28, .62), steel, .055)
    cheek = cube("Cheek blade", (side*.40, -.48, -.32), (.19, .11, .36), light_steel, .04)
    cheek.rotation_euler[1] = side * -0.17
    cube("Jaw hinge", (side*.37, -.5, -.58), (.16, .18, .16), dark, .035)
    # multi-piece eye surrounds and optics facing front (-Y)
    cube("Optical socket", (side*.24, -.575, .18), (.35, .095, .17), dark, .065)
    cube("Optic glass lens", (side*.24, -.635, .18), (.252, .035, .065), black_glass, .028)
    cube("Crimson optical core", (side*.24, -.659, .18), (.218, .018, .026), red, .012)
    brow = cube("Brow ridge", (side*.24, -.55, .30), (.40, .12, .075), steel, .03)
    brow.rotation_euler[1] = side * -0.12
    cyl("Audio sensor", (side*.70, -.08, .05), .10, .10, dark)
    cyl("Sensor rim", (side*.75, -.08, .05), .067, .10, steel)
    for z in (-.22, -.34, -.46):
        cube("Jaw vent", (side*.18, -.574, z), (.09, .025, .025), light_steel, .01)
    # Layered cheek armor and recessed fasteners break up the broad face planes.
    cheek_panel = cube("Layered cheek armor", (side*.34, -.535, -.20), (.14, .045, .15), steel, .025)
    cheek_panel.rotation_euler[1] = side * .24
    uv("Cheek fastener", (side*.31, -.568, -.16), (.018, .012, .018), light_steel, segments=12)

# Nose bridge and articulated lower jaw: jaw mesh is driven around its hinge in the UI.
cube("Central brow bridge", (0, -.535, .12), (.105, .09, .27), light_steel, .025)
cube("Nasal plate", (0, -.57, -.14), (.13, .10, .18), steel, .045)
# A recessed mouth cavity remains visible while the lower jaw articulates.
cube("Mouth recess", (0, -.575, -.405), (.43, .055, .105), dark, .025)
for tooth_x in (-.15, -.05, .05, .15):
    cube("Machined mouth grille", (tooth_x, -.614, -.405), (.024, .018, .064), light_steel, .009)
jaw = cube("JawPivot", (0, -.38, -.51), (.69, .20, .27), steel, .07)
jaw.name = "JawPivot"
# Put hinge origin on bottom rear of the jaw to allow natural opening.
bpy.context.scene.cursor.location = (0, -.38, -.38)
bpy.context.view_layer.objects.active = jaw
jaw.select_set(True)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
jaw.select_set(False)
for side in (-1, 1):
    vent = cube("Jaw grille", (side*.11, -.50, -.52), (.07, .03, .14), dark, .015)
    vent.parent = jaw
    vent.matrix_parent_inverse = jaw.matrix_world.inverted()
    jaw_bolt = uv("Jaw actuator cap", (side*.30, -.50, -.51), (.042, .024, .042), light_steel, segments=16)
    jaw_bolt.parent = jaw
    jaw_bolt.matrix_parent_inverse = jaw.matrix_world.inverted()
# Neck and a small visible clavicle base.
cyl("Neck coupling", (0, .0, -.88), .29, .24, light_steel, rotation=(0, 0, 0))
cube("Neck column", (0, .03, -1.06), (.33, .34, .35), steel, .05)
cube("Collar", (0, .0, -1.25), (1.0, .46, .16), dark, .05)

# A small line of forehead machining and restrained panel details.
for x in (-.10, 0, .10):
    cube("Forehead seam", (x, -.493, .55), (.012, .018, .09), dark, .004)
for side in (-1, 1):
    for z in (.46, .54):
        uv("Fastener", (side*.53, -.40, z), (.025, .018, .025), light_steel, segments=16)

# Parent any top-level mesh pieces that were not attached through helper (to HeadPivot).
for ob in list(bpy.context.scene.objects):
    if ob.type == "MESH" and ob.parent is None:
        ob.parent = head

# Compact scene settings for reproducible realtime rendering.
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = True
scene.world.color = (.035, .035, .035)
# Camera + studio lights are preview-only and excluded from exported avatar.
bpy.ops.object.camera_add(location=(0, -4.4, -.05), rotation=(math.radians(90), 0, 0))
camera = bpy.context.object
camera.name = "Preview camera"
scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = 2.8
for loc, energy, size in [((-2, -3, 2), 250, 3), ((2, -2, .4), 170, 2), ((0, 1, 1), 320, 2)]:
    bpy.ops.object.light_add(type="AREA", location=loc)
    light = bpy.context.object
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    direction = Vector((0, 0, -.1)) - light.location
    light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

# Export only the original avatar meshes and rig pivots. Render preview separately.
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.context.view_layer.objects.active = head
bpy.ops.object.select_all(action="DESELECT")
for ob in bpy.context.scene.objects:
    if ob.name in {"HeadPivot", "JawPivot"} or (ob.type == "MESH" and ob.name not in {"Preview camera"}):
        if ob.type == "MESH" and (ob.name.startswith("Preview") or ob.type == "LIGHT"):
            continue
        ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", use_selection=True, export_apply=True)
scene.render.filepath = str(OUT.with_suffix(".png"))
bpy.ops.render.render(write_still=True)
