# SF6 Combo Bot — Pure REFramework Mod

**Single Lua file. No Python. No virtual gamepad. No ViGEmBus.**  
Runs entirely inside Street Fighter 6 via REFramework.

---

## How It Works

This mod writes directly to SF6's internal input register (`ok_key` / `ok_trg`)
each game frame via REFramework's `sdk.set_field`. Inputs go through exactly the
same code path as a real controller — frame-perfect by definition because the
script runs on the same thread as the game loop.

Combos are Lua coroutines. Each step calls `wait_frames(n)`, which yields the
coroutine n times — one yield per game frame. Timing is expressed in actual game
frames, not wall-clock milliseconds. Hitstop is handled automatically because the
coroutine simply doesn't advance while you tell it to wait.

---

## Install

### 1 — REFramework
https://github.com/praydog/REFramework-nightly/releases  
→ Download **SF6.zip**  
→ Extract `dinput8.dll` into your SF6 game folder (same folder as `StreetFighter6.exe`)

### 2 — This mod
Copy the `reframework/` folder from this archive into your SF6 game folder.  
Final path should be:
```
<SF6 folder>/reframework/autorun/sf6_combo_bot.lua
```

### 3 — Launch SF6
REFramework loads all scripts in `autorun/` automatically on startup.  
Press **Insert** to open the REFramework overlay.  
Navigate to **Script Generated UI → SF6 Combo Bot**.

---

## Hotkeys

| Key    | Action                         |
|--------|--------------------------------|
| **F1** | BnB #1                         |
| **F2** | BnB #2                         |
| **F3** | Punish #1                      |
| **F4** | Punish #2 (OD / Drive)         |
| **F5** | BnB into Super                 |
| **F6** | Next character →               |
| **F7** | Previous character ←           |
| **F8** | Advanced combo                 |
| **F9** | Cancel / abort running combo   |

Hotkeys are polled every frame and work while SF6 has focus (REFramework overlay
does not need to be open for hotkeys to work once the script is loaded).

---

## UI Panel Features

- **Live battle state** — HP, Drive gauge, Super level, hitstop, combo count, current animation ID
- **Character auto-detect** — reads `chara_id` from the player object and offers a one-click "Use [Character]" button to switch the active combo set
- **Per-character notes** — meter requirements, charge reminders, Fuha stock warnings
- **Executing combo highlight** — the active combo slot turns green while running
- **Developer: Field Inspector** — scans common field name variants and shows which ones are live, useful after game updates change internal names
- **Log panel** — timestamped execution log (last 50 lines)

---

## Characters & Combos

| # | Character | Notes |
|---|-----------|-------|
| 1 | Akuma     | ADV: Drive needed. OD Tatsumaki corner only. |
| 2 | Chun-Li   | F1/F4/ADV need back-charge. ADV: Drive + Lv2 super. |
| 3 | Mai       | ADV: Drive + Lv2 super. |
| 4 | Ken       | ADV: Drive + Lv1 super. Jinrai auto-follows on hit. |
| 5 | Juri      | ★ F1/F3/ADV need 1 pre-stored Fuha stock (236+LK first). |
| 6 | Cammy     | ADV: Drive + Lv2 super. OD Cannon Spike = 623+LK+HK. |
| 7 | Ryu       | ADV: Drive + Lv3 super. Hold HP input for Shin Shoryuken. |
| 8 | Ed        | Hold direction DURING normals to build charge. |
| 9 | JP        | Close range only — max cane range drops links. |
| 10| Marisa   | ADV: Drive + Lv3 super. Even short combos deal huge damage. |
| 11| Luke     | F1/ADV need charge. ADV: Drive + Lv1 super. |
| 12| A.K.I.   | ADV applies poison first — bonus ticks throughout. |
| 13| M. Bison | Hold back DURING all normals to maintain charge. |

Each character has 6 combos: F1, F2, F3, F4, F5, and F8 (Advanced).  
**78 combos total.**

### Full Combo List

