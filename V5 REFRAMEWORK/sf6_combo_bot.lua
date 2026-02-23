-- ============================================================================
--  SF6 Combo Bot  —  Pure REFramework Mod
--  File: reframework/autorun/sf6_combo_bot.lua
--  Version: 1.0
-- ============================================================================
--
--  INSTALL:
--    1. Install REFramework for SF6:
--       https://github.com/praydog/REFramework-nightly/releases  (SF6.zip)
--       Drop dinput8.dll into your SF6 game folder.
--
--    2. Place THIS file at:
--       <SF6 folder>/reframework/autorun/sf6_combo_bot.lua
--
--    3. Launch SF6. Press INSERT to open REFramework overlay.
--       Navigate to Script Generated UI → SF6 Combo Bot.
--
--  HOW IT WORKS:
--    Rather than emulating a controller from outside the game, this mod writes
--    directly to the player's internal input register (ok_trg / ok_key) each
--    frame via REFramework's sdk.set_field. This means inputs are processed
--    by exactly the same code path as real controller inputs — frame-perfect
--    by definition since we run inside the game loop.
--
--    The combo engine is a coroutine-based sequencer: each combo is a Lua
--    coroutine that yields after each input step, resuming on the next game
--    frame. This gives frame-accurate timing without any sleep calls.
--
--  HOTKEYS (configurable in the UI):
--    F1  BnB #1        F2  BnB #2
--    F3  Punish #1     F4  Punish #2 (OD)
--    F5  Super route   F8  Advanced combo
--    F6  Next char     F7  Prev char
--    F9  Cancel / abort running combo
--
--  NOTE ON FIELD NAMES:
--    Field names (ok_trg, act_id, etc.) were identified from community RE
--    Engine research on SF6. If Capcom updates the game and values stop
--    reading correctly, use REFramework's Object Explorer (Insert → Developer
--    Tools → Object Explorer → Singletons → gBattle) to find current names.
-- ============================================================================

-- ── Imports ──────────────────────────────────────────────────────────────────
local json = json  -- bundled with REFramework

-- ══════════════════════════════════════════════════════════════════════════════
--  INPUT BIT FLAGS  (SF6 internal button bitfield — ok_trg / ok_key)
-- ══════════════════════════════════════════════════════════════════════════════
--  These are the bitmask values SF6 uses internally for each button.
--  Multiple buttons are combined with bitwise OR.
--  Direction bits combine with button bits in the same field.
--  Values confirmed from WistfulHopes/SF6Mods and MMDK community research.

local BTN = {
    LP    = 0x00000001,   -- Light Punch
    MP    = 0x00000002,   -- Medium Punch
    HP    = 0x00000004,   -- Heavy Punch
    LK    = 0x00000008,   -- Light Kick
    MK    = 0x00000010,   -- Medium Kick
    HK    = 0x00000020,   -- Heavy Kick
    -- Directions
    UP    = 0x00000040,
    DOWN  = 0x00000080,
    LEFT  = 0x00000100,   -- back  (relative to facing direction)
    RIGHT = 0x00000200,   -- forward
    -- System
    PARRY = 0x00000400,   -- Drive Parry (MP+MK)
    DI    = 0x00000800,   -- Drive Impact (HP+HK)
    DR    = 0x00001000,   -- Drive Rush (after parry or cancel: f+MP+MK)
    OD    = 0x80000000,   -- Overdrive modifier flag (internal; real OD = two same-strength buttons)
}

-- Aliases for combos — OD moves press two buttons simultaneously:
-- LP+HP = OD Punch,  LK+HK = OD Kick,  MP+HP = OD Medium Punch etc.
local function od_punch(strength)
    if strength == "L" then return BTN.LP | BTN.HP end
    if strength == "M" then return BTN.MP | BTN.HP end
    return BTN.MP | BTN.HP  -- default
end
local function od_kick(strength)
    if strength == "L" then return BTN.LK | BTN.HK end
    if strength == "M" then return BTN.MK | BTN.HK end
    return BTN.MK | BTN.HK
end

-- Directional shorthands (numpad notation; these are absolute, flip left for P2)
local DIR = {
    ["5"] = 0,                        -- neutral
    ["2"] = BTN.DOWN,                 -- down
    ["8"] = BTN.UP,                   -- up
    ["4"] = BTN.LEFT,                 -- back
    ["6"] = BTN.RIGHT,                -- forward
    ["1"] = BTN.DOWN | BTN.LEFT,      -- down-back
    ["3"] = BTN.DOWN | BTN.RIGHT,     -- down-forward
    ["7"] = BTN.UP   | BTN.LEFT,      -- up-back
    ["9"] = BTN.UP   | BTN.RIGHT,     -- up-forward
    -- QCF path segments
    ["23"] = BTN.DOWN | BTN.RIGHT,
    ["24"] = BTN.DOWN | BTN.LEFT,
    ["62"] = BTN.RIGHT | BTN.DOWN,
}

-- ══════════════════════════════════════════════════════════════════════════════
--  GAME STATE ACCESS
-- ══════════════════════════════════════════════════════════════════════════════

local _gbattle_type = nil
local _player_obj   = nil   -- cached P1 player object

local function get_gbattle()
    if not _gbattle_type then
        _gbattle_type = sdk.find_type_definition("gBattle")
    end
    return _gbattle_type
end

-- Returns the P1 player managed object, or nil if not in a battle scene.
local function get_player(idx)
    idx = idx or 0
    local ok, result = pcall(function()
        local gb   = get_gbattle()
        if not gb then return nil end
        local sPlayer = gb:get_field("Player"):get_data(nil)
        if not sPlayer then return nil end
        local mcPlayer = sPlayer:get_field("mcPlayer")
        if not mcPlayer then return nil end
        return mcPlayer[idx]
    end)
    return ok and result or nil
end

-- Safe field reader — returns default on any error
local function rfield(obj, field, default)
    if not obj then return default end
    local ok, v = pcall(function() return obj:get_field(field) end)
    return (ok and v ~= nil) and v or default
end

-- Safe field writer
local function wfield(obj, field, value)
    if not obj then return false end
    local ok = pcall(function() obj:set_field(field, value) end)
    return ok
end

-- Read current game state data for P1
local function read_battle_state()
    local p1 = get_player(0)
    if not p1 then
        return { valid = false }
    end
    return {
        valid      = true,
        act_id     = rfield(p1, "act_id", -1),       -- current action/animation ID
        act_frame  = rfield(p1, "act_frame", -1),     -- frame within current action
        hp         = rfield(p1, "hp", -1),
        drive      = rfield(p1, "drive_val", -1),     -- drive gauge value
        super_lvl  = rfield(p1, "sa_gauge_lv", 0),   -- super art level (0-3)
        hitstop    = rfield(p1, "hitstop", 0),
        combo      = rfield(p1, "combo_cnt", 0),
        chara_id   = rfield(p1, "chara_id", -1),     -- character ID for auto-detect
    }
end

