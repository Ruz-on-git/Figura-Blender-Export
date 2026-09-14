MeshDriver = require("FiguraMeshDriver")
local mesh = MeshDriver.init("DemoChar", models.DemoChar.Mesh, models.DemoChar.Root) 

vanilla_model.ALL:setVisible(false)

animations.DemoChar.Jump:setSpeed(1.2)

local function onJump()
    if player:isOnGround() then
        animations.DemoChar.Jump:stop()
        animations.DemoChar.Jump:play()
    end
end

keybinds:newKeybind("On Jump", "key.keyboard.space", false):setOnPress(onJump)

function events.tick()
    local vel = player:getVelocity()
    local walking = vel.xz:length() > .01

    if player:isSprinting() then
        animations.DemoChar.Walk:setSpeed(3)
    else
        animations.DemoChar.Walk:setSpeed(2)
    end

    animations.DemoChar.Walk:setPlaying(walking)
end

local mainPage  = action_wheel:newPage("Main")
local blendPage = action_wheel:newPage("Blendshapes")
local emotePage = action_wheel:newPage("Emotes")

local function addBlendAction(name)
    local action = blendPage:newAction()
        :item("minecraft:slime_ball")
        :hoverColor(0.4, 0.8, 1)
        :color(0.2, 0.5, 0.8)

    local function refresh()
        action:title(string.format("%s  (%.2f)", name, mesh.getBlendShape(name)))
    end

    action:onLeftClick(function()
        local v = mesh.getBlendShape(name) + 0.25
        if v > 1.01 then v = 0 end
        mesh.setBlendShape(name, v, 0)
        refresh()
    end)

    action:onRightClick(function()
        mesh.setBlendShape(name, 0, 0)
        refresh()
    end)

    action:onScroll(function(dir)
        mesh.setBlendShape(name, math.clamp(mesh.getBlendShape(name) + dir * 0.05, -2, 2), 0)
        refresh()
    end)

    refresh()
end

for _, name in ipairs(mesh.getBlendShapeNames()) do
    addBlendAction(name)
end

local emote_list = {
    Happy = {
        HappyL = 1,
        HappyR = 1,
    },

    Sad = {
        SadL = 1,
        SadR = 1,
    },

    Angry = {
        AngryR = 1,
        AngryL = 1,
    },
}

local activeEmote = nil

local function clearEmote()
    if activeEmote == nil then
        return
    end

    for blendshape, _ in pairs(activeEmote) do
        mesh.setBlendShape(blendshape, 0, 0)
    end

    activeEmote = nil
end

local function playEmote(name)
    clearEmote()

    local emote = emote_list[name]
    if emote == nil then
        return
    end

    for blendshape, value in pairs(emote) do
        mesh.setBlendShape(blendshape, value, 0)
    end

    activeEmote = emote
end

for name, _ in pairs(emote_list) do
    local action = emotePage:newAction()
        :title(name)
        :item("minecraft:player_head")

    action:onLeftClick(function()
        playEmote(name)
    end)

    action:onRightClick(function()
        clearEmote()
    end)
end


blendPage:newAction()
    :title("← Back")
    :item("minecraft:arrow")
    :onLeftClick(function()
        action_wheel:setPage(mainPage)
    end)

mainPage:newAction()
    :title("Blendshapes")
    :item("minecraft:magma_cream")
    :hoverColor(1, 0.6, 0.2)
    :onLeftClick(function()
        action_wheel:setPage(blendPage)
    end)

mainPage:newAction()
    :title("Emotes")
    :item("minecraft:player_head")
    :hoverColor(1, 0.4, 0.6)
    :color(0.8, 0.2, 0.4)
    :onLeftClick(function()
        action_wheel:setPage(emotePage)
    end)

emotePage:newAction()
    :title("Back")
    :item("minecraft:arrow")
    :onLeftClick(function()
        action_wheel:setPage(mainPage)
    end)

emotePage:newAction()
    :title("Reset")
    :item("minecraft:barrier")
    :onLeftClick(function()
        clearEmote()
    end)

action_wheel:setPage(mainPage)
