import json

def to_json(obj) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)

def to_lua(obj, indent=0) -> str:
    spaces = "  " * indent

    if isinstance(obj, dict):
        items = []
        for key, value in obj.items():
            lua_key = key if str(key).isidentifier() else f"[{to_lua(key)}]"
            items.append(f"{spaces}  {lua_key} = {to_lua(value, indent + 1)}")
        return "{\n" + ",\n".join(items) + f"\n{spaces}}}"

    if isinstance(obj, (list, tuple)):
        return "{" + ", ".join(to_lua(v, indent + 1) for v in obj) + "}"

    if isinstance(obj, bool):
        return "true" if obj else "false"

    if isinstance(obj, (int, float)):
        return str(obj)

    if obj is None:
        return "nil"

    return f'"{obj}"'