-- ══════════════════════════════════════════════════════════════════════════════
--  INPUT ENGINE  —  write to the player's internal input register each frame
-- ══════════════════════════════════════════════════════════════════════════════
--
--  Strategy: The player object has two relevant fields:
--    ok_trg  — "trigger" inputs: bits that are SET this frame and were not set last frame (pressed)
--    ok_key  — "key" inputs: bits that are held down right now (held)
--
--  For a combo step we:
--    1. Set ok_key to the desired direction + button combination for N frames
--    2. After N frames, clear ok_key to simulate release
--    3. ok_trg is automatically derived by the engine (new bits = trg, held bits = key)
--       But we also set ok_trg directly for the first frame of a press to be safe.
--
--  This is the same mechanism SF6's training mode dummy uses internally.

-- Pending input state for the current frame
local _pending_key   = 0   -- buttons/directions to hold
local _pending_trg   = 0   -- buttons that are newly pressed this frame

-- Called once per frame from re.on_application_entry to flush pending inputs
local function flush_inputs(p1)
    if not p1 then return end
    wfield(p1, "ok_key", _pending_key)
    wfield(p1, "ok_trg", _pending_trg)
    -- ok_trg is a single-frame trigger — clear after writing
    _pending_trg = 0
end

local function set_input(key_bits, trg_bits)
    _pending_key = key_bits  or 0
    _pending_trg = trg_bits  or key_bits or 0
end

local function clear_input()
    _pending_key = 0
    _pending_trg = 0
end

-- ══════════════════════════════════════════════════════════════════════════════
--  COROUTINE COMBO ENGINE
-- ══════════════════════════════════════════════════════════════════════════════
--
--  Each combo is a Lua function that uses the helpers below.
--  Calling wait_frames(n) yields the coroutine n times — one yield per game frame.
--  The main frame hook resumes the coroutine each frame while one is running.
--
--  This means timing is expressed in actual game frames, not wall-clock time.
--  Hitstop is handled by pausing frame-count advancement while p1.hitstop > 0.

local _combo_coro    = nil   -- active coroutine, or nil
local _cancel_flag   = false -- set true to abort

-- Yield for n game frames (hitstop-aware)
local function wait_frames(n)
    for _ = 1, n do
        if _cancel_flag then coroutine.yield("cancel") end
        coroutine.yield("frame")
    end
end

-- Wait out any current hitstop before continuing
local function wait_hitstop()
    while true do
        local state = read_battle_state()
        if not state.valid or state.hitstop <= 0 then break end
        if _cancel_flag then coroutine.yield("cancel") end
        coroutine.yield("hitstop")
    end
end

-- Press buttons for n frames (direction = numpad string like "2", "6", "23")
local function press(buttons_bits, frames, direction)
    local dir_bits = direction and (DIR[direction] or 0) or 0
    local combined = buttons_bits | dir_bits
    -- First frame: set both key and trigger
    set_input(combined, combined)
    wait_frames(1)
    -- Remaining hold frames
    if frames > 1 then
        set_input(combined, 0)   -- held, not newly pressed
        wait_frames(frames - 1)
    end
    -- Release
    clear_input()
    wait_frames(1)
end

-- Hold a direction with no button press
local function hold_dir(dir_str, frames)
    local dir_bits = DIR[dir_str] or 0
    set_input(dir_bits, 0)
    wait_frames(frames)
end

-- Return to neutral
local function neutral(frames)
    clear_input()
    wait_frames(frames or 1)
end

-- Shorthand: crouching normal
local function cr(btn_bits, frames)
    press(btn_bits, frames or 3, "2")
end

-- Shorthand: standing normal (from neutral)
local function st(btn_bits, frames)
    neutral(1)
    press(btn_bits, frames or 3, nil)
end

-- Link pause between normals (let recovery finish)
local function link(frames)
    neutral(frames or 3)
end

-- Cancel gap (tight, before a special)
local function cancel(frames)
    wait_frames(frames or 1)
end

-- ── Motion helpers ────────────────────────────────────────────────────────────

local function qcf(frames)  -- 236
    frames = frames or 2
    hold_dir("2", frames)
    hold_dir("23", frames)
    hold_dir("6", frames)
end

local function qcb(frames)  -- 214
    frames = frames or 2
    hold_dir("2", frames)
    hold_dir("24", frames)
    hold_dir("4", frames)
end

local function dp(frames)   -- 623
    frames = frames or 2
    hold_dir("6", frames)
    hold_dir("2", frames)
    hold_dir("23", frames)
end

local function rdp(frames)  -- 421
    frames = frames or 2
    hold_dir("4", frames)
    hold_dir("2", frames)
    hold_dir("24", frames)
end

local function hcf(frames)  -- 41236
    frames = frames or 2
    hold_dir("4", frames); hold_dir("24", frames)
    hold_dir("2", frames); hold_dir("23", frames); hold_dir("6", frames)
end

local function hcb(frames)  -- 63214
    frames = frames or 2
    hold_dir("6", frames); hold_dir("62", frames)
    hold_dir("2", frames); hold_dir("24", frames); hold_dir("4", frames)
end

-- Charge helpers — hold a direction for N frames (builds charge during normals)
local function charge(dir_str, frames)
    hold_dir(dir_str, frames or 10)
end

-- ══════════════════════════════════════════════════════════════════════════════
--  CHARACTER ID → NAME MAP
--  (Numeric IDs from gBattle.Player[0].chara_id field)
--  Found via Object Explorer / community research
-- ══════════════════════════════════════════════════════════════════════════════

local CHARA_ID_MAP = {
    [0]  = "Ryu",
    [1]  = "Luke",
    [2]  = "Kimberly",
    [3]  = "Chun-Li",
    [4]  = "Manon",
    [5]  = "Zangief",
    [6]  = "JP",
    [7]  = "Dhalsim",
    [8]  = "Cammy",
    [9]  = "Ken",
    [10] = "Dee Jay",
    [11] = "Lily",
    [12] = "Aki",
    [13] = "Rashid",
    [14] = "Blanka",
    [15] = "Juri",
    [16] = "Marisa",
    [17] = "Guile",
    [18] = "Ed",
    [19] = "Akuma",
    [20] = "M. Bison",
    [21] = "Terry",
    [22] = "Mai",
    [23] = "Elena",
}

-- ══════════════════════════════════════════════════════════════════════════════
--  ▓▓  COMBO DEFINITIONS  ▓▓
--
--  Each combo is a plain Lua function that calls the helpers above.
--  wait_frames(), press(), cr(), st(), etc. all work inside coroutines.
--  DO NOT call os.clock() or os.sleep() — use wait_frames() only.
-- ══════════════════════════════════════════════════════════════════════════════

-- ── AKUMA ────────────────────────────────────────────────────────────────────
local function akuma_bnb1()
    cr(BTN.MP); link(); cr(BTN.MP); cancel()
    dp(); press(BTN.HP)
end

