# SF6 World Tour Combo Bot v3

Auto-executes combos for **9 characters** in SF6 World Tour mode via hotkeys.
Akuma · Chun-Li · Mai · Ken · Juri · Cammy · Ryu · Ed · JP

Uses a virtual Xbox 360 gamepad (ViGEmBus) — SF6 sees it as a real controller.

---

## Requirements

### 1. ViGEmBus Driver (REQUIRED)
https://github.com/ViGEm/ViGEmBus/releases → install `ViGEmBus_Setup_x64.msi`

### 2. Python Packages
```bash
pip install vgamepad keyboard
```

---

## Running
```bash
python combo_bot.py
```
Alt-tab into SF6, select your character in the GUI or use F6/F7, then press F1–F5.

---

## Hotkeys

| Key     | Action                         |
|---------|--------------------------------|
| **F1**  | BnB #1 (current character)     |
| **F2**  | BnB #2 (current character)     |
| **F3**  | Punish #1                      |
| **F4**  | Punish #2 / OD combo           |
| **F5**  | BnB into Super                 |
| **F6**  | Next character →               |
| **F7**  | Previous character ←           |

---

## All Combos

### AKUMA
| Key | Combo |
|-----|-------|
| F1 | cr.MP xx cr.MP xx HP Goshoryuken |
| F2 | cr.LK > cr.LP > cr.MP xx Gohadouken |
| F3 | st.HP xx HP Goshoryuken |
| F4 | cr.MP > st.HP xx OD Goshoryuken > juggle HP DP |
| F5 | cr.MP > cr.HP xx Messatsu-Goshoryu (214214+HP) |

### CHUN-LI
| Key | Combo |
|-----|-------|
| F1 | cr.MK xx Spinning Bird Kick (charge) |
| F2 | cr.LP > cr.LP > cr.MK xx Kikoken |
| F3 | st.MP > st.HP xx Hyakuretsukyaku |
| F4 | cr.MP > st.HP xx OD SBK > juggle HP |
| F5 | cr.MP > cr.HP xx Kikosho (236236+HP) |

### MAI
| Key | Combo |
|-----|-------|
| F1 | cr.LK > cr.LP > st.MP xx Kachousen |
| F2 | st.MP > st.HP xx Ryuuenbu |
| F3 | cr.MP > st.HP xx Kachousen |
| F4 | cr.MP > st.HP xx OD Ryuuenbu > juggle HP |
| F5 | cr.MP > st.HP xx Hissatsu Shinobibachi (236236+HK) |

### KEN
| Key | Combo |
|-----|-------|
| F1 | cr.MK xx Hadouken |
| F2 | cr.LP > cr.LP > cr.MK xx Jinrai Kick |
| F3 | st.MP > st.HP xx HP Shoryuken |
| F4 | cr.MP > st.HP xx OD Shoryuken > Tatsumaki juggle |
| F5 | cr.MK xx Shinryuken (236236+HP) |

### JURI
| Key | Combo |
|-----|-------|
| F1 | cr.MK > st.HP xx Fuha Release LP *(needs 1 stock)* |
| F2 | cr.LP > cr.LP > cr.MK xx Shiku-sen |
| F3 | st.HP xx Fuha Release HP *(needs 1 stock)* |
| F4 | cr.MP > st.HP xx OD Shiku-sen > cr.HP > Fuha Release |
| F5 | cr.MK > st.HP xx Feng Shui Engine (214214+LK) |

### CAMMY
| Key | Combo |
|-----|-------|
| F1 | cr.LK > cr.LP > cr.MK xx Spiral Arrow MK |
| F2 | st.MP > st.MP > cr.MK xx Spiral Arrow HK |
| F3 | st.HP xx Cannon Spike (623+HK) |
| F4 | cr.MP > st.HP xx OD Spiral Arrow > Cannon Spike juggle |
| F5 | cr.MK xx Spin Drive Smasher (236236+HK) |

### RYU
| Key | Combo |
|-----|-------|
| F1 | cr.MK xx Hadouken |
| F2 | cr.LP > cr.LP > cr.MK xx Hashogeki |
| F3 | st.HP xx HP Shoryuken |
| F4 | cr.MP > st.HP xx OD Shoryuken > Tatsumaki juggle |
| F5 | cr.MK xx Shin Hashogeki (236236+HP) |

### ED
| Key | Combo |
|-----|-------|
| F1 | cr.LP > cr.LP > st.MP xx Psycho Blitz (hold 4→6+MK) |
| F2 | cr.MK xx Flicker > Psycho Spark (hold 4→6+HP) |
| F3 | st.HP xx Psycho Upper (hold 2→8+HP) |
| F4 | cr.MP > st.HP xx OD Psycho Upper > Psycho Blitz juggle |
| F5 | cr.MK xx Psycho Cannon Barrage (236236+HP) |

### JP
| Key | Combo |
|-----|-------|
| F1 | st.MP > st.HP xx Amnesia Surge (QCF+HP) |
| F2 | cr.LP > cr.MP xx Surge > Departure (623+HK) |
| F3 | st.HP xx Surge > Departure |
| F4 | st.MP > st.HP xx OD Amnesia Surge > Departure juggle |
| F5 | st.HP xx Interdiction (236236+HP) |

---

## Character Notes

**Juri (F1/F3):** Require a pre-stored Fuha stock. Manually press 236+LK beforehand.

**Ed:** Uses hold-charge mechanics (hold 4→6 or 2→8). The bot holds the direction long enough during the normal chain to build charge — if dropping, raise Frame Scale slightly.

**JP:** His normals have very long range from his cane. Combos here assume point-blank range for the links; at max range some links may whiff — use F1/F3 from slightly closer.

**Chun-Li (F1):** SBK needs charge. Bot holds back before executing — fire from neutral or after a backdash for best results.

---

## Controller Mapping (SF6 Classic, Xbox)

| SF6 | Xbox |
|-----|------|
| LP  | X    |
| MP  | Y    |
| HP  | RB   |
| LK  | A    |
| MK  | B    |
| HK  | RT   |

Edit the `BTN` dict in `combo_bot.py` if your mapping differs.

---

## Tuning
- **Inputs dropping?** Raise Frame Scale in the GUI (try 1.2–1.5)
- **Too slow?** Lower Frame Scale toward 0.8–0.9
- OD/Super combos require Drive/Super meter — ensure you have it first