#### AKUMA
| Key | Combo |
|-----|-------|
| F1  | cr.MP > cr.MP xx HP Goshoryuken |
| F2  | cr.LK > cr.LP > cr.MP xx Gohadouken |
| F3  | st.HP xx HP Goshoryuken |
| F4  | cr.MP > st.HP xx OD Goshoryuken > juggle HP DP |
| F5  | cr.MP > cr.HP xx Messatsu-Goshoryuken Lv1 |
| F8  | cr.LK > cr.LP > cr.MP > st.HP xx OD Tatsumaki > juggle HP DP |

#### CHUN-LI
| Key | Combo |
|-----|-------|
| F1  | cr.MK xx Spinning Bird Kick (charge 4→6) |
| F2  | cr.LP > cr.LP > cr.MK xx Kikoken |
| F3  | st.MP > st.HP xx Hyakuretsukyaku (6 rapid hits) |
| F4  | cr.MP > st.HP xx OD SBK > juggle HP |
| F5  | cr.MP > cr.HP xx Kikosho Lv1 |
| F8  | Low starter > OD SBK > Hazan Shu xx Hoyokusen Lv2 |

#### MAI
| Key | Combo |
|-----|-------|
| F1  | cr.LK > cr.LP > st.MP xx Kachousen |
| F2  | st.MP > st.HP xx Ryuuenbu |
| F3  | cr.MP > st.HP xx Kachousen |
| F4  | cr.MP > st.HP xx OD Ryuuenbu > HP > Kachousen |
| F5  | cr.MP > st.HP xx Hissatsu Shinobibachi Lv1 |
| F8  | Low > OD Ryuuenbu > HP xx Sen'en Ryuuenbu Lv2 |

#### KEN
| Key | Combo |
|-----|-------|
| F1  | cr.MK xx Hadouken |
| F2  | cr.LP > cr.LP > cr.MK xx Jinrai Kick |
| F3  | st.MP > st.HP xx HP Shoryuken |
| F4  | cr.MP > st.HP xx OD Shoryuken > Tatsumaki juggle |
| F5  | cr.MK xx Shinryuken Lv1 |
| F8  | st.MP > st.HP xx OD DP > Jinrai chain (3 hits) xx Shinryuken Lv1 |

#### JURI ★ = needs pre-stored Fuha stock
| Key | Combo |
|-----|-------|
| F1  | cr.MK > st.HP xx Fuha LP Release ★ |
| F2  | cr.LP > cr.LP > cr.MK xx Shiku-sen |
| F3  | st.HP xx Fuha HP Release ★ |
| F4  | cr.MP > st.HP xx OD Shiku-sen > cr.HP > Fuha |
| F5  | cr.MK > st.HP xx Feng Shui Engine Lv1 |
| F8  | Low > OD Shiku > cr.HP > Fuha HP xx FSE Omega Lv3 ★ |

#### CAMMY
| Key | Combo |
|-----|-------|
| F1  | cr.LK > cr.LP > cr.MK xx Spiral Arrow MK |
| F2  | st.MP > st.MP > cr.MK xx Spiral Arrow HK |
| F3  | st.HP xx Cannon Spike |
| F4  | cr.MP > st.HP xx OD Spiral Arrow > Cannon Spike |
| F5  | cr.MK xx Spin Drive Smasher Lv1 |
| F8  | Long chain > OD Cannon Spike > QSK xx Delta Red Assault Lv2 |

#### RYU
| Key | Combo |
|-----|-------|
| F1  | cr.MK xx Hadouken |
| F2  | cr.LP > cr.LP > cr.MK xx Hashogeki |
| F3  | st.HP xx HP Shoryuken |
| F4  | cr.MP > st.HP xx OD Shoryuken > Tatsumaki |
| F5  | cr.MK xx Shin Hashogeki Lv1 |
| F8  | OD DP > Tatsumaki xx Shin Shoryuken Lv3 (hold HP) |