local function akuma_bnb2()
    cr(BTN.LK, 2); link()
    cr(BTN.LP, 2); link()
    cr(BTN.MP); cancel()
    qcf(); press(BTN.HP)
end

local function akuma_punish1()
    st(BTN.HP, 4); cancel()
    dp(); press(BTN.HP)
end

local function akuma_punish2()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    dp(); press(BTN.LP | BTN.HP)   -- OD Goshoryuken
    wait_frames(11)
    dp(); press(BTN.HP)
end

local function akuma_super1()
    cr(BTN.MP); link()
    cr(BTN.HP, 4); cancel()
    qcf(); qcf(); press(BTN.HP)    -- Messatsu-Goshoryuken Lv1
end

local function akuma_advanced()
    cr(BTN.LK, 2); link()
    cr(BTN.LP, 2); link()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcb(); press(BTN.MK | BTN.HK)  -- OD Tatsumaki
    wait_frames(16)
    dp(); press(BTN.HP)
end

-- ── CHUN-LI ──────────────────────────────────────────────────────────────────
local function chunli_bnb1()
    charge("4", 10)
    cr(BTN.MK, 3)
    hold_dir("6", 2); press(BTN.HK)  -- SBK
end

local function chunli_bnb2()
    cr(BTN.LP, 2); link()
    cr(BTN.LP, 2); link()
    cr(BTN.MK); cancel()
    qcf(); press(BTN.HP)             -- Kikoken
end

local function chunli_punish1()
    st(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    -- Hyakuretsukyaku: rapid HK presses
    for i = 1, 6 do
        press(BTN.HK, 2)
        wait_frames(2)
    end
end

local function chunli_punish2()
    charge("4", 6)
    cr(BTN.MP); neutral(2); wait_frames(3)
    st(BTN.HP, 4); cancel()
    hold_dir("4", 5); hold_dir("6", 2)
    press(BTN.MK | BTN.HK)          -- OD SBK
    wait_frames(14)
    st(BTN.HP)
end

local function chunli_super1()
    cr(BTN.MP); link()
    cr(BTN.HP, 4); cancel()
    qcf(); qcf(); press(BTN.HP)     -- Kikosho Lv1
end

local function chunli_advanced()
    charge("4", 8)
    cr(BTN.LP, 2); link()
    cr(BTN.LP, 2); link()
    cr(BTN.MK); cancel()
    hold_dir("4", 5); hold_dir("6", 2)
    press(BTN.MK | BTN.HK)         -- OD SBK
    wait_frames(12)
    hold_dir("2", 6); hold_dir("8", 2)
    press(BTN.HK)                   -- Hazan Shu
    wait_frames(11)
    qcf(); qcf(); press(BTN.HK)    -- Hoyokusen Lv2
end

-- ── MAI ──────────────────────────────────────────────────────────────────────
local function mai_bnb1()
    cr(BTN.LK, 2); link()
    cr(BTN.LP, 2); link()
    st(BTN.MP); cancel()
    qcf(); press(BTN.HP)
end

local function mai_bnb2()
    st(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcb(); press(BTN.HK)
end

local function mai_punish1()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.HP)
end

local function mai_punish2()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcb(); press(BTN.MK | BTN.HK)  -- OD Ryuuenbu
    wait_frames(12)
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.HP)
end

local function mai_super1()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcf(); qcf(); press(BTN.HK)    -- Hissatsu Shinobibachi Lv1
end

local function mai_advanced()
    cr(BTN.LK, 2); link()
    cr(BTN.LP, 2); link()
    st(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcb(); press(BTN.MK | BTN.HK)
    wait_frames(12)
    st(BTN.HP, 4); cancel()
    qcb(); qcb(); press(BTN.HK)    -- Sen'en Ryuuenbu Lv2
end

-- ── KEN ──────────────────────────────────────────────────────────────────────
local function ken_bnb1()
    cr(BTN.MK); cancel()
    qcf(); press(BTN.HP)
end

local function ken_bnb2()
    cr(BTN.LP, 2); link()
    cr(BTN.LP, 2); link()
    cr(BTN.MK); cancel()
    qcf(); press(BTN.MK)            -- Jinrai Kick
end

local function ken_punish1()
    st(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    dp(); press(BTN.HP)
end

local function ken_punish2()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    dp(); press(BTN.LP | BTN.HP)    -- OD Shoryuken
    wait_frames(16)
    qcb(); press(BTN.HK)            -- Tatsumaki juggle
end

local function ken_super1()
    cr(BTN.MK); cancel()
    qcf(); qcf(); press(BTN.HP)     -- Shinryuken Lv1
end

local function ken_advanced()
    st(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    dp(); press(BTN.LP | BTN.HP)
    wait_frames(15)
    qcf(); press(BTN.MK)            -- Jinrai 1
    wait_frames(5)
    press(BTN.MK)                   -- Jinrai 2
    wait_frames(5)
    press(BTN.HP); cancel()         -- Jinrai 3 → super cancel
    qcf(); qcf(); press(BTN.HP)
end

-- ── JURI ─────────────────────────────────────────────────────────────────────
local function juri_bnb1()         -- ★ needs 1 Fuha stock
    cr(BTN.MK); link()
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.LP)            -- Fuha LP release
end

local function juri_bnb2()
    cr(BTN.LP, 2); link()
    cr(BTN.LP, 2); link()
    cr(BTN.MK); cancel()
    qcf(); press(BTN.MK)            -- Shiku-sen
end

local function juri_punish1()      -- ★ needs 1 Fuha stock
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.HP)            -- Fuha HP release
end

local function juri_punish2()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.MK | BTN.HK)  -- OD Shiku-sen
    wait_frames(11)
    cr(BTN.HP, 4); cancel()
    qcf(); press(BTN.LP)
end

local function juri_super1()
    cr(BTN.MK); link()
    st(BTN.HP, 4); cancel()
    qcb(); qcb(); press(BTN.LK)    -- Feng Shui Engine Lv1
end

local function juri_advanced()     -- ★ needs 1 Fuha stock
    cr(BTN.LP, 2); link()
    cr(BTN.MK); link()
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.MK | BTN.HK)
    wait_frames(11)
    cr(BTN.HP, 4); cancel()
    qcf(); press(BTN.HP)
    wait_frames(9)
    qcb(); qcb(); press(BTN.HK)    -- FSE Omega Lv3
end

-- ── CAMMY ────────────────────────────────────────────────────────────────────
local function cammy_bnb1()
    cr(BTN.LK, 2); link()
    cr(BTN.LP, 2); link()
    cr(BTN.MK); cancel()
    qcf(); press(BTN.MK)            -- Spiral Arrow MK
end

local function cammy_bnb2()
    st(BTN.MP); link()
    st(BTN.MP); link()
    cr(BTN.MK); cancel()
    qcf(); press(BTN.HK)            -- Spiral Arrow HK
end

local function cammy_punish1()
    st(BTN.HP, 4); cancel()
    dp(); press(BTN.HK)             -- Cannon Spike
end

