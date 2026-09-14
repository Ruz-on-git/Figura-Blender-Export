# Figura Blender Export
A Blender plugin for exporting characters from Blender for use with Figura, inspired by https://github.com/KitCat962/figura-mesh-deformation.
This plugin has been made and developed for Blender 5.2. Compatibility past or prior to this version is not guaranteed.


**AI Assistance Disclosure:** AI tools have been used to assist with debugging, troubleshooting, and documentation during the development of this project.

---

## What is Figura Blender Export?

Figura Blender Export is a Blender add-on that allows you to create avatars for Figura in blender, with an aim to make the creation of more complex Figura avatars easier.

The following has currently been implemented:
- Export Blender characters for use with Figura
- Export textures (Shader node textures still currently need to be baked into a texture)
- Support for Blender Bones
- Export blendshapes
- Export Animations with blendshapes

With plans in the future to support:
- Nothing currently happy for suggestions

---

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/T7D226ZUTG)
---

# Installation

1. Go into releases and download the latest ZIP file with the current release.
2. Open Blender.
3. Go to Edit -> Preferences.
4. Select Add-ons.
5. In the top right, there is a dropdown arrow. Click it and click install from disk.
6. Select the downloaded Figura Blender Export `.zip`.
7. Click Install Add-on.
8. Enable the plugin if it isn't automaticly enabled.

Once installed you should be able to go File -> Export and there should be an option for Figura Avatar.

---

# Exporting a Character
When exporting a character, you will first need to make sure the mesh is parented to the armature.

This can be done by doing the following:
1. In Object mode, click on your mesh.
2. Shift click on your armature.
3. Press CTRL + P
4. Press with automatic Weights
5. Optionally go though your mesh and fix up the weight painting to each bone

Also if you are using a texture made by shader nodes, you will need to bake that texture to a file, as otherwise the model will export with solid colours.

This can be done by doing the following:
1. Go to the UV Tab.
2. Press A and then in the uv tab use 'Smart Uv Project...'.
3. Go to the shading tab.
4. Click on your mesh in object mode.
5. Do Shift + A and search for 'Image Texture' and add it to the shader graph.
6. Press new and create a texture with whatever name and resolution you want.
7. Go to the Rendering tab.
8. In the middle of the top bar, press the photo icon and click the texture you just made.
9. In the inspector, go to the rendering tab, and choose Cycles for your renderer.
10. Go down in the rendering tab until you find 'Bake' and untick Direct and Indirect lighting.
11. Press the bake button.
12. Go back to the shading tab.
13. Drag the colour from your texture node into you base colour of the Principled BSDF.

After these have been setup we can get the avatar setup ingame.

This can be done by doing the following:
1. In Object mode click on your avatar mesh.
2. Go File -> Export -> Figura Avatar and save it to your figura character folder.
3. Open up a script file in your Figura Avatar and add the following:

```lua
MeshDriver = require("FiguraMeshDriver")
local mesh = MeshDriver.init("Blockbench File Name", models.[Blockbench File Name].Mesh, models.[Blockbench File Name].[Root bone name])
```

I would not suggest changing the names unless your willing to look into the code, where you will need to change some names in the MeshData.lua file. 

---

# API Summary

This is a summary of the public API functions that will be available to you when you import your mesh into figura. Animations can be called like usual.

| Function | Description |
| --- | --- |
| `mesh.getBlendShapeNames()` | Returns all available blend shape names. |
| `mesh.getBlendShape(name)` | Gets the current weight of a blend shape. |
| `mesh.setBlendShape(name, value, duration)` | Sets a blend shape immediately or smoothly. |
| `mesh.setBlendShapeKey(name, value, nextValue, duration)` | Sets an initial value and optionally transitions to another value. |
| `mesh.setBlendShapes(tbl, duration)` | Sets multiple blend shapes at once. |
| `mesh.resetBlendShapes(duration)` | Resets all blend shapes to `0`. |


<details>
 <summary>Get BlendShape Names</summary>

 ### `mesh.getBlendShapeNames()`

 Returns a list containing the names of every blend shape available on the mesh.

 ### Syntax

 ```lua
    local names = mesh.getBlendShapeNames()
 ```

 ### Returns

 | Type | Description |
 | --- | --- |
 | `string[]` | A table containing the names of all available blend shapes. |

 ### Example

 ```lua
    local shapes = mesh.getBlendShapeNames()

    for _, name in ipairs(shapes) do
        print("Blend shape: " .. name)
    end
 ```
</details> 

