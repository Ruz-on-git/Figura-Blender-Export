from ..utils import clean_name
from ..parsers.bones import BoneParser
from .serializers import to_lua

class MeshDataBuilder:
    def build(self, obj, vertices, loops, faces, textures, shapekey_names) -> str:
        group_map = self._build_group_map(obj)
        figura_map = self._build_figura_map(faces, textures)

        vertex_data = []
        for vi, vertex in enumerate(vertices):
            loops_for_vert = self._loops_for_vertex(vi, loops, figura_map)
            weights = self._map_weights(vertex, obj, group_map)
            deltas = self._map_deltas(vertex)

            entry = {"loops": loops_for_vert}
            if weights:
                entry["weights"] = weights
            if deltas:
                entry["deltas"] = deltas
            vertex_data.append(entry)

        data = {
            "groupMap": group_map,
            "textureMap": [t["name"] for t in textures],
            "shapeKeys": shapekey_names,
            "vertexData": vertex_data,
        }
        return "return " + to_lua(data)

    def _build_group_map(self, obj):
        group_map = {clean_name(g.name): i + 1 for i, g in enumerate(obj.vertex_groups)}

        all_bones = set()

        def collect_bones(bones):
            for bone in bones:
                all_bones.add(bone.name)
                collect_bones(bone.children)

        armature = obj.find_armature()
        if armature:
            collect_bones(BoneParser().parse(armature.data))

        next_idx = len(group_map) + 1
        for bone_name in sorted(all_bones):
            if bone_name not in group_map:
                group_map[bone_name] = next_idx
                next_idx += 1

        return group_map

    def _build_figura_map(self, faces, textures):
        figura_map = [[] for _ in textures]
        for face in faces:
            for li in face.loop_indices:
                figura_map[face.material_index].append(li)
                if len(face.loop_indices) == 3 and li == face.loop_indices[-1]:
                    figura_map[face.material_index].append(li)
        return figura_map

    def _loops_for_vertex(self, vi, loops, figura_map):
        loops_for_vert = {}
        for tex_idx, tex_loops in enumerate(figura_map):
            matching = [i for i, li in enumerate(tex_loops) if loops[li]["vertex_index"] == vi]
            if matching:
                loops_for_vert[tex_idx + 1] = [x + 1 for x in matching]
        return loops_for_vert

    def _map_weights(self, vertex, obj, group_map):
        if not vertex.weights:
            return None
        weights = {}
        for group_idx, weight in vertex.weights.items():
            group_name = clean_name(obj.vertex_groups[group_idx].name)
            if group_name in group_map:
                weights[group_map[group_name]] = round(weight, 5)
        return weights or None

    def _map_deltas(self, vertex):
        if not vertex.deltas:
            return None
        return {name: [d.x, d.y, d.z] for name, d in vertex.deltas.items()}