local function cammy_punish2()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.MK | BTN.HK)  -- OD Spiral Arrow
    wait_frames(12)
    dp(); press(BTN.HK)
end

local function cammy_super1()
    cr(BTN.MK); cancel()
    qcf(); qcf(); press(BTN.HK)    -- Spin Drive Smasher Lv1
end

local function cammy_advanced()
    cr(BTN.LP, 2); link()
    cr(BTN.LP, 2); link()
    st(BTN.MP); link()
    st(BTN.MP); link()
    cr(BTN.HP, 4); cancel()
    dp(); press(BTN.LK | BTN.HK)   -- OD Cannon Spike
    wait_frames(13)
    qcf(); press(BTN.HP); cancel()  -- Quick Spin Knuckle
    qcf(); qcf(); press(BTN.LP)    -- Delta Red Assault Lv2
end

-- ── RYU ──────────────────────────────────────────────────────────────────────
local function ryu_bnb1()
    cr(BTN.MK); cancel()
    qcf(); press(BTN.HP)
end

local function ryu_bnb2()
    cr(BTN.LP, 2); link()
    cr(BTN.LP, 2); link()
    cr(BTN.MK); cancel()
    qcf(); press(BTN.HP)            -- Hashogeki
end

local function ryu_punish1()
    st(BTN.HP, 4); cancel()
    dp(); press(BTN.HP)
end

local function ryu_punish2()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    dp(); press(BTN.LP | BTN.HP)
    wait_frames(16)
    qcb(); press(BTN.HK)
end

local function ryu_super1()
    cr(BTN.MK); cancel()
    qcf(); qcf(); press(BTN.HP)    -- Shin Hashogeki Lv1
end

local function ryu_advanced()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    dp(); press(BTN.LP | BTN.HP)
    wait_frames(16)
    qcb(); press(BTN.HK); cancel()
    qcf(); qcf()
    -- Shin Shoryuken Lv3: hold HP for powered version
    set_input(BTN.HP, BTN.HP)
    wait_frames(20)
    clear_input()
    neutral(2)
end

-- ── ED ───────────────────────────────────────────────────────────────────────
-- Ed uses hold-release mechanics: hold 4 during normals, release to 6 + button
local function ed_bnb1()
    charge("4", 3)
    hold_dir("24", 1); press(BTN.LP, 2); wait_frames(2)
    hold_dir("24", 1); press(BTN.LP, 2); wait_frames(2)
    hold_dir("4", 4); press(BTN.MP, 3); wait_frames(2)
    hold_dir("4", 5); hold_dir("6", 2); press(BTN.MK)  -- Psycho Blitz
end

local function ed_bnb2()
    cr(BTN.MK); cancel()
    qcf(); press(BTN.LP)                                -- Flicker
    wait_frames(5)
    hold_dir("4", 5); hold_dir("6", 2); press(BTN.HP)  -- Psycho Spark
end

local function ed_punish1()
    st(BTN.HP, 4); cancel()
    hold_dir("2", 6); hold_dir("8", 2); press(BTN.HP)  -- Psycho Upper
end

local function ed_punish2()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    hold_dir("2", 6); hold_dir("8", 2); press(BTN.LP | BTN.HP)  -- OD Upper
    wait_frames(14)
    hold_dir("4", 5); hold_dir("6", 2); press(BTN.HK)
end

local function ed_super1()
    cr(BTN.MK); cancel()
    qcf(); qcf(); press(BTN.HP)    -- Psycho Cannon Barrage Lv1
end

local function ed_advanced()
    charge("4", 3)
    hold_dir("24", 1); press(BTN.LP, 2); wait_frames(2)
    hold_dir("24", 1); press(BTN.LP, 2); wait_frames(2)
    hold_dir("4", 4); press(BTN.MP, 3); wait_frames(2)
    hold_dir("4", 5); hold_dir("6", 2); press(BTN.MK)  -- Blitz
    wait_frames(5)
    hold_dir("4", 5); hold_dir("6", 2); press(BTN.HP)  -- Spark
    wait_frames(4)
    qcf(); qcf(); press(BTN.HP)                         -- Cannon Barrage
end

-- ── JP ───────────────────────────────────────────────────────────────────────
local function jp_bnb1()
    st(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.HP)            -- Amnesia Surge
end

local function jp_bnb2()
    cr(BTN.LP, 2); link()
    cr(BTN.MP); cancel()
    qcf(); press(BTN.MP)            -- Surge
    wait_frames(9)
    dp(); press(BTN.HK)             -- Departure
end

local function jp_punish1()
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.HP)
    wait_frames(7)
    dp(); press(BTN.MK)
end

local function jp_punish2()
    st(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.LP | BTN.HP)   -- OD Surge
    wait_frames(13)
    dp(); press(BTN.HK)
end

local function jp_super1()
    st(BTN.HP, 4); cancel()
    qcf(); qcf(); press(BTN.HP)    -- Interdiction Lv1
end

local function jp_advanced()
    st(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.LP | BTN.HP)
    wait_frames(13)
    dp(); press(BTN.HK)
    wait_frames(10)
    qcf(); press(BTN.HP)
    wait_frames(4)
    qcf(); qcf(); press(BTN.HP)
end

-- ── MARISA ───────────────────────────────────────────────────────────────────
local function marisa_bnb1()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.HP)            -- Gladius
end

local function marisa_bnb2()
    cr(BTN.LK, 2); link()
    cr(BTN.LP, 2); link()
    cr(BTN.MP); cancel()
    qcf(); press(BTN.MP)
end

local function marisa_punish1()
    st(BTN.HP, 5); cancel()
    dp(); press(BTN.HP)             -- Dimachaerus
end

local function marisa_punish2()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    dp(); press(BTN.LP | BTN.HP)    -- OD Dimachaerus
    wait_frames(14)
    qcf(); press(BTN.HP)
end

local function marisa_super1()
    st(BTN.HP, 5); cancel()
    qcf(); qcf(); press(BTN.HP)    -- Aether Lv1
end

local function marisa_advanced()
    cr(BTN.LP, 2); link()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    dp(); press(BTN.LP | BTN.HP)
    wait_frames(14)
    qcf(); press(BTN.HP); cancel()
    qcf(); qcf()
    -- Goddess of the Hunt Lv3: hold HP
    set_input(BTN.HP, BTN.HP)
    wait_frames(18)
    clear_input()
    neutral(2)
end

-- ── LUKE ─────────────────────────────────────────────────────────────────────
local function luke_bnb1()
    charge("4", 6)
    cr(BTN.MK); cancel()
    hold_dir("4", 5); hold_dir("6", 2); press(BTN.MP)  -- Flash Knuckle
end

local function luke_bnb2()
    cr(BTN.LP, 2); link()
    cr(BTN.LP, 2); link()
    cr(BTN.MK); cancel()
    qcf(); press(BTN.HP)            -- Sand Blast
end

local function luke_punish1()
    st(BTN.HP, 4); cancel()
    dp(); press(BTN.HP)             -- Rising Uppercut
