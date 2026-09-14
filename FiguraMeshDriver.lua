local DRIVER = {}

function DRIVER.init(modelName, meshPart, first_bone)
--#region Load Model
    if _G.Mesh and _G.Mesh[modelName] then
        return _G.Mesh[modelName]
    end

    if not meshPart then
        error('meshPart is required for "' .. modelName .. '"')
    end
    if not first_bone then
        error('boneRoot is required for "' .. modelName .. '"')
    end

    local ok, meshData = pcall(require, modelName .. "-MeshData")
    if not ok or not meshData then
        error('Could not load MeshData for "' .. modelName .. '"')
    end
--#endregion

--#region Build Vertices
    meshPart:setVisible(true)
    local figuraVertices = meshPart:getAllVertices() or {}
    
    local vertices = {}

    for index, data in ipairs(meshData.vertexData) do
        local vert = {
            restPos = nil,
            weights = data.weights,
            deltas = data.deltas or {},
            figuraVerts = {}
        }

        for texIndex, loopList in pairs(data.loops or {}) do
            local texName = meshData.textureMap[texIndex]
            local texVerts = figuraVertices[modelName .. "." .. texName] or figuraVertices[tostring(texName)]

            if texVerts then
                for _, idx in ipairs(loopList) do
                    local v = texVerts[idx]
                    if v then
                        table.insert(vert.figuraVerts, v)
                        if not vert.restPos then
                            vert.restPos = v:getPos():copy()
                        end
                    end
                end
            end
        end

        if not vert.restPos and #vert.figuraVerts > 0 then
            vert.restPos = vert.figuraVerts[1]:getPos():copy()
        end

        vertices[index] = vert
    end
--#endregion

--#region Build Bone Hierarchy
    local boneTree = {}
    local groupMap = meshData.groupMap or {}

    local function buildBoneTree(part, parentIndex)
        local idx = groupMap[part:getName()]
        if idx then
            table.insert(boneTree, {
                index  = idx,
                parent = parentIndex,
                part   = part:setParentType("None")
            })
            parentIndex = idx
        end

        for _, child in ipairs(part:getChildren()) do
            if child:getType() == "GROUP" then
                buildBoneTree(child, parentIndex)
            end
        end
    end

    buildBoneTree(first_bone, nil)
--#endregion

--#region Blend Shape State
    local weights = {}
    local blends  = {}

    for _, name in ipairs(meshData.shapeKeys or {}) do
        weights[name] = 0
    end
--#endregion

    local mesh = {}

--#region Public API
    
    --- Returns the names of all blend shapes on the mesh.
    ---@return string[] names List of blend shape names.
    function mesh.getBlendShapeNames()
        return meshData.shapeKeys or {}
    end

    --- Returns the current weight of a blend shape.
    ---@param name string The name of the blend shape.
    ---@return number value The current weight, from 0 to 1.
    function mesh.getBlendShape(name)
        return weights[name] or 0
    end

    --- Sets a blend shape to a value, optionally interpolating to it over time.
    ---@param name string The name of the blend shape.
    ---@param value number The target weight, clamped between 0 and 1.
    ---@param duration? number Time in seconds to interpolate to the target value.
    function mesh.setBlendShape(name, value, duration)
        value = math.clamp(tonumber(value) or 0, 0, 1)
        duration = tonumber(duration) or 0

        if duration > 0 then
            blends[name] = {
                from = weights[name] or 0,
                to = value,
                start = client.getSystemTime() / 1000 - (1 / 60),
                duration = duration
            }
        else
            blends[name] = nil
            weights[name] = value
        end
    end

    --- Sets a blend shape immediately and optionally starts a second transition.
    ---@param name string The name of the blend shape.
    ---@param value number The initial weight, clamped between 0 and 1.
    ---@param nextValue? number The weight to transition to after setting the initial value.
    ---@param duration? number Time in seconds to transition from value to nextValue.
    function mesh.setBlendShapeKey(name, value, nextValue, duration)
        value = math.clamp(tonumber(value) or 0, 0, 1)
        blends[name] = nil
        weights[name] = value

        if nextValue ~= nil and (tonumber(duration) or 0) > 0 then
            nextValue = math.clamp(tonumber(nextValue) or 0, 0, 1)
            blends[name] = {
                from = value,
                to = nextValue,
                start = client.getSystemTime() / 1000 - (1 / 60),
                duration = tonumber(duration)
            }
        end
    end

    --- Sets multiple blend shapes to their target values.
    ---@param tbl table<string, number> A table where each key is a blend shape name and each value is its target weight.
    ---@param duration? number Time in seconds to transition to the target values.
    function mesh.setBlendShapes(tbl, duration)
        for name, value in pairs(tbl) do
            mesh.setBlendShape(name, value, duration)
        end
    end

    --- Resets all blend shapes to 0.
    ---@param duration? number Time in seconds to transition the blend shapes back to 0.
    function mesh.resetBlendShapes(duration)
        for name in pairs(weights) do
            mesh.setBlendShape(name, 0, duration)
        end
    end
