import math
from mathutils import Vector

def fix_pos(v: Vector) -> Vector:
    return Vector((-v.x * 16.0, v.z * 16.0, v.y * 16.0))

def fix_uv(uv):
    return (uv[0], 1.0 - uv[1])

def fix_angle(euler, degrees=True):
    x, y, z = euler[0], euler[1], euler[2]
    if degrees:
        x = math.degrees(x)
        y = math.degrees(y)
        z = math.degrees(z)
    return (x, y, z)

def clean_name(name: str) -> str:
    return name.replace(".", "_").replace(" ", "_").replace("-", "_")