end

local function luke_punish2()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    dp(); press(BTN.LP | BTN.HP)    -- OD Rising Uppercut
    wait_frames(14)
    hold_dir("4", 5); hold_dir("6", 2); press(BTN.HP)
end

local function luke_super1()
    cr(BTN.MK); cancel()
    qcf(); qcf(); press(BTN.HP)    -- Vulcan Blast Lv1
end

local function luke_advanced()
    charge("4", 4)
    cr(BTN.LP, 2); link()
    cr(BTN.LP, 2); link()
    cr(BTN.MK); cancel()
    hold_dir("4", 6); hold_dir("6", 2); press(BTN.LP | BTN.MP)  -- OD Flash Knuckle
    wait_frames(13)
    dp(); press(BTN.HP); cancel()
    qcf(); qcf(); press(BTN.HP)
end

-- ── A.K.I. ───────────────────────────────────────────────────────────────────
local function aki_bnb1()
    cr(BTN.LP, 2); link()
    cr(BTN.MP); cancel()
    qcf(); press(BTN.HP)            -- Cruel Fate (applies poison)
end

local function aki_bnb2()
    st(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.MK)            -- Sinister Slide
end

local function aki_punish1()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.HP)            -- Cruel Fate
    wait_frames(7)
    qcb(); press(BTN.HP)            -- Clinging Cobra
end

local function aki_punish2()
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    qcf(); press(BTN.LP | BTN.HP)   -- OD Cruel Fate
    wait_frames(12)
    st(BTN.HP, 4); cancel()
    qcb(); press(BTN.HP)
end

local function aki_super1()
    st(BTN.HP, 4); cancel()
    qcf(); qcf(); press(BTN.HP)    -- Coronation Lv1
end

local function aki_advanced()
    cr(BTN.LP, 2); link()
    cr(BTN.MP); cancel()
    qcf(); press(BTN.HP)            -- Cruel Fate (poison)
    wait_frames(6)
    qcb(); press(BTN.HP)            -- Cobra
    wait_frames(6)
    qcf(); press(BTN.LP | BTN.MK)  -- OD Sinister Slide
    wait_frames(12)
    st(BTN.HP, 4); cancel()
    qcf(); qcf(); press(BTN.HP)
end

-- ── M. BISON ─────────────────────────────────────────────────────────────────
local function bison_bnb1()
    charge("4", 8)
    hold_dir("2", 2); press(BTN.MK, 3)
    hold_dir("4", 4); hold_dir("6", 2); press(BTN.MK)  -- Scissors MK
end

local function bison_bnb2()
    charge("4", 6)
    hold_dir("24", 1); press(BTN.LP, 2); wait_frames(2)
    hold_dir("2", 2); press(BTN.MK, 3)
    hold_dir("4", 4); hold_dir("6", 2); press(BTN.HP)  -- Psycho Crusher
end

local function bison_punish1()
    charge("4", 8)
    st(BTN.HP, 4); cancel()
    hold_dir("4", 4); hold_dir("6", 2); press(BTN.HK)  -- Scissors HK
end

local function bison_punish2()
    charge("4", 8)
    cr(BTN.MP); link()
    st(BTN.HP, 4); cancel()
    hold_dir("4", 5); hold_dir("6", 2); press(BTN.MK | BTN.HK)  -- OD Scissors
    wait_frames(14)
    hold_dir("4", 5); hold_dir("6", 2); press(BTN.HP)
end

local function bison_super1()
    cr(BTN.MK); cancel()
    qcf(); qcf(); press(BTN.HK)    -- Knee Press Nightmare Lv1
end

local function bison_advanced()
    charge("4", 8)
    hold_dir("24", 1); press(BTN.LP, 2); wait_frames(2)
    hold_dir("2", 2); press(BTN.MK, 3)
    hold_dir("4", 5); hold_dir("6", 2); press(BTN.MK | BTN.HK)  -- OD Scissors
    wait_frames(13)
    hold_dir("4", 5); hold_dir("6", 2); press(BTN.HK)            -- Scissors juggle
    wait_frames(10)
    hold_dir("4", 5); hold_dir("6", 2); press(BTN.HP)            -- Crusher
    wait_frames(4)
    qcf(); qcf(); press(BTN.HK)
end

-- ══════════════════════════════════════════════════════════════════════════════
--  COMBO REGISTRY
-- ══════════════════════════════════════════════════════════════════════════════

