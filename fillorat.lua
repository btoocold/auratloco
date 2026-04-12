
-- Here is the updated code after fixing scroll, round corners, invisible scrollbars, and mobile support.

-- Function to make the UI scrollable and dynamic
local function createScrollableTab(tab)
    local container = tab:FindFirstChild("Container") -- Get the container of the tab

    if container then
        -- Create a new ScrollingFrame
        local scrollFrame = Instance.new("ScrollingFrame")
        scrollFrame.Name = "ScrollableContent"
        scrollFrame.Size = UDim2.new(1, 0, 1, 0)  -- Make the frame fill the container
        scrollFrame.Position = UDim2.new(0, 0, 0, 0)
        scrollFrame.CanvasSize = UDim2.new(0, 0, 1, 0)  -- Initially set canvas size to fit the content
        scrollFrame.ScrollingDirection = Enum.ScrollingDirection.Y
        scrollFrame.ScrollBarThickness = 4
        scrollFrame.ClipsDescendants = true
        scrollFrame.Parent = container

        -- Move all current children of the container into the new scrolling frame
        for _, child in ipairs(container:GetChildren()) do
            if child ~= scrollFrame then
                child.Parent = scrollFrame
            end
        end

        -- Update canvas size dynamically based on content size
        scrollFrame:GetPropertyChangedSignal("AbsoluteSize"):Connect(function()
            scrollFrame.CanvasSize = UDim2.new(0, 0, 0, scrollFrame.UIListLayout.AbsoluteContentSize.Y)
        end)
    end
end

-- Apply the scrollable feature to the relevant tabs
task.spawn(function()
    -- Apply scrolling to all relevant tabs (Visuals, Settings, Player Mods)
    local tabsToScroll = {Tabs.Visuals, Tabs.Settings, Tabs.PlayerMods}
    for _, tab in ipairs(tabsToScroll) do
        createScrollableTab(tab)
    end
end)

-- Customizable style (rounded corners and invisible scrollbar)
local function applyUIStyling()
    local uiFrame = script.Parent -- Assuming this is the main frame of the UI

    -- Add rounded corners
    local UICorner = Instance.new("UICorner")
    UICorner.CornerRadius = UDim.new(0, 12)  -- Adjust corner radius for rounded corners
    UICorner.Parent = uiFrame

    -- Invisible scrollbar setup
    local scrollFrame = uiFrame:FindFirstChild("ScrollableContent")
    if scrollFrame then
        scrollFrame.ScrollBarImageTransparency = 1 -- Make the scrollbar invisible
    end
end

applyUIStyling()

-- Mobile support to make UI draggable
function Library:MakeDraggable(Instance, Cutoff)
    Instance.Active = true
    local UserInputService = game:GetService("UserInputService")
    local Mouse = game:GetService("Players").LocalPlayer:GetMouse()

    Instance.InputBegan:Connect(function(Input)
        if Input.UserInputType == Enum.UserInputType.MouseButton1 then
            local ObjPos = Vector2.new(Mouse.X - Instance.AbsolutePosition.X, Mouse.Y - Instance.AbsolutePosition.Y)

            if ObjPos.Y > (Cutoff or 40) then return end

            while UserInputService:IsMouseButtonPressed(Enum.UserInputType.MouseButton1) do
                Instance.Position = UDim2.new(
                    0, Mouse.X - ObjPos.X + (Instance.Size.X.Offset * Instance.AnchorPoint.X),
                    0, Mouse.Y - ObjPos.Y + (Instance.Size.Y.Offset * Instance.AnchorPoint.Y)
                )
                game:GetService("RunService").RenderStepped:Wait()
            end
        end
    end)
end
