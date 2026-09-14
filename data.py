from uuid import uuid4
from .utils import clean_name

class VertexData:
    __slots__ = ("pos", "weights", "deltas")

    def __init__(self, pos, weights=None, deltas=None):
        self.pos = pos
        self.weights = weights or {}
        self.deltas = deltas or {}

    def __str__(self):
        return (
            f"VertexData("
            f"pos={self.pos}, "
            f"weights={self.weights}, "
            f"deltas={self.deltas}"
            f")"
        )

class FaceData:
    __slots__ = ("material_index", "loop_indices")

    def __init__(self, mat_idx, loops):
        self.material_index = mat_idx
        self.loop_indices = loops

    def __str__(self):
        return (
            f"FaceData("
            f"material_index={self.material_index}, "
            f"loop_indices={self.loop_indices}"
            f")"
        )

class BoneData:
    __slots__ = ("name", "uuid", "head", "tail", "children")

    def __init__(self, name, head, tail, children=None):
        self.name = clean_name(name)
        self.uuid = str(uuid4())
        self.head = head
        self.tail = tail
        self.children = children or []

    def __str__(self):
        return (
            f"BoneData("
            f"name={self.name!r}, "
            f"uuid={self.uuid!r}, "
            f"head={self.head}, "
            f"tail={self.tail}, "
            f"children={len(self.children)}"
            f")"
        )

class Keyframe:
    __slots__ = ("time", "channel", "data")

    def __init__(self, time, channel, data):
        self.time = time
        self.channel = channel
        self.data = data


    def __str__(self):
        return (
            f"Keyframe("
            f"time={self.time:.4f}, "
            f"channel={self.channel!r}, "
            f"data={self.data}"
            f")"
        )

class AnimationData:
    __slots__ = ("name", "length", "loop", "animators", "shape_keyframes")

    def __init__(self, name, length, loop="once"):
        self.name = name
        self.length = length
        self.loop = loop
        self.animators = {}
        self.shape_keyframes = []

    def __str__(self):
        lines = [
            f"AnimationData(",
            f"  name={self.name!r},",
            f"  length={self.length:.4f},",
            f"  loop={self.loop!r},",
            f"  animators={{",
        ]

        for bone_name, keyframes in self.animators.items():
            lines.append(f"    {bone_name!r}: [")

            for keyframe in keyframes:
                lines.append(f"      {keyframe},")

            lines.append("    ],")

        lines.append("  },")

        lines.append("  shape_keyframes=[")

        for keyframe in self.shape_keyframes:
            lines.append(f"    {keyframe},")

        lines.append("  ]")
        lines.append(")")

        return "\n".join(lines)