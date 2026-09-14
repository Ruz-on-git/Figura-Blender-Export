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

    def parse(self, armature_obj, mesh_obj=None):
        animations = []
        by_name = {}
        bone_ranges = []

        def process_sources(sources, shape_only=False):
            for name_hint, action, slot, strip_frame_range in sources:
                fcurves = self._get_fcurves(action, slot)
                if not fcurves:
                    continue
                shape_fcurves = [fc for fc in fcurves if 'key_blocks["' in fc.data_path and fc.data_path.endswith(".value")]
                if shape_only:
                    if not shape_fcurves:
                        continue
                    anim = self._process_action(None, name_override=clean_name(name_hint or action.name), extra_fcurves=shape_fcurves)
                else:
                    anim = self._process_action(action, name_override=clean_name(name_hint or action.name), slot=slot)

                if not anim:
                    continue

                target = self._find_matching_animation(by_name, bone_ranges, animations, name_hint, strip_frame_range)
                if shape_only:
                    if anim.shape_keyframes and target:
                        target.shape_keyframes.extend(anim.shape_keyframes)
                    continue

                if target is None:
                    if anim and anim.name not in by_name:
                        animations.append(anim)
                        by_name[anim.name] = anim
                    target = by_name.get(anim.name) if anim else None

                if target and anim.shape_keyframes:
                    target.shape_keyframes.extend(anim.shape_keyframes)

        if anim_data := armature_obj.animation_data:
            sources = self._get_animation_sources(anim_data)
            process_sources(sources)

        if mesh_obj:
            process_sources(self._get_animation_sources(mesh_obj.animation_data))
        if mesh_obj.data.shape_keys:
            process_sources(self._get_animation_sources(mesh_obj.data.shape_keys.animation_data), shape_only=True)
        return animations


    def _get_animation_sources(self, source):
        result = []
        if not source:
            return result
        if source.action:
            result.append((source.action.name, source.action, getattr(source, "action_slot", None), None))
        for track in source.nla_tracks:
            for strip in track.strips:
                if strip.action:
                    result.append((strip.name, strip.action, None, (strip.frame_start, strip.frame_end)))
        return result

    def _find_matching_animation(self, by_name, bone_ranges, animations, name_hint, strip_frame_range):
        if strip_frame_range is not None and bone_ranges:
            best_anim, best_overlap = None, 0.0
            for anim, fs, fe in bone_ranges:
                overlap = min(strip_frame_range[1], fe) - max(strip_frame_range[0], fs)
                if overlap > best_overlap:
                    best_overlap, best_anim = overlap, anim
            if best_anim is not None:
                return best_anim

        if name_hint:
            cleaned = clean_name(name_hint)
            if cleaned in by_name:
                return by_name[cleaned]
            import re
            base_hint = re.sub(r'[._]\d+$', '', cleaned)
            for name, anim in by_name.items():
                if re.sub(r'[._]\d+$', '', name) == base_hint:
                    return anim

        if name_hint is None and len(animations) == 1:
            return animations[0]

        return None


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
            fcurves = []
            slots = [slot] if slot is not None else list(getattr(action, "slots", []))

            for s in slots:
                try:
                    channelbag = anim_utils.action_get_channelbag_for_slot(action, s)
                    if channelbag and hasattr(channelbag, "fcurves"):
                        fcurves.extend(channelbag.fcurves)
                        continue
                except Exception:
                    pass

                try:
                    layer = action.layers[0]
                    if layer.strips:
                        cb = layer.strips[0].channelbag(s)
                        if cb and hasattr(cb, "fcurves"):
                            fcurves.extend(cb.fcurves)
                except Exception:
                    pass

            if fcurves:
                return fcurves

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