--#endregion

--#region Animation Helpers
    local currentAnim = nil
    local watcherName = "meshdriver_" .. modelName .. "_watch"

    function mesh.play(animName, onFinish)
        local anim = animations[modelName] and animations[modelName][animName]
        if not anim then return end

        if currentAnim then currentAnim:stop() end

        local backup = {}
        for name, value in pairs(weights) do
            backup[name] = value
        end

        currentAnim = anim
        anim:stop():play()

        events.TICK:register(function()
            if not currentAnim or currentAnim:isPlaying() then return end

            currentAnim = nil
            events.TICK:remove(watcherName)
            mesh.setBlendShapes(backup, 0)
            if onFinish then onFinish() end
        end, watcherName)
    end

    function mesh.stop(animName)
        local anim = animations[modelName] and animations[modelName][animName]
        if anim then anim:stop() end

        if currentAnim == anim then
            currentAnim = nil
            events.TICK:remove(watcherName)
        end
    end

    function mesh.stopAll()
        for _, anim in pairs(animations[modelName] or {}) do
            anim:stop()
        end
        currentAnim = nil
        events.TICK:remove(watcherName)
    end
--#endregion

--#region Render Loop
    local identity = matrices.mat4()

    events.render:register(function()
        local now = client.getSystemTime() / 1000

        -- Update blend shape interpolations
        for name, b in pairs(blends) do
            local t = math.clamp((now - b.start) / b.duration, 0, 1)
            weights[name] = math.lerp(b.from, b.to, t)

            if t >= 1 then
                weights[name] = b.to
                blends[name] = nil
            end
        end

        -- Bone matrices
        local boneMats = {}
        for _, bone in ipairs(boneTree) do
            local parentMat = bone.parent and boneMats[bone.parent] or identity
            boneMats[bone.index] = parentMat * bone.part:getPositionMatrix()
        end

        for _, vert in ipairs(vertices) do
            if not vert.restPos then goto continue end

            local pos = vert.restPos:copy()

            -- Blend shapes
            for name, d in pairs(vert.deltas) do
                local w = weights[name]
                if w and w ~= 0 then
                    pos = pos + vectors.vec3(d[1], d[2], d[3]) * w
                end
            end

            -- Skinning
            if vert.weights then
                local skinned = vectors.vec3()
                local total = 0

                for boneIdx, weight in pairs(vert.weights) do
                    local mat = boneMats[boneIdx]
                    if mat then
                        skinned = skinned + mat:apply(pos) * weight
                        total = total + weight
                    end
                end

                if total > 0.0001 then
                    pos = skinned
                end
            end

            for _, fv in ipairs(vert.figuraVerts) do
                fv:setPos(pos)
            end

            ::continue::
        end
    end, "meshdriver_" .. modelName .. "_render")
--#endregion

--#region Registration
    _G.Mesh = _G.Mesh or {}
    _G.Mesh[modelName] = mesh

    return mesh
--#endregion
end

return DRIVER