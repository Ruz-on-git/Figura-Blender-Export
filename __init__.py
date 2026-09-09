bl_info = {
    "name": "Figura Mesh Exporter",
    "author": "Ruz (based on KitCat962)",
    "version": (0, 2, 0),
    "blender": (5, 2, 0),
    "location": "File > Export > Figura Avatar",
    "description": "Exports models for figura with blendshapes, bones and animations.",
    "category": "Import-Export",
}

import os
from uuid import uuid4

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ExportHelper
from bpy.types import Operator

from .parsers import MeshParser, BoneParser, TextureParser, AnimationParser
from .builders.bbmodel import BBModelBuilder
from .builders.meshdata import MeshDataBuilder

class EXPORT_OT_figura_avatar(Operator, ExportHelper):
    bl_idname = "export.figura_avatar_opt"
    bl_label = "Export Figura Avatar"
    bl_options = {"PRESET", "UNDO"}

    filename_ext = ".bbmodel"
    filter_glob: StringProperty(default="*.bbmodel;*.lua", options={"HIDDEN"})

    export_driver: BoolProperty(name="Also export driver script", default=True)
    max_influences: IntProperty(name="Max bone influences", default=4, min=0, max=8)
    normalize_weights: BoolProperty(name="Normalize weights", default=True)
    export_shapekeys: BoolProperty(name="Export shape keys", default=True)
    export_animations: BoolProperty(name="Export animations", default=True)

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != "MESH":
            self.report({"ERROR"}, "Select a Mesh object")
            return {"CANCELLED"}

        arm = obj.find_armature()
        if not arm:
            self.report({"ERROR"}, "Mesh must be parented to an Armature")
            return {"CANCELLED"}

        if not obj.material_slots:
            self.report({"ERROR"}, "Mesh needs at least one material")
            return {"CANCELLED"}

        depsgraph = context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)

        try:
            mesh_parser = MeshParser(
                max_influences=self.max_influences,
                normalize_weights=self.normalize_weights,
                export_shapekeys=self.export_shapekeys,
            )
            vertices, loops, faces, sk_names = mesh_parser.parse(eval_obj)

            textures = TextureParser().parse(obj)
            bones = BoneParser().parse(arm.data)

            animations = []
            if self.export_animations:
                animations = AnimationParser().parse(arm, mesh_obj=obj)


            directory = os.path.dirname(self.filepath)
            basename = os.path.splitext(os.path.basename(self.filepath))[0]
            mesh_uuid = str(uuid4())

            bb_json = BBModelBuilder().build(basename, bones, vertices, loops, faces, textures, mesh_uuid, animations=animations)
            with open(os.path.join(directory, f"{basename}.bbmodel"), "w", encoding="utf-8") as f:
                f.write(bb_json)

            meshdata = MeshDataBuilder().build(obj, vertices, loops, faces, textures, sk_names)
            with open(os.path.join(directory, f"{basename}-MeshData.lua"), "w", encoding="utf-8") as f:
                f.write(meshdata)

            if self.export_driver:
                import shutil

                src = os.path.join(os.path.dirname(__file__), "FiguraMeshDriver.lua")
                dst = os.path.join(directory, "FiguraMeshDriver.lua")
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                else:
                    with open(dst, "w", encoding="utf-8") as f:
                        f.write("-- FiguraMeshDriver.lua not found next to the addon\n")

            self.report({"INFO"}, f"Exported {basename} ({len(animations)} animations)")
            return {"FINISHED"}
        finally:
            eval_obj.to_mesh_clear()


def menu_func(self, context):
    self.layout.operator(EXPORT_OT_figura_avatar.bl_idname, text="Figura Avatar")

def register():
    bpy.utils.register_class(EXPORT_OT_figura_avatar)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)

def unregister():
    try:
        bpy.types.TOPBAR_MT_file_export.remove(menu_func)
    except Exception:
        pass
    try:
        bpy.utils.unregister_class(EXPORT_OT_figura_avatar)
    except Exception:
        pass

if __name__ == "__main__":
    register()