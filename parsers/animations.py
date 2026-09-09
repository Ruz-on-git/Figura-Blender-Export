import bpy
from mathutils import Vector, Euler, Quaternion
from bpy_extras import anim_utils

from ..data import Keyframe, AnimationData
from ..utils import fix_pos, fix_angle, clean_name

class AnimationParser:
    def __init__(self, fps=None):
        if fps is None:
            fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
        self.fps = fps

    def parse(self, armature_obj, mesh_obj=None) -> list:
        animations = []
        anim_data = armature_obj.animation_data
        if not anim_data:
            return animations

        if anim_data.action:
            slot = getattr(anim_data, "action_slot", None)
            anim = self._process_action(anim_data.action, slot=slot)
            if anim:
                animations.append(anim)

        if mesh_obj and mesh_obj.data.shape_keys:
            mesh_anim = mesh_obj.data.shape_keys.animation_data
            if mesh_anim and mesh_anim.action:
                extra = self._get_fcurves(mesh_anim.action, getattr(mesh_anim, "action_slot", None))

                if extra:
                    if animations:
                        shape_anim = self._process_action(None, name_override="ShapeKeys", extra_fcurves=extra)

                        if shape_anim and shape_anim.shape_keyframes:
                            animations[0].shape_keyframes.extend(shape_anim.shape_keyframes)
                    else:
                        anim = self._process_action(mesh_anim.action, name_override="ShapeKeys")
                        if anim:
                            animations.append(anim)

            if mesh_obj.animation_data and mesh_obj.animation_data.action:
                extra = self._get_fcurves(mesh_obj.animation_data.action, getattr(mesh_obj.animation_data, "action_slot", None))
                if extra:
                    shape_anim = self._process_action(None, name_override="ShapeKeys", extra_fcurves=extra)
                    if shape_anim and shape_anim.shape_keyframes:
                        if animations:
                            animations[0].shape_keyframes.extend(shape_anim.shape_keyframes)
                        else:
                            animations.append(shape_anim)

        for track in anim_data.nla_tracks:
            for strip in track.strips:
                if strip.action:
                    anim = self._process_action(strip.action, name_override=strip.name)
                    if anim:
                        animations.append(anim)

        return animations

    def _process_action(self, action, name_override=None, slot=None, extra_fcurves=None):
        if not action and not extra_fcurves:
            return None

        fcurves = self._get_fcurves(action, slot) if action else []
        if extra_fcurves:
            fcurves.extend(extra_fcurves)

        if not fcurves:
            return None

        name = clean_name(name_override or (action.name if action else "ShapeKeyAnim"))

        try:
            frame_range = action.frame_range if action else (0.0, 1.0)
        except Exception:
            frame_range = (0.0, 1.0)

        frame_start = int(frame_range[0])
        frame_end = int(frame_range[1]) + 1

        length = max((frame_end - frame_start) / self.fps, 0.05)
        anim = AnimationData(name, length)

        bone_curves = self._group_bone_curves(fcurves)
        for bone_name, channels in bone_curves.items():
            keyframes = self._build_bone_keyframes(channels, frame_start, frame_end)
            if keyframes:
                anim.animators[bone_name] = keyframes

        shape_curves = self._group_shape_curves(fcurves)
        for sk_name, fcurve in shape_curves.items():
            for t, value in self._sample_shape_curve(fcurve, frame_start, frame_end):
                anim.shape_keyframes.append((t, sk_name, value))

        return anim

    def _group_bone_curves(self, fcurves):
        bone_curves = {}
        for fcurve in fcurves:
            path = fcurve.data_path
            if not path.startswith('pose.bones["'):
                continue
            try:
                bone_name = path.split('"')[1]
                prop = path.split(".")[-1]
            except Exception:
                continue
            bone_name = clean_name(bone_name)
            if bone_name not in bone_curves:
                bone_curves[bone_name] = {
                    "location": {},
                    "rotation_euler": {},
                    "rotation_quaternion": {},
                    "scale": {},
                }
            bone_curves[bone_name][prop][fcurve.array_index] = fcurve
        return bone_curves

    def _group_shape_curves(self, fcurves):
        shape_curves = {}
        for fcurve in fcurves:
            path = fcurve.data_path
            if 'key_blocks["' in path and path.endswith(".value"):
                try:
                    raw = path.split('"')[1]
                    sk_name = clean_name(raw)
                    shape_curves[sk_name] = fcurve
                except Exception:
                    continue
        return shape_curves

    def _build_bone_keyframes(self, channels, frame_start, frame_end):
        keyframes = []

        def eval_loc(frame):
            loc = Vector((0.0, 0.0, 0.0))
            for i, fc in channels["location"].items():
                loc[i] = fc.evaluate(frame)
            return fix_pos(loc)

        for t, val in self._optimise_channel(channels["location"], eval_loc, frame_start, frame_end):
            keyframes.append(Keyframe(t, "position", (val.x, val.y, val.z)))

        def eval_scale(frame):
            sc = Vector((1.0, 1.0, 1.0))
            for i, fc in channels["scale"].items():
                sc[i] = fc.evaluate(frame)
            return sc

        for t, val in self._optimise_channel(channels["scale"], eval_scale, frame_start, frame_end):
            keyframes.append(Keyframe(t, "scale", (val.x, val.y, val.z)))

        if channels["rotation_euler"]:
            def eval_euler(frame):
                eul = Euler((0.0, 0.0, 0.0))
                for i, fc in channels["rotation_euler"].items():
                    eul[i] = fc.evaluate(frame)
                return fix_angle(eul, degrees=True)

            for t, val in self._optimise_channel(channels["rotation_euler"], eval_euler, frame_start, frame_end, is_rotation=True):
                keyframes.append(Keyframe(t, "rotation", val))

        elif channels["rotation_quaternion"]:
            def eval_quat(frame):
                quat = Quaternion()
                for i, fc in channels["rotation_quaternion"].items():
                    quat[i] = fc.evaluate(frame)
                return fix_angle(quat.to_euler("XYZ"), degrees=True)

            for t, val in self._optimise_channel(channels["rotation_quaternion"], eval_quat, frame_start, frame_end, is_rotation=True):
                keyframes.append(Keyframe(t, "rotation", val))

        return keyframes

    def _sample_shape_curve(self, fcurve, frame_start, frame_end):
        frames = sorted({int(kp.co[0]) for kp in fcurve.keyframe_points})
        frames = sorted(set(frames) | {frame_start, frame_end - 1})
        prev = None
        results = []
        for frame in frames:
            t = (frame - frame_start) / self.fps
            value = fcurve.evaluate(frame)
            if prev is None or abs(value - prev) > 1e-5:
                results.append((t, float(value)))
                prev = value
        return results

    def _get_fcurves(self, action, slot=None):
        if action is None:
            return []

        if hasattr(action, "layers") and len(action.layers) > 0:
            try:
                if slot is None and hasattr(action, "slots") and len(action.slots) > 0:
                    slot = action.slots[0]
                if slot is not None:
                    channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
                    if channelbag and hasattr(channelbag, "fcurves"):
                        return list(channelbag.fcurves)
            except Exception:
                pass
            try:
                layer = action.layers[0]
                if layer.strips:
                    strip = layer.strips[0]
                    if hasattr(action, "slots") and len(action.slots) > 0:
                        cb = strip.channelbag(action.slots[0])
                        if cb and hasattr(cb, "fcurves"):
                            return list(cb.fcurves)
            except Exception:
                pass

        if hasattr(action, "fcurves"):
            return list(action.fcurves)
        return []

    def _optimise_channel(self, channel_dict, evaluate_func, frame_start, frame_end, is_rotation=False, eps=1e-5):
        if not channel_dict:
            return []
        frames = sorted({int(kp.co[0]) for fc in channel_dict.values() for kp in fc.keyframe_points})

        if not frames:
            return []

        frames = sorted(set(frames) | {frame_start, frame_end - 1})
        result = []
        prev = None

        for frame in frames:
            t = (frame - frame_start) / self.fps
            value = evaluate_func(frame)
            if prev is None:
                result.append((t, value))
                prev = value
                continue

            changed = False

            if is_rotation:
                for a, b in zip(value, prev):
                    if abs(a - b) > eps:
                        changed = True
                        break
            else:
                if (value - prev).length > eps:
                    changed = True
            if changed:
                result.append((t, value))
                prev = value

        return result