<details> 
 <summary>Get Blend Shape</summary> 

 ### `mesh.getBlendShape(name)`

 Returns the current weight of a blend shape.

 Blend shape weights normally range from `0` to `1`:

 - `0` = Blend shape is not applied
 - `1` = Blend shape is fully applied
 - `0.5` = Blend shape is applied at 50%

 ### Syntax

 ```lua
    local value = mesh.getBlendShape("Blink")
 ```

 ### Parameters

 | Parameter | Type | Description |
 | --- | --- | --- |
 | `name` | `string` | The name of the blend shape. |

 ### Returns

 | Type | Description |
 | --- | --- |
 | `number` | The current blend shape weight. |

 ### Example

 ```lua
    local blink = mesh.getBlendShape("Blink")

    print("Blink weight: " .. blink)
 ```

 If the requested blend shape does not have a stored weight, `0` is returned.
</details> 

<details> 
 <summary>Set Blend Shape</summary> 

 ### `mesh.setBlendShape(name, value, duration)`

 Sets a blend shape to a target weight.

 The change can either happen immediately or be interpolated over a period of time.

 ### Syntax

 ```lua
    mesh.setBlendShape(name, value, duration)
 ```

 ### Parameters

 | Parameter | Type | Optional | Description |
 | --- | --- | --- | --- |
 | `name` | `string` | No | The name of the blend shape. |
 | `value` | `number` | No | The target weight. |
 | `duration` | `number` | Yes | Time in seconds to transition to the target value. |

 If `duration` is omitted or `0`, the blend shape changes immediately.

</details>
 
<details> 
 <summary>Set Blend Shape Key</summary> 

 ### `mesh.setBlendShapeKey(name, value, nextValue, duration)`

 Sets a blend shape to an initial value immediately, then optionally transitions it to a second value.

 ### Syntax

 ```lua
    mesh.setBlendShapeKey(name, value, nextValue, duration)
 ```

 ### Parameters

 | Parameter | Type | Optional | Description |
 | --- | --- | --- | --- |
 | `name` | `string` | No | The name of the blend shape. |
 | `value` | `number` | No | The initial weight. |
 | `nextValue` | `number` | Yes | The weight to transition to after setting the initial value. |
 | `duration` | `number` | Yes | Time in seconds for the transition to `nextValue`. |

 ### Example

 ```lua
    mesh.setBlendShapeKey("Blink", 1, 0, 0.15)
 ```

 This:

 1. Immediately sets `Blink` to `1`.
 2. Starts a transition from `1` to `0`.
 3. Takes `0.15` seconds to complete the transition.
</details> 

<details> 
 <summary>Set Blend Shapes (multiple at once)</summary> 

 ### `mesh.setBlendShapes(tbl, duration)`

 Sets multiple blend shapes at once.

 The first parameter is a Lua table where each key is a blend shape name and each value is its target weight.

 ### Syntax

 ```lua
    mesh.setBlendShapes({
        ["ShapeName"] = value,
        ["AnotherShape"] = value
    }, duration)
 ```

 ### Parameters

 | Parameter | Type | Optional | Description |
 | --- | --- | --- | --- |
 | `tbl` | `table<string, number>` | No | A table containing blend shape names and target weights. |
 | `duration` | `number` | Yes | Time in seconds to transition to the target values. |

 ### Example

 ```lua
    mesh.setBlendShapes({
        ["Smile"] = 1,
        ["Blink"] = 0.5,
        ["MouthOpen"] = 0.25
    })
 ```

 All three blend shapes are changed immediately.

 You can also smoothly transition them:

 ```lua
    mesh.setBlendShapes({
        ["Smile"] = 1,
        ["Blink"] = 0.5,
        ["MouthOpen"] = 0.25
    }, 0.5)
 ```

 All of the specified blend shapes will transition to their target values over `0.5` seconds.
</details>

<details> 
 <summary>Reset Blend Shapes</summary> 

 ### `mesh.resetBlendShapes(duration)`

 Resets all currently tracked blend shapes to `0`.

 ### Parameters

 | Parameter | Type | Optional | Description |
 | --- | --- | --- | --- |
 | `duration` | `number` | Yes | Time in seconds to transition all blend shapes back to `0`. |

 ### Immediate Reset

 ```
    mesh.resetBlendShapes()
 ```

 All blend shapes are immediately set to `0`.

 ### Smooth Reset

 ```
    mesh.resetBlendShapes(0.25)
 ```

 All blend shapes smoothly transition back to `0` over `0.25` seconds.
</details>
