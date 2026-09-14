import math
from uuid import uuid4
from collections import defaultdict

from .serializers import to_json

class BBModelBuilder:

    def build(self, name, bones, vertices, loops, faces, textures, mesh_uuid, animations=None) -> str:
        bone_cubes = []
        outliner = []
        bone_uuid_map = {}

        def add_bone(bone):
            bone_uuid_map[bone.name] = bone.uuid

            direction = bone.tail - bone.head
            length = max(direction.length, 1.0)
            yaw = math.degrees(math.atan2(direction.x, direction.z))
            pitch = math.degrees(math.atan2(math.sqrt(direction.x ** 2 + direction.z ** 2), direction.y))

            cube_uuid = str(uuid4())
            cube = {
                "name": "bone_helper",
                "type": "cube",
                "uuid": cube_uuid,
                "color": 0,
                "origin": [bone.head.x, bone.head.y, bone.head.z],
                "from": [bone.head.x - 0.25, bone.head.y, bone.head.z - 0.25],
                "to": [bone.head.x + 0.25, bone.head.y + length, bone.head.z + 0.25],
                "rotation": [pitch, yaw, 0],
                "faces": {
                    side: {"uv": [0, 0, 1, 1]}
                    for side in ("north", "east", "south", "west", "up", "down")
                },
            }
            bone_cubes.append(cube)

            group = {
                "name": bone.name,
                "uuid": bone.uuid,
                "origin": [bone.head.x, bone.head.y, bone.head.z],
                "children": [add_bone(child) for child in bone.children],
            }
            group["children"].append(cube_uuid)
            return group

        for bone in bones:
            outliner.append(add_bone(bone))

        mesh_elem = self._build_mesh_element(mesh_uuid, vertices, loops, faces)
        outliner.append(mesh_uuid)

        bbmodel = {
            "meta": {
                "format_version": "4.5",
                "model_format": "free",
                "box_uv": False,
            },
            "name": name,
            "resolution": {"width": 1, "height": 1},
            "outliner": outliner,
            "elements": bone_cubes + [mesh_elem],
            "textures": textures,
            "animations": self._build_animations_section(animations or [], bone_uuid_map, name),
        }
        return to_json(bbmodel)

    def _build_mesh_element(self, mesh_uuid, vertices, loops, faces):
        mesh_elem = {
            "name": "Mesh",
            "type": "mesh",
            "uuid": mesh_uuid,
            "origin": [0, 0, 0],
            "rotation": [0, 0, 0],
            "vertices": {
                str(i): [v.pos.x, v.pos.y, v.pos.z] for i, v in enumerate(vertices)
            },
            "faces": {},
        }

        for face_idx, face in enumerate(faces):
            mesh_elem["faces"][str(face_idx)] = {
                "vertices": [str(loops[li]["vertex_index"]) for li in face.loop_indices],
                "uv": {
                    str(loops[li]["vertex_index"]): list(loops[li]["uv"])
                    for li in face.loop_indices
                },
                "texture": face.material_index,
            }
        return mesh_elem

    def _build_animations_section(self, animations, bone_uuid_map, mesh_name):
        result = []

        for anim in animations:
            animators = {}

            # Bone keyframes
            for bone_name, keyframes in anim.animators.items():
                uuid = bone_uuid_map.get(bone_name)
                if not uuid:
                    continue

                channels = {"position": [], "rotation": [], "scale": []}
                for kf in keyframes:
                    channels[kf.channel].append(
                        {
                            "time": round(kf.time, 4),
                            "channel": kf.channel,
                            "interpolation": "linear",
                            "data_points": [{
                                "x": round(kf.data[0], 4),
                                "y": round(kf.data[1], 4),
                                "z": round(kf.data[2], 4),
                            }],
                        }
                    )

                animators[uuid] = {
                    "name": bone_name,
                    "type": "bone",
                    "keyframes": (channels["position"] + channels["rotation"] + channels["scale"]),
                }

            # Blendshape events
            if anim.shape_keyframes:
                by_shape = defaultdict(list)
                for time, sk_name, value in anim.shape_keyframes:
                    by_shape[sk_name].append((round(time, 5), value))

                timed_events = []

                for sk_name, kfs in by_shape.items():
                    kfs = sorted(kfs, key=lambda x: x[0])

                    for i, (t, value) in enumerate(kfs):
                        if i + 1 < len(kfs):
                            next_t, next_value = kfs[i + 1]
                            duration = max(next_t - t, 0.0)
                            script = (f'Mesh["{mesh_name}"].setBlendShape("{sk_name}", {round(next_value, 4)}, {round(duration, 4)})')
                        else:
                            script = (f'Mesh["{mesh_name}"].setBlendShape("{sk_name}", {round(value, 4)}, 0)')
                        timed_events.append((t, script))

                # Group scripts that happen on the exact same frame
                by_time = defaultdict(list)
                for t, script in timed_events:
                    by_time[t].append(script)

                timeline_kfs = []
                for t in sorted(by_time.keys()):
                    full_script = "; ".join(by_time[t])
                    timeline_kfs.append({
                        "channel": "timeline",
                        "time": t,
                        "interpolation": "linear",
                        "data_points": [{"script": full_script}],
                    })

                animators["effects"] = {
                    "name": "Effects",
                    "type": "2",
                    "keyframes": timeline_kfs,
                }

            result.append({
                "name": anim.name,
                "loop": anim.loop,
                "length": round(anim.length, 4),
                "snapping": 24,
                "animators": animators,
            })

        return result