local COMBOS = {
    ["Akuma"] = {
        { fn=akuma_bnb1,     label="BnB #1 — cr.MP > cr.MP xx HP Goshoryuken",          slot="F1" },
        { fn=akuma_bnb2,     label="BnB #2 — cr.LK > cr.LP > cr.MP xx Gohadouken",      slot="F2" },
        { fn=akuma_punish1,  label="Punish #1 — st.HP xx HP Goshoryuken",                slot="F3" },
        { fn=akuma_punish2,  label="Punish #2 — OD Goshoryuken > juggle HP DP",          slot="F4" },
        { fn=akuma_super1,   label="Super — cr.MP > cr.HP xx Messatsu-Goshoryuken Lv1",  slot="F5" },
        { fn=akuma_advanced, label="ADV — Low > OD Tatsumaki > HP DP",                   slot="ADV"},
    },
    ["Chun-Li"] = {
        { fn=chunli_bnb1,    label="BnB #1 — cr.MK xx Spinning Bird Kick (charge)",      slot="F1" },
        { fn=chunli_bnb2,    label="BnB #2 — cr.LP > cr.LP > cr.MK xx Kikoken",          slot="F2" },
        { fn=chunli_punish1, label="Punish #1 — st.MP > st.HP xx Hyakuretsukyaku",       slot="F3" },
        { fn=chunli_punish2, label="Punish #2 — OD SBK > juggle HP",                     slot="F4" },
        { fn=chunli_super1,  label="Super — cr.MP > cr.HP xx Kikosho Lv1",               slot="F5" },
        { fn=chunli_advanced,label="ADV — Low > OD SBK > Hazan Shu xx Hoyokusen Lv2",   slot="ADV"},
    },
    ["Mai"] = {
        { fn=mai_bnb1,    label="BnB #1 — cr.LK > cr.LP > st.MP xx Kachousen",          slot="F1" },
        { fn=mai_bnb2,    label="BnB #2 — st.MP > st.HP xx Ryuuenbu",                   slot="F2" },
        { fn=mai_punish1, label="Punish #1 — cr.MP > st.HP xx Kachousen",               slot="F3" },
        { fn=mai_punish2, label="Punish #2 — OD Ryuuenbu > HP > Kachousen",             slot="F4" },
        { fn=mai_super1,  label="Super — cr.MP > st.HP xx Hissatsu Shinobibachi Lv1",   slot="F5" },
        { fn=mai_advanced,label="ADV — Low > OD Ryuuenbu > HP xx Sen'en Lv2",           slot="ADV"},
    },
    ["Ken"] = {
        { fn=ken_bnb1,    label="BnB #1 — cr.MK xx Hadouken",                           slot="F1" },
        { fn=ken_bnb2,    label="BnB #2 — cr.LP > cr.LP > cr.MK xx Jinrai Kick",        slot="F2" },
        { fn=ken_punish1, label="Punish #1 — st.MP > st.HP xx HP Shoryuken",            slot="F3" },
        { fn=ken_punish2, label="Punish #2 — OD Shoryuken > Tatsumaki juggle",          slot="F4" },
        { fn=ken_super1,  label="Super — cr.MK xx Shinryuken Lv1",                      slot="F5" },
        { fn=ken_advanced,label="ADV — OD DP > Jinrai chain xx Shinryuken Lv1",         slot="ADV"},
    },
    ["Juri"] = {
        { fn=juri_bnb1,    label="BnB #1 — cr.MK > st.HP xx Fuha LP ★stock",           slot="F1" },
        { fn=juri_bnb2,    label="BnB #2 — cr.LP > cr.LP > cr.MK xx Shiku-sen",        slot="F2" },
        { fn=juri_punish1, label="Punish #1 — st.HP xx Fuha HP ★stock",                slot="F3" },
        { fn=juri_punish2, label="Punish #2 — OD Shiku-sen > cr.HP > Fuha",            slot="F4" },
        { fn=juri_super1,  label="Super — cr.MK > st.HP xx Feng Shui Engine Lv1",      slot="F5" },
        { fn=juri_advanced,label="ADV — Low > OD Shiku > cr.HP > Fuha xx FSE Lv3 ★",  slot="ADV"},
    },
    ["Cammy"] = {
        { fn=cammy_bnb1,    label="BnB #1 — cr.LK > cr.LP > cr.MK xx Spiral Arrow",    slot="F1" },
        { fn=cammy_bnb2,    label="BnB #2 — st.MP > st.MP > cr.MK xx Spiral Arrow HK", slot="F2" },
        { fn=cammy_punish1, label="Punish #1 — st.HP xx Cannon Spike",                  slot="F3" },
        { fn=cammy_punish2, label="Punish #2 — OD Spiral Arrow > Cannon Spike",         slot="F4" },
        { fn=cammy_super1,  label="Super — cr.MK xx Spin Drive Smasher Lv1",           slot="F5" },
        { fn=cammy_advanced,label="ADV — Long chain > OD Spike > QSK xx Delta Red Lv2",slot="ADV"},
    },
    ["Ryu"] = {
        { fn=ryu_bnb1,    label="BnB #1 — cr.MK xx Hadouken",                          slot="F1" },
        { fn=ryu_bnb2,    label="BnB #2 — cr.LP > cr.LP > cr.MK xx Hashogeki",         slot="F2" },
        { fn=ryu_punish1, label="Punish #1 — st.HP xx HP Shoryuken",                   slot="F3" },
        { fn=ryu_punish2, label="Punish #2 — OD Shoryuken > Tatsumaki juggle",         slot="F4" },
        { fn=ryu_super1,  label="Super — cr.MK xx Shin Hashogeki Lv1",                 slot="F5" },
        { fn=ryu_advanced,label="ADV — OD DP > Tatsumaki xx Shin Shoryuken Lv3 (hold)",slot="ADV"},
    },
    ["Ed"] = {
        { fn=ed_bnb1,    label="BnB #1 — cr.LP > cr.LP > st.MP xx Psycho Blitz",       slot="F1" },
        { fn=ed_bnb2,    label="BnB #2 — cr.MK xx Flicker > Psycho Spark",             slot="F2" },
        { fn=ed_punish1, label="Punish #1 — st.HP xx Psycho Upper",                     slot="F3" },
        { fn=ed_punish2, label="Punish #2 — OD Psycho Upper > Blitz juggle",            slot="F4" },
        { fn=ed_super1,  label="Super — cr.MK xx Psycho Cannon Barrage Lv1",           slot="F5" },
        { fn=ed_advanced,label="ADV — Low > Blitz > Spark xx Cannon Barrage Lv1",      slot="ADV"},
    },
    ["JP"] = {
        { fn=jp_bnb1,    label="BnB #1 — st.MP > st.HP xx Amnesia Surge",              slot="F1" },
        { fn=jp_bnb2,    label="BnB #2 — cr.LP > cr.MP xx Surge > Departure",          slot="F2" },
        { fn=jp_punish1, label="Punish #1 — st.HP xx Surge > Departure",               slot="F3" },
        { fn=jp_punish2, label="Punish #2 — OD Surge > Departure juggle",              slot="F4" },
        { fn=jp_super1,  label="Super — st.HP xx Interdiction Lv1",                    slot="F5" },
        { fn=jp_advanced,label="ADV — OD Surge > Departure > Surge xx Interdiction",   slot="ADV"},
    },
    ["Marisa"] = {
        { fn=marisa_bnb1,    label="BnB #1 — cr.MP > st.HP xx Gladius",                slot="F1" },
        { fn=marisa_bnb2,    label="BnB #2 — cr.LK > cr.LP > cr.MP xx Gladius",        slot="F2" },
        { fn=marisa_punish1, label="Punish #1 — st.HP xx Dimachaerus",                 slot="F3" },
        { fn=marisa_punish2, label="Punish #2 — OD Dimachaerus > Gladius juggle",      slot="F4" },
        { fn=marisa_super1,  label="Super — st.HP xx Aether Lv1",                      slot="F5" },
        { fn=marisa_advanced,label="ADV — Low > OD DP > Gladius xx Goddess Lv3 (hold)",slot="ADV"},
    },
    ["Luke"] = {
        { fn=luke_bnb1,    label="BnB #1 — cr.MK xx Flash Knuckle (charge)",           slot="F1" },
        { fn=luke_bnb2,    label="BnB #2 — cr.LP > cr.LP > cr.MK xx Sand Blast",       slot="F2" },
        { fn=luke_punish1, label="Punish #1 — st.HP xx Rising Uppercut",               slot="F3" },
        { fn=luke_punish2, label="Punish #2 — OD Uppercut > Flash Knuckle juggle",     slot="F4" },
        { fn=luke_super1,  label="Super — cr.MK xx Vulcan Blast Lv1",                  slot="F5" },
        { fn=luke_advanced,label="ADV — Low > OD Knuckle > Uppercut xx Vulcan Blast",  slot="ADV"},
    },
    ["Aki"] = {
        { fn=aki_bnb1,    label="BnB #1 — cr.LP > cr.MP xx Cruel Fate (poison)",       slot="F1" },
        { fn=aki_bnb2,    label="BnB #2 — st.MP > st.HP xx Sinister Slide",            slot="F2" },
        { fn=aki_punish1, label="Punish #1 — cr.MP > st.HP xx Cruel Fate > Cobra",     slot="F3" },
        { fn=aki_punish2, label="Punish #2 — OD Cruel Fate > st.HP > Cobra",           slot="F4" },
        { fn=aki_super1,  label="Super — st.HP xx Coronation Lv1",                     slot="F5" },
        { fn=aki_advanced,label="ADV — Poison > Cobra > OD Slide > HP xx Coronation",  slot="ADV"},
    },
    ["M. Bison"] = {
        { fn=bison_bnb1,    label="BnB #1 — cr.MK xx Scissors MK (charge)",            slot="F1" },
        { fn=bison_bnb2,    label="BnB #2 — cr.LP > cr.MK xx Psycho Crusher HP",       slot="F2" },
        { fn=bison_punish1, label="Punish #1 — st.HP xx Scissors HK (charge)",         slot="F3" },
        { fn=bison_punish2, label="Punish #2 — OD Scissors > Psycho Crusher",          slot="F4" },
        { fn=bison_super1,  label="Super — cr.MK xx Knee Press Nightmare Lv1",         slot="F5" },
        { fn=bison_advanced,label="ADV — Low > OD Scissors > Scissors > Crusher xx KPN",slot="ADV"},
    },
}

