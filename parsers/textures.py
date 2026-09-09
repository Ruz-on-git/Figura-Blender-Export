import os
from base64 import b64encode

import bpy

from ..utils import clean_name

class TextureParser:
    def parse(self, obj) -> list:
        textures = []
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or not mat.use_nodes:
                textures.append(self._solid_color((1, 0, 1, 1), mat.name if mat else "null"))
                continue

            out = mat.node_tree.get_output_node("ALL")
            if not out:
                textures.append(self._solid_color((1, 0, 1, 1), mat.name))
                continue

            surface = None
            for link in mat.node_tree.links:
                if link.to_node == out and link.to_socket.name == "Surface":
                    surface = link.from_node
                    break

            if surface is None:
                textures.append(self._solid_color((1, 0, 1, 1), mat.name))
                continue

            if surface.bl_idname == "ShaderNodeTexImage" and surface.image:
                textures.append(self._image_to_b64(surface.image))
                continue

            if surface.bl_idname == "ShaderNodeBsdfPrincipled":
                color_in = surface.inputs.get("Base Color")
                if color_in and color_in.is_linked:
                    tex_node = color_in.links[0].from_node
                    if tex_node.bl_idname == "ShaderNodeTexImage" and tex_node.image:
                        textures.append(self._image_to_b64(tex_node.image))
                        continue
                col = color_in.default_value[:4] if color_in else (0.8, 0.8, 0.8, 1)
                textures.append(self._solid_color(col, mat.name))
                continue

            textures.append(self._solid_color((1, 0, 1, 1), mat.name))
        return textures

    def _image_to_b64(self, image) -> dict:
        filepath = bpy.path.abspath(image.filepath)
        temp = False
        if not os.path.exists(filepath) or image.packed_file:
            filepath = os.path.join(bpy.app.tempdir, f"{image.name}.png")
            image.save_render(filepath)
            temp = True

        with open(filepath, "rb") as f:
            data = b64encode(f.read()).decode("ascii")

        if temp:
            try:
                os.remove(filepath)
            except OSError:
                pass

        name = os.path.splitext(image.name)[0]
        return {"name": clean_name(name), "source": f"data:image/png;base64,{data}"}

    def _solid_color(self, rgba, name) -> dict:
        img = bpy.data.images.new(f"solid_{name}", 1, 1)
        img.pixels = list(rgba)
        img.file_format = "PNG"
        tex = self._image_to_b64(img)
        bpy.data.images.remove(img)
        return tex