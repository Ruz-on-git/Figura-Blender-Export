from ..data import BoneData
from ..utils import fix_pos

class BoneParser:

    def parse(self, armature) -> list:
        return [self._recurse(b) for b in armature.bones if not b.parent]

    def _recurse(self, bone):
        return BoneData(
            bone.name,
            fix_pos(bone.head_local),
            fix_pos(bone.tail_local),
            [self._recurse(c) for c in bone.children],
        )