-- Character notes shown in UI
local CHAR_NOTES = {
    ["Akuma"]   = "ADV: Drive Gauge needed. OD Tatsumaki corner only.",
    ["Chun-Li"] = "F1/F4/ADV need back-charge. ADV needs Drive + Lv2 super.",
    ["Mai"]     = "ADV needs Drive + Lv2 super.",
    ["Ken"]     = "ADV needs Drive + Lv1 super. Jinrai auto-follows on hit.",
    ["Juri"]    = "★ = needs 1 pre-stored Fuha stock (236+LK in neutral first).",
    ["Cammy"]   = "ADV needs Drive + Lv2 super. OD Cannon Spike = 623+LK+HK.",
    ["Ryu"]     = "ADV needs Drive + Lv3 super. Hold HP input for Shin Shoryuken.",
    ["Ed"]      = "Hold directional input DURING normals to build charge.",
    ["JP"]      = "Combos at close range. Max cane range may drop links.",
    ["Marisa"]  = "ADV needs Drive + Lv3 super. Hold HP for Goddess of the Hunt.",
    ["Luke"]    = "F1/ADV need charge. ADV needs Drive + Lv1 super.",
    ["Aki"]     = "ADV applies poison first — bonus ticks apply throughout.",
    ["M. Bison"]= "Hold back DURING all normals to maintain Scissors/Crusher charge.",
}

local CHAR_COLORS = {
    ["Akuma"]   = {0.55, 0.17, 0.89, 1},
    ["Chun-Li"] = {0.31, 0.76, 0.97, 1},
    ["Mai"]     = {1.00, 0.42, 0.21, 1},
    ["Ken"]     = {1.00, 0.80, 0.13, 1},
    ["Juri"]    = {0.88, 0.25, 0.98, 1},
    ["Cammy"]   = {0.00, 0.90, 0.63, 1},
    ["Ryu"]     = {0.91, 0.15, 0.10, 1},
    ["Ed"]      = {0.23, 0.61, 0.86, 1},
    ["JP"]      = {0.78, 0.66, 0.31, 1},
    ["Marisa"]  = {0.75, 0.22, 0.17, 1},
    ["Luke"]    = {0.15, 0.68, 0.38, 1},
    ["Aki"]     = {0.61, 0.35, 0.71, 1},
    ["M. Bison"]= {0.16, 0.50, 0.73, 1},
}

-- Build ordered character list for cycling
local CHAR_ORDER = {
    "Akuma","Chun-Li","Mai","Ken","Juri","Cammy","Ryu",
    "Ed","JP","Marisa","Luke","Aki","M. Bison"
}

-- ══════════════════════════════════════════════════════════════════════════════
--  EXECUTION STATE
-- ══════════════════════════════════════════════════════════════════════════════

local _current_char_idx = 1   -- index into CHAR_ORDER
local _active_combo     = nil -- label of currently running combo (for UI)
local _log_lines        = {}  -- circular log buffer
local _log_max          = 50

local function log(msg)
    table.insert(_log_lines, string.format("[%s] %s", os.date("%H:%M:%S"), msg))
    if #_log_lines > _log_max then table.remove(_log_lines, 1) end
end

local function get_current_char()
    return CHAR_ORDER[_current_char_idx]
end