#### ED (hold direction during normals for charge)
| Key | Combo |
|-----|-------|
| F1  | cr.LP > cr.LP > st.MP xx Psycho Blitz (4→6+MK) |
| F2  | cr.MK xx Flicker > Psycho Spark (4→6+HP) |
| F3  | st.HP xx Psycho Upper (2→8+HP) |
| F4  | cr.MP > st.HP xx OD Psycho Upper > Blitz juggle |
| F5  | cr.MK xx Psycho Cannon Barrage Lv1 |
| F8  | Low > Blitz > Spark cancel xx Cannon Barrage Lv1 |

#### JP (close range)
| Key | Combo |
|-----|-------|
| F1  | st.MP > st.HP xx Amnesia Surge HP |
| F2  | cr.LP > cr.MP xx Surge > Departure |
| F3  | st.HP xx Surge > Departure |
| F4  | st.MP > st.HP xx OD Surge > Departure juggle |
| F5  | st.HP xx Interdiction Lv1 |
| F8  | OD Surge > Departure > Surge xx Interdiction Lv1 |

#### MARISA
| Key | Combo |
|-----|-------|
| F1  | cr.MP > st.HP xx Gladius |
| F2  | cr.LK > cr.LP > cr.MP xx Gladius |
| F3  | st.HP xx Dimachaerus |
| F4  | cr.MP > st.HP xx OD Dimachaerus > Gladius juggle |
| F5  | st.HP xx Aether Lv1 |
| F8  | Low > OD Dimachaerus > Gladius xx Goddess of the Hunt Lv3 (hold HP) |

#### LUKE (F1/F8 need charge)
| Key | Combo |
|-----|-------|
| F1  | cr.MK xx Flash Knuckle MP (hold 4→6) |
| F2  | cr.LP > cr.LP > cr.MK xx Sand Blast |
| F3  | st.HP xx Rising Uppercut |
| F4  | cr.MP > st.HP xx OD Rising Uppercut > Flash Knuckle juggle |
| F5  | cr.MK xx Vulcan Blast Lv1 |
| F8  | Low > OD Flash Knuckle > Uppercut xx Vulcan Blast Lv1 |

#### A.K.I.
| Key | Combo |
|-----|-------|
| F1  | cr.LP > cr.MP xx Cruel Fate (applies poison) |
| F2  | st.MP > st.HP xx Sinister Slide |
| F3  | cr.MP > st.HP xx Cruel Fate > Clinging Cobra |
| F4  | cr.MP > st.HP xx OD Cruel Fate > st.HP > Clinging Cobra |
| F5  | st.HP xx Coronation Lv1 |
| F8  | Poison > Cobra > OD Slide > st.HP xx Coronation Lv1 |

#### M. BISON (hold back during all normals)
| Key | Combo |
|-----|-------|
| F1  | cr.MK xx Scissors Kick MK (charge 4→6) |
| F2  | cr.LP > cr.MK xx Psycho Crusher HP |
| F3  | st.HP xx Scissors HK (charge) |
| F4  | cr.MP > st.HP xx OD Scissors > Psycho Crusher |
| F5  | cr.MK xx Knee Press Nightmare Lv1 |
| F8  | Low > OD Scissors > Scissors juggle > Crusher xx KPN Lv1 |

---

## If Combos Don't Execute After a Game Update

Capcom patches can rename internal fields. Open the REFramework overlay and expand:

**SF6 Combo Bot → Developer: Field Inspector**

This panel automatically scans common field name variants and shows which ones
are currently readable. Update the field names at the top of `sf6_combo_bot.lua`
in the `read_battle_state()` function to match.

You can also use **REFramework → Developer Tools → Object Explorer → Singletons → gBattle**
to browse the full live object tree and find current field names.

---

## Controller Mapping Reference

The input bitflags in the script correspond to SF6 Classic controls:

| SF6    | Bit flag | | SF6    | Bit flag |
|--------|----------|-|--------|----------|
| LP     | 0x001    | | LK     | 0x008    |
| MP     | 0x002    | | MK     | 0x010    |
| HP     | 0x004    | | HK     | 0x020    |
| Up     | 0x040    | | Down   | 0x080    |
| Back   | 0x100    | | Fwd    | 0x200    |

Edit the `BTN` table at the top of the script if SF6 uses different values
in your version (verify with Field Inspector → ok_key while pressing buttons).