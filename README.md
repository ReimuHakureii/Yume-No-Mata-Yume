# SF6 World Tour Combo Bot v4

**13 characters · 78 total combos · Advanced combo per character**

Akuma · Chun-Li · Mai · Ken · Juri · Cammy · Ryu · Ed · JP
Marisa · Luke · A.K.I. · M. Bison

---

## Setup

```bash
# 1. Install ViGEmBus driver (REQUIRED)
# https://github.com/ViGEm/ViGEmBus/releases → ViGEmBus_Setup_x64.msi

# 2. Install Python packages
pip install vgamepad keyboard

# 3. Run
python combo_bot.py
```

---

## Hotkeys

| Key       | Action                              |
|-----------|-------------------------------------|
| **F1**    | BnB #1 (current character)          |
| **F2**    | BnB #2 (current character)          |
| **F3**    | Punish #1                           |
| **F4**    | Punish #2 (OD / Drive meter)        |
| **F5**    | BnB into Super                      |
| **F6**    | Next character →                    |
| **F7**    | Previous character ←                |
| **F8**    | Advanced combo (current character)  |
| **ESC**   | Cancel combo mid-execution          |

---

## v4 Code Improvements

- **`_sleep()` with cancel flag** — ESC now cleanly aborts any running combo and releases all inputs
- **`f(frames)` via `perf_counter`** — High-resolution timing instead of `time.sleep` approximations  
- **`cr()` / `st()` helpers** — Eliminate repeated stick+button boilerplate throughout all combos
- **`hold_charge()` helper** — Clean, explicit charge mechanic for Chun-Li, Bison, Luke, Ed
- **`link()` / `cancel()` semantics** — Distinguishes between linked normals and cancelled specials  
- **Progress row highlight** — The GUI highlights which combo slot is currently executing
- **Per-character notes panel** — Displays special requirements (charge, stock, meter) per character
- **`_entry()` factory** — Combo registry is cleaner and less repetitive
- **Clean input release on cancel** — No stuck buttons if a combo is interrupted

---

## All Combos

### AKUMA
| Key | Combo |
|-----|-------|
| F1  | cr.MP > cr.MP xx HP Goshoryuken |
| F2  | cr.LK > cr.LP > cr.MP xx Gohadouken |
| F3  | st.HP xx HP Goshoryuken |
| F4  | cr.MP > st.HP xx OD Goshoryuken > juggle HP DP |
| F5  | cr.MP > cr.HP xx Messatsu-Goshoryuken Lv1 |
| ADV | cr.LK > cr.LP > cr.MP > st.HP xx OD Tatsumaki > juggle HP DP |

### CHUN-LI
| Key | Combo |
|-----|-------|
| F1  | cr.MK xx Spinning Bird Kick (charge 4→6) |
| F2  | cr.LP > cr.LP > cr.MK xx Kikoken |
| F3  | st.MP > st.HP xx Hyakuretsukyaku (6 hits) |
| F4  | cr.MP > st.HP xx OD SBK > juggle HP |
| F5  | cr.MP > cr.HP xx Kikosho Lv1 |
| ADV | Low starter > OD SBK > Hazan Shu xx Hoyokusen Lv2 |

### MAI
| Key | Combo |
|-----|-------|
| F1  | cr.LK > cr.LP > st.MP xx Kachousen |
| F2  | st.MP > st.HP xx Ryuuenbu |
| F3  | cr.MP > st.HP xx Kachousen |
| F4  | cr.MP > st.HP xx OD Ryuuenbu > HP > Kachousen |
| F5  | cr.MP > st.HP xx Hissatsu Shinobibachi Lv1 |
| ADV | Low starter > OD Ryuuenbu > HP xx Sen'en Ryuuenbu Lv2 |

### KEN
| Key | Combo |
|-----|-------|
| F1  | cr.MK xx Hadouken |
| F2  | cr.LP > cr.LP > cr.MK xx Jinrai Kick |
| F3  | st.MP > st.HP xx HP Shoryuken |
| F4  | cr.MP > st.HP xx OD Shoryuken > Tatsumaki juggle |
| F5  | cr.MK xx Shinryuken Lv1 |
| ADV | st.MP > st.HP xx OD DP > Jinrai chain (3 hits) xx Shinryuken Lv1 |

### JURI ★ = needs pre-stored Fuha stock (236+LK beforehand)
| Key | Combo |
|-----|-------|
| F1  | cr.MK > st.HP xx Fuha LP Release ★ |
| F2  | cr.LP > cr.LP > cr.MK xx Shiku-sen |
| F3  | st.HP xx Fuha HP Release ★ |
| F4  | cr.MP > st.HP xx OD Shiku-sen > cr.HP > Fuha |
| F5  | cr.MK > st.HP xx Feng Shui Engine Lv1 |
| ADV | Low > OD Shiku > cr.HP > Fuha HP xx FSE Omega Lv3 ★ |