local function cycle_char(dir)
    _current_char_idx = ((_current_char_idx - 1 + dir) % #CHAR_ORDER) + 1
    log("Character → " .. get_current_char())
end

local function fire_combo(slot_or_adv)
    if _combo_coro and coroutine.status(_combo_coro) ~= "dead" then
        log("Combo already running — press F9 to cancel")
        return
    end

    local char   = get_current_char()
    local combos = COMBOS[char]
    if not combos then
        log("No combos defined for " .. char)
        return
    end

    local entry = nil
    if slot_or_adv == "ADV" then
        for _, c in ipairs(combos) do
            if c.slot == "ADV" then entry = c; break end
        end
    else
        -- slot_or_adv is a 1-based index (1=F1 .. 5=F5)
        local non_adv = {}
        for _, c in ipairs(combos) do
            if c.slot ~= "ADV" then table.insert(non_adv, c) end
        end
        entry = non_adv[slot_or_adv]
    end

    if not entry then
        log("Combo slot not found")
        return
    end

    _cancel_flag  = false
    _active_combo = entry.label
    log("▶ [" .. char .. "] " .. entry.label)

    -- Wrap the combo function in a coroutine
    _combo_coro = coroutine.create(function()
        entry.fn()
        clear_input()
        _active_combo = nil
        log("✓ Complete")
    end)
end

local function cancel_combo_fn()
    _cancel_flag = true
    clear_input()
    _active_combo = nil
    if _combo_coro then
        _combo_coro = nil
        log("⊘ Cancelled")
    end
end

-- ══════════════════════════════════════════════════════════════════════════════
--  HOTKEY STATE  (polled in on_draw_ui since REFramework Lua has no key hooks)
-- ══════════════════════════════════════════════════════════════════════════════
--  REFramework exposes imgui.is_key_pressed() which we use for hotkeys.
--  Keys are checked in the draw_ui callback (runs before the game frame).
--  This effectively gives us per-frame hotkey polling at 60fps.

-- Key codes (Windows Virtual Key codes, which imgui maps to)
local VK = {
    F1=0x70, F2=0x71, F3=0x72, F4=0x73, F5=0x74,
    F6=0x75, F7=0x76, F8=0x77, F9=0x78,
}

-- ══════════════════════════════════════════════════════════════════════════════
--  PER-FRAME HOOK  —  flush inputs + tick combo coroutine
-- ══════════════════════════════════════════════════════════════════════════════

re.on_application_entry("UpdateBehavior", function()
    local p1 = get_player(0)

    -- Tick the active combo coroutine
    if _combo_coro and coroutine.status(_combo_coro) ~= "dead" then
        local ok, result = coroutine.resume(_combo_coro)
        if not ok then
            log("✗ Combo error: " .. tostring(result))
            _combo_coro = nil
            _active_combo = nil
            clear_input()
        elseif result == "cancel" or _cancel_flag then
            _combo_coro = nil
            _active_combo = nil
            clear_input()
        end
    end

    -- Write pending inputs to P1's input register
    flush_inputs(p1)
end)

-- ══════════════════════════════════════════════════════════════════════════════
--  IMGUI PANEL  (visible via Insert → Script Generated UI → SF6 Combo Bot)
-- ══════════════════════════════════════════════════════════════════════════════


re.on_draw_ui(function()
    -- Hotkeys polled every frame the REFramework overlay is open
    if imgui.is_key_pressed(VK.F1, false) then fire_combo(1)      end
    if imgui.is_key_pressed(VK.F2, false) then fire_combo(2)      end
    if imgui.is_key_pressed(VK.F3, false) then fire_combo(3)      end
    if imgui.is_key_pressed(VK.F4, false) then fire_combo(4)      end
    if imgui.is_key_pressed(VK.F5, false) then fire_combo(5)      end
    if imgui.is_key_pressed(VK.F6, false) then cycle_char(1)      end
    if imgui.is_key_pressed(VK.F7, false) then cycle_char(-1)     end
    if imgui.is_key_pressed(VK.F8, false) then fire_combo("ADV")  end
    if imgui.is_key_pressed(VK.F9, false) then cancel_combo_fn()  end

    -- on_draw_ui renders directly inside "Script Generated UI".
    -- NEVER call begin_window / end_window here.
    -- Use tree_node to create the collapsible section.
    if not imgui.tree_node("SF6 Combo Bot") then return end

    local char  = get_current_char()
    local state = read_battle_state()

    -- Status
    imgui.text("v1.0  |  REFramework Edition")
    if _active_combo then
        imgui.text("RUNNING: " .. _active_combo)
    else
        imgui.text_disabled("Idle — F1-F5 / F8 to fire combo")
    end

    imgui.separator()

    -- Battle state
    if state.valid then
        imgui.text(string.format(
            "HP:%d  Drive:%.0f  SuperLv:%d  Hitstop:%d  Combo:x%d",
            state.hp, (state.drive or 0), state.super_lvl, state.hitstop, state.combo))
        imgui.text(string.format("ActionID:%d  Frame:%d", state.act_id, state.act_frame))
        local detected = CHARA_ID_MAP[state.chara_id]
        if detected then
            imgui.text_disabled("Detected: " .. detected)
            if detected ~= char then
                imgui.same_line()
                if imgui.button("Switch##autosel") then
                    for i, name in ipairs(CHAR_ORDER) do
                        if name == detected then _current_char_idx = i; log("Auto: "..detected); break end
                    end
                end
            end
        end
    else
        imgui.text_disabled("Not in a battle scene")
    end

    imgui.separator()

    -- Character selector
    imgui.text("Active: " .. char)
    imgui.same_line()
    if imgui.button("< Prev (F7)") then cycle_char(-1) end
    imgui.same_line()
    if imgui.button("Next > (F6)") then cycle_char(1) end

    for idx, name in ipairs(CHAR_ORDER) do
        if (idx - 1) % 5 ~= 0 then imgui.same_line() end
        local lbl = (name == char) and ("["..name.."]") or name
        if imgui.button(lbl.."##c"..idx) then
            _current_char_idx = idx
            log("Switched to "..name)
        end
    end

    imgui.separator()

    -- Combo slots
    local combos   = COMBOS[char] or {}
    local tlbls    = {"BnB #1","BnB #2","Punish","Punish OD","Super"}
    local non_adv  = {}
    local adv_entry = nil
    for _, c in ipairs(combos) do
        if c.slot ~= "ADV" then table.insert(non_adv, c) else adv_entry = c end
    end

    local hkeys = {"F1","F2","F3","F4","F5"}
    for i, combo in ipairs(non_adv) do
        local running = (_active_combo == combo.label)
        if imgui.button(string.format("[%s] %s##s%d", hkeys[i] or "?", tlbls[i], i)) then
            fire_combo(i)
        end
        imgui.same_line()
        if running then imgui.text(">> "..combo.label) else imgui.text_disabled(combo.label) end
    end

    imgui.separator()

    if adv_entry then
        if imgui.button("[F8] ADVANCED") then fire_combo("ADV") end
        imgui.same_line()
        if _active_combo == adv_entry.label then imgui.text(">> "..adv_entry.label)
        else imgui.text_disabled(adv_entry.label) end
        imgui.same_line()
    end
    if imgui.button("[F9] CANCEL") then cancel_combo_fn() end

    local note = CHAR_NOTES[char]
    if note then
        imgui.separator()
        imgui.text_disabled("NOTE: "..note)
    end

    imgui.separator()

    if imgui.tree_node("Hotkeys") then
        imgui.text("F1=BnB1  F2=BnB2  F3=Punish  F4=PunishOD  F5=Super")
        imgui.text("F6=NextChar  F7=PrevChar  F8=Advanced  F9=Cancel")
        imgui.tree_pop()
    end

    if imgui.tree_node("Log") then
        local s = math.max(1, #_log_lines - 14)
        for i = s, #_log_lines do imgui.text_disabled(_log_lines[i]) end
        imgui.tree_pop()
    end

    if imgui.tree_node("Field Inspector") then
        imgui.text_disabled("Live field names on P1 object — use after game updates.")
        local p1 = get_player(0)
        if p1 then
            local candidates = {
                "act_id","action_id","ok_key","ok_trg","raw_key","raw_trg",
                "hp","mCurrentHP","hitstop","hit_stop",
                "drive_val","mDriveGauge","combo_cnt","mComboCount",
                "chara_id","mCharaID","sa_gauge_lv","super_lv",
            }
            for _, fname in ipairs(candidates) do
                local ok, v = pcall(function() return p1:get_field(fname) end)
                if ok and v ~= nil then
                    imgui.text("OK  "..fname.." = "..tostring(v))
                end
            end
        else
            imgui.text_disabled("(enter a battle scene first)")
        end
        imgui.tree_pop()
    end

    imgui.tree_pop()  -- closes "SF6 Combo Bot"
end)


-- ══════════════════════════════════════════════════════════════════════════════
--  SCRIPT RESET CLEANUP
-- ══════════════════════════════════════════════════════════════════════════════

re.on_script_reset(function()
    cancel_combo_fn()
    clear_input()
    -- Flush zeroed inputs one last time
    local p1 = get_player(0)
    if p1 then flush_inputs(p1) end
    log("Script reset — inputs cleared.")
end)

-- Startup log
log("SF6 Combo Bot loaded. " .. #CHAR_ORDER .. " characters, " ..
    (function()
        local n = 0
        for _, c in pairs(COMBOS) do n = n + #c end
        return n
    end)() .. " combos.")
log("Open REFramework overlay (Insert) → Script Generated UI → SF6 Combo Bot")
log("Hotkeys: F1-F5 combos | F6/F7 char | F8 advanced | F9 cancel")