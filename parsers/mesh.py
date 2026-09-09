from ..data import VertexData, FaceData
from ..utils import fix_pos, fix_uv, clean_name

class MeshParser:
    def __init__(self, max_influences: int = 4, normalize_weights: bool = True, export_shapekeys: bool = True):
        self.max_influences = max_influences if max_influences > 0 else 999
        self.normalize_weights = normalize_weights
        self.export_shapekeys = export_shapekeys

    def parse(self, obj):
        mesh = obj.data
        uv_layer = mesh.uv_layers.active.data if mesh.uv_layers else None

        vertices = self._parse_vertices(mesh)
        loops, faces = self._parse_faces(mesh, uv_layer)
        shapekey_names = self._collect_shapekey_names(mesh)

        if not self.export_shapekeys:
            shapekey_names = []
            for v in vertices:
                v.deltas = {}

        return vertices, loops, faces, shapekey_names

    def _parse_vertices(self, mesh):
        basis = None
        if mesh.shape_keys:
            basis = mesh.shape_keys.key_blocks[0]

        vertices = []
        for i, v in enumerate(mesh.vertices):
            weights = self._collect_weights(v)
            deltas = self._collect_deltas(i, basis, mesh) if basis else {}
            vertices.append(VertexData(fix_pos(v.co), weights, deltas))
        return vertices

    def _collect_weights(self, vertex):
        wdict = {g.group: g.weight for g in vertex.groups if g.weight > 1e-5}

        if self.normalize_weights and wdict:
            total = sum(wdict.values())
            if total > 0:
                wdict = {k: val / total for k, val in wdict.items()}

        if len(wdict) > self.max_influences:
            sorted_w = sorted(wdict.items(), key=lambda x: x[1], reverse=True)[:self.max_influences]
            total = sum(w for _, w in sorted_w)
            wdict = {k: w / total for k, w in sorted_w} if total > 0 else {}

        return wdict

    def _collect_deltas(self, index, basis, mesh):
        deltas = {}
        base_co = basis.data[index].co
        for kb in mesh.shape_keys.key_blocks[1:]:
            delta = kb.data[index].co - base_co
            if delta.length > 1e-6:
                deltas[clean_name(kb.name)] = fix_pos(delta)
        return deltas

    def _parse_faces(self, mesh, uv_layer):
        loops = []
        faces = []
        for poly in mesh.polygons:
            if poly.loop_total not in (3, 4):
                continue
            face_loops = []
            for li in poly.loop_indices:
                loop = mesh.loops[li]
                uv = fix_uv(uv_layer[li].uv) if uv_layer else (0.0, 0.0)
                loops.append({"vertex_index": loop.vertex_index, "uv": uv})
                face_loops.append(len(loops) - 1)
            faces.append(FaceData(poly.material_index, face_loops))
        return loops, faces

    def _collect_shapekey_names(self, mesh):
        if not mesh.shape_keys:
            return []
        return [clean_name(kb.name) for kb in mesh.shape_keys.key_blocks[1:]]