### CAMMY
| Key | Combo |
|-----|-------|
| F1  | cr.LK > cr.LP > cr.MK xx Spiral Arrow MK |
| F2  | st.MP > st.MP > cr.MK xx Spiral Arrow HK |
| F3  | st.HP xx Cannon Spike |
| F4  | cr.MP > st.HP xx OD Spiral Arrow > Cannon Spike |
| F5  | cr.MK xx Spin Drive Smasher Lv1 |
| ADV | Long chain > OD Cannon Spike > QSK xx Delta Red Assault Lv2 |

### RYU
| Key | Combo |
|-----|-------|
| F1  | cr.MK xx Hadouken |
| F2  | cr.LP > cr.LP > cr.MK xx Hashogeki |
| F3  | st.HP xx HP Shoryuken |
| F4  | cr.MP > st.HP xx OD Shoryuken > Tatsumaki |
| F5  | cr.MK xx Shin Hashogeki Lv1 |
| ADV | OD DP > Tatsumaki xx Shin Shoryuken Lv3 (hold HP for powered) |

### ED (charge: hold 4→6 or 2→8 during normals)
| Key | Combo |
|-----|-------|
| F1  | cr.LP > cr.LP > st.MP xx Psycho Blitz (4→6+MK) |
| F2  | cr.MK xx Flicker > Psycho Spark (4→6+HP) |
| F3  | st.HP xx Psycho Upper (2→8+HP) |
| F4  | cr.MP > st.HP xx OD Psycho Upper > Blitz juggle |
| F5  | cr.MK xx Psycho Cannon Barrage Lv1 |
| ADV | Low > Blitz > Spark cancel xx Cannon Barrage Lv1 |

### JP (close range recommended)
| Key | Combo |
|-----|-------|
| F1  | st.MP > st.HP xx Amnesia Surge HP |
| F2  | cr.LP > cr.MP xx Surge > Departure |
| F3  | st.HP xx Surge > Departure |
| F4  | st.MP > st.HP xx OD Surge > Departure juggle |
| F5  | st.HP xx Interdiction Lv1 |
| ADV | OD Surge > Departure > Surge xx Interdiction Lv1 |

### MARISA
| Key | Combo |
|-----|-------|
| F1  | cr.MP > st.HP xx Gladius |
| F2  | cr.LK > cr.LP > cr.MP xx Gladius |
| F3  | st.HP xx Dimachaerus |
| F4  | cr.MP > st.HP xx OD Dimachaerus > Gladius juggle |
| F5  | st.HP xx Aether Lv1 |
| ADV | Low > OD Dimachaerus > Gladius xx Goddess of the Hunt Lv3 (hold HP) |

### LUKE (F1/ADV require charge)
| Key | Combo |
|-----|-------|
| F1  | cr.MK xx Flash Knuckle MP (hold 4→6) |
| F2  | cr.LP > cr.LP > cr.MK xx Sand Blast |
| F3  | st.HP xx Rising Uppercut |
| F4  | cr.MP > st.HP xx OD Rising Uppercut > Flash Knuckle juggle |
| F5  | cr.MK xx Vulcan Blast Lv1 |
| ADV | Low > OD Flash Knuckle > Uppercut xx Vulcan Blast Lv1 |

### A.K.I. (poison applies bonus damage ticks)
| Key | Combo |
|-----|-------|
| F1  | cr.LP > cr.MP xx Cruel Fate (poison) |
| F2  | st.MP > st.HP xx Sinister Slide |
| F3  | cr.MP > st.HP xx Cruel Fate > Clinging Cobra |
| F4  | cr.MP > st.HP xx OD Cruel Fate > HP > Clinging Cobra |
| F5  | st.HP xx Coronation Lv1 |
| ADV | Poison > Cobra > OD Slide > HP xx Coronation Lv1 |

### M. BISON (all specials are charge — hold back DURING normals)
| Key | Combo |
|-----|-------|
| F1  | cr.MK xx Scissors Kick MK (charge 4→6) |
| F2  | cr.LP > cr.MK xx Psycho Crusher HP |
| F3  | st.HP xx Scissors HK (charge) |
| F4  | cr.MP > st.HP xx OD Scissors > Psycho Crusher |
| F5  | cr.MK xx Knee Press Nightmare Lv1 |
| ADV | Low > OD Scissors > Scissors > Crusher xx KPN Lv1 |

---

## Controller Mapping (SF6 Classic, Xbox)

| SF6 | Xbox | | SF6 | Xbox |
|-----|------|-|-----|------|
| LP  | X    | | LK  | A    |
| MP  | Y    | | MK  | B    |
| HP  | RB   | | HK  | RT   |

Edit `_BTN` dict in `combo_bot.py` if your mapping differs.

---

## Tuning
- **Inputs dropping?** → Raise Frame Scale (1.2–1.5)  
- **Too slow?** → Lower Frame Scale (0.8–0.9)
- Charge combos: bot holds the charge direction **during** normals — if dropping, raise Frame Scale by 0.2
- OD / Advanced combos require Drive Gauge; Super routes require super meter
- Press **ESC** at any time to abort a running combo cleanly
