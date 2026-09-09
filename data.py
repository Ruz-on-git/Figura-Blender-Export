from uuid import uuid4
from .utils import clean_name

class VertexData:
    __slots__ = ("pos", "weights", "deltas")

    def __init__(self, pos, weights=None, deltas=None):
        self.pos = pos
        self.weights = weights or {}
        self.deltas = deltas or {}

class FaceData:
    __slots__ = ("material_index", "loop_indices")

    def __init__(self, mat_idx, loops):
        self.material_index = mat_idx
        self.loop_indices = loops

class BoneData:
    __slots__ = ("name", "uuid", "head", "tail", "children")

    def __init__(self, name, head, tail, children=None):
        self.name = clean_name(name)
        self.uuid = str(uuid4())
        self.head = head
        self.tail = tail
        self.children = children or []

class Keyframe:
    __slots__ = ("time", "channel", "data")

    def __init__(self, time, channel, data):
        self.time = time
        self.channel = channel
        self.data = data

class AnimationData:
    __slots__ = ("name", "length", "loop", "animators", "shape_keyframes")

    def __init__(self, name, length, loop="once"):
        self.name = name
        self.length = length
        self.loop = loop
        self.animators = {}
        self.shape_keyframes = []