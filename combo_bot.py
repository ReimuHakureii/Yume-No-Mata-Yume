"""
SF6 World Tour Combo Bot v3
Executes character combos via hotkeys using virtual gamepad simulation.
Characters: Akuma, Chun-Li, Mai, Ken, Juri, Cammy, Ryu, Ed, JP

Requires: vgamepad, keyboard, tkinter (built-in)
Install deps: pip install vgamepad keyboard
Also requires ViGEmBus driver: https://github.com/ViGEm/ViGEmBus/releases

HOTKEYS (F1-F5 per selected character):
  F1 = BnB #1
  F2 = BnB #2
  F3 = Punish #1
  F4 = Punish #2 (OD/meter)
  F5 = BnB into Super

  F6 = Cycle to next character
  F7 = Cycle to previous character
"""

import vgamepad as vg
import keyboard
import time
import threading
import tkinter as tk
from tkinter import ttk
import sys

# ─── Virtual Gamepad Setup ────────────────────────────────────────────────────
gamepad = None

def init_gamepad():
    global gamepad
    try:
        gamepad = vg.VX360Gamepad()
        return True
    except Exception as e:
        print(f"[ERROR] Could not init virtual gamepad: {e}")
        print("Make sure ViGEmBus driver is installed.")
        return False

# ─── Button Constants (Xbox layout) ───────────────────────────────────────────
# SF6 Default Classic mapping (Xbox controller):
# LP = X,  MP = Y,  HP = RB
# LK = A,  MK = B,  HK = RT (right trigger)
# Drive Impact = LB+RB  /  Parry = LT (left trigger)

BTN = {
    "LP": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "MP": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    "HP": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    "LK": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "MK": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "HK": None,   # RT (trigger, handled separately)
    "LT": None,   # LT (trigger, handled separately)
    "LB": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "RB": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
}

STICK_MAX = 32767
STICK_MIN = -32768

# ─── Low-level input helpers ──────────────────────────────────────────────────

FRAME_SCALE = 1.0

def f(frames):
    return frames * 0.0167 * FRAME_SCALE

def wait(ms):
    time.sleep(ms / 1000.0)

def _set_stick(direction):
    lx, ly = 0, 0
    if "6" in direction: lx = STICK_MAX
    if "4" in direction: lx = STICK_MIN
    if "8" in direction: ly = STICK_MAX
    if "2" in direction: ly = STICK_MIN
    gamepad.left_joystick(x_value=lx, y_value=ly)

def press_buttons(*buttons, duration=0.05):
    """Press one or more buttons simultaneously, then release."""
    for b in buttons:
        if b == "HK":
            gamepad.right_trigger(value=255)
        elif b == "LT":
            gamepad.left_trigger(value=255)
        elif b in BTN and BTN[b]:
            gamepad.press_button(button=BTN[b])
    gamepad.update()
    time.sleep(duration)
    for b in buttons:
        if b == "HK":
            gamepad.right_trigger(value=0)
        elif b == "LT":
            gamepad.left_trigger(value=0)
        elif b in BTN and BTN[b]:
            gamepad.release_button(button=BTN[b])
    gamepad.update()

def press_od(*buttons, duration=0.05):
    """Press OD (Overdrive/EX) version — two punches or two kicks simultaneously."""
    # buttons should be a pair like ("LP","HP") or ("LK","HK")
    press_buttons(*buttons, duration=duration)

def motion(direction, hold_frames=3):
    _set_stick(direction)
    gamepad.update()
    time.sleep(hold_frames * 0.0167 * FRAME_SCALE)

def neutral(hold_frames=1):
    gamepad.left_joystick(x_value=0, y_value=0)
    gamepad.update()
    time.sleep(hold_frames * 0.0167 * FRAME_SCALE)

def qcf(hold_frames=3):
    """Quarter circle forward 236"""
    motion("2", hold_frames)
    motion("23", hold_frames)
    motion("6", hold_frames)

def qcb(hold_frames=3):
    """Quarter circle back 214"""
    motion("2", hold_frames)
    motion("24", hold_frames)
    motion("4", hold_frames)

def dp(hold_frames=3):
    """Dragon punch 623"""
    motion("6", hold_frames)
    motion("2", hold_frames)
    motion("23", hold_frames)

def rdp(hold_frames=3):
    """Reverse dragon punch 421"""
    motion("4", hold_frames)
    motion("2", hold_frames)
    motion("24", hold_frames)

def hcf(hold_frames=3):
    """Half circle forward 41236"""
    motion("4", hold_frames)
    motion("24", hold_frames)
    motion("2", hold_frames)
    motion("23", hold_frames)
    motion("6", hold_frames)

def hcb(hold_frames=3):
    """Half circle back 63214"""
    motion("6", hold_frames)
    motion("62", hold_frames)
    motion("2", hold_frames)
    motion("24", hold_frames)
    motion("4", hold_frames)

def cr_press(*buttons, duration_frames=3):
    """Press buttons while crouching (hold 2)."""
    motion("2", 2)
    press_buttons(*buttons, duration=f(duration_frames))

def cr_cancel_into(motion_fn, *buttons):
    """Perform a crouching normal and immediately cancel into a special motion+button."""
    motion_fn()
    press_buttons(*buttons, duration=f(3))
    neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  AKUMA COMBOS
# ══════════════════════════════════════════════════════════════════════════════

def akuma_bnb_1():
    """cr.MP xx cr.MP xx HP Goshoryuken — Meterless BnB, safe cancel window."""
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(30)
    dp(2); press_buttons("HP", duration=f(3)); neutral()

def akuma_bnb_2():
    """cr.LK > cr.LP > cr.MP xx Gohadouken (QCF+HP) — Low starter BnB."""
    motion("2", 2); press_buttons("LK", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("LP", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("MP", duration=f(3))
    qcf(2); press_buttons("HP", duration=f(3)); neutral()

def akuma_punish_1():
    """st.HP xx HP Goshoryuken — Large punish window, heavy damage."""
    press_buttons("HP", duration=f(4)); wait(40)
    dp(2); press_buttons("HP", duration=f(3)); neutral()

def akuma_punish_2():
    """cr.MP > st.HP xx OD Goshoryuken > juggle HP DP — Full meter punish."""
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(40)
    dp(2); press_od("LP", "HP", duration=f(3))
    wait(200)
    dp(2); press_buttons("HP", duration=f(3)); neutral()

def akuma_bnb_super():
    """cr.MP > cr.HP xx Messatsu-Goshoryu (214214+HP) — BnB into Level 2 Super."""
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    motion("2", 2); press_buttons("HP", duration=f(4)); wait(30)
    qcb(2); qcb(2); press_buttons("HP", duration=f(3)); neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  CHUN-LI COMBOS
# ══════════════════════════════════════════════════════════════════════════════

def chunli_bnb_1():
    """cr.MK xx Spinning Bird Kick (charge 4→6+HK) — Classic charge BnB."""
    motion("4", 8)
    motion("2", 2); press_buttons("MK", duration=f(3))
    motion("6", 2); press_buttons("HK", duration=f(3)); neutral()

def chunli_bnb_2():
    """cr.LP > cr.LP > cr.MK xx Kikoken (QCF+HP) — Meterless poke BnB."""
    motion("2", 2); press_buttons("LP", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("LP", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("MK", duration=f(3)); wait(20)
    qcf(2); press_buttons("HP", duration=f(3)); neutral()

def chunli_punish_1():
    """st.MP > st.HP xx Hyakuretsukyaku (rapid HK) — Standard punish into legs."""
    press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(30)
    for _ in range(5):
        press_buttons("HK", duration=f(2)); wait(30)
    neutral()

def chunli_punish_2():
    """cr.MP > st.HP xx OD SBK > juggle HP — Full meter corner carry punish."""
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(30)
    motion("4", 6); motion("6", 2)
    press_od("MK", "HK", duration=f(3))
    wait(250); press_buttons("HP", duration=f(3)); neutral()

def chunli_bnb_super():
    """cr.MP > cr.HP xx Kikosho (236236+HP) — BnB into Level 1 Super."""
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    motion("2", 2); press_buttons("HP", duration=f(4)); wait(30)
    qcf(2); qcf(2); press_buttons("HP", duration=f(3)); neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  MAI COMBOS
# ══════════════════════════════════════════════════════════════════════════════
# Mai is a rushdown/fireball character with strong oki and fan-based specials.
# Key moves: Kachousen (QCF+P fireball), Ryuuenbu (QCB+K spin),
#            Musasabi no Mai (hold 4→6+K wall dive), Hissatsu Shinobibachi (Super)
# Note: Mai has a unique "Shiranui" Stance on HCB+K which leads to mix-ups.

def mai_bnb_1():
    """
    Mai BnB #1 — cr.LK > cr.LP > st.MP xx Kachousen (QCF+HP)
    Fast low starter into confirm. Solid damage, leaves fan on screen.
    """
    motion("2", 2); press_buttons("LK", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("LP", duration=f(2)); neutral(1); wait(40)
    press_buttons("MP", duration=f(3)); wait(30)
    qcf(2); press_buttons("HP", duration=f(3)); neutral()

def mai_bnb_2():
    """
    Mai BnB #2 — st.MP > st.HP xx Ryuuenbu (QCB+HK)
    Midrange punish and pressure combo. Ryuuenbu has great corner carry.
    """
    press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(30)
    qcb(2); press_buttons("HK", duration=f(3)); neutral()

def mai_punish_1():
    """
    Mai Punish #1 — cr.MP > st.HP xx Kachousen (QCF+HP)
    Reliable punish on large whiffs. Good damage and safe on block with fan.
    """
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(30)
    qcf(2); press_buttons("HP", duration=f(3)); neutral()

def mai_punish_2():
    """
    Mai Optimal Punish #2 — cr.MP > st.HP xx OD Ryuuenbu > juggle st.HP
    Spends Drive Meter for maximum damage and corner carry.
    OD Ryuuenbu (QCB + MK+HK) launches for juggle opportunity.
    """
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(30)
    # OD Ryuuenbu: QCB + MK+HK
    qcb(2); press_od("MK", "HK", duration=f(3))
    wait(220)
    # Juggle follow-up
    press_buttons("HP", duration=f(3)); neutral()

def mai_bnb_super():
    """
    Mai BnB into Super — cr.MP > st.HP xx Hissatsu Shinobibachi (236236+K)
    Mai's Level 1 Super. Massive damage, great combo ender from almost any starter.
    """
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(30)
    # Super: 236236+HK
    qcf(2); qcf(2); press_buttons("HK", duration=f(3)); neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  KEN COMBOS
# ══════════════════════════════════════════════════════════════════════════════
# Ken is an aggressive rushdown character. Key moves:
# Hadouken (QCF+P), Shoryuken (623+P), Tatsumaki (QCB+K),
# Jinrai Kick (236+K) — target combo chain, very important for his gameplan.
# Super: Shinryuken (236236+P) Level 1 or Shippu Jinraikyaku (236236+K) Level 3

def ken_bnb_1():
    """
    Ken BnB #1 — cr.MK xx Hadouken (QCF+HP)
    Fundamental Ken combo. Safe on block, great for neutral control.
    """
    motion("2", 2); press_buttons("MK", duration=f(3)); wait(20)
    qcf(2); press_buttons("HP", duration=f(3)); neutral()

def ken_bnb_2():
    """
    Ken BnB #2 — cr.LP > cr.LP > cr.MK xx Jinrai Kick (236+MK)
    Low starter into target combo setup. Jinrai Kick leads to follow-ups.
    """
    motion("2", 2); press_buttons("LP", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("LP", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("MK", duration=f(3)); wait(20)
    # Jinrai Kick: 236+MK
    qcf(2); press_buttons("MK", duration=f(3)); neutral()

def ken_punish_1():
    """
    Ken Punish #1 — st.MP > st.HP xx HP Shoryuken (623+HP)
    Classic Ken punish. Massive damage on big openings.
    """
    press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(35)
    dp(2); press_buttons("HP", duration=f(3)); neutral()

def ken_punish_2():
    """
    Ken Optimal Punish #2 — cr.MP > st.HP xx OD Shoryuken > juggle Tatsumaki (QCB+HK)
    Full Drive Meter spend for maximum damage. OD DP launches into juggle.
    """
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(35)
    # OD Shoryuken: 623 + LP+HP
    dp(2); press_od("LP", "HP", duration=f(3))
    wait(280)
    # Juggle: Tatsumaki Senpukyaku QCB+HK
    qcb(2); press_buttons("HK", duration=f(3)); neutral()

def ken_bnb_super():
    """
    Ken BnB into Super — cr.MK xx Shinryuken (236236+HP) — Level 1 Super
    Ken's fastest route into super. Huge damage, great cinematic ender.
    """
    motion("2", 2); press_buttons("MK", duration=f(3)); wait(20)
    # Level 1 Super Shinryuken: 236236+HP
    qcf(2); qcf(2); press_buttons("HP", duration=f(3)); neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  JURI COMBOS
# ══════════════════════════════════════════════════════════════════════════════
# Juri is a unique charge/store character. Her Fuha stocks (236+K) store fireballs,
# releasing with 236+K again. Her gameplan revolves around storing and releasing Fuha
# to power up her normals and extend combos.
# Key specials: Fuha Store/Release (236+K), Saihasho (QCF+LP release),
#               Shiku-sen (236+K dive kick), Feng Shui Engine Super (214214+K)
# NOTE: These combos assume Juri has at least 1 Fuha stock stored before use
#       where indicated. Store a stock first with 236+LK before starting.

def juri_bnb_1():
    """
    Juri BnB #1 — cr.MK > st.HP xx Saihasho (QCF+LP Fuha release)
    Solid meterless BnB assuming 1 Fuha stock is pre-stored.
    If no stock, ends after st.HP for less damage.
    """
    motion("2", 2); press_buttons("MK", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(30)
    # Fuha release: QCF + LP
    qcf(2); press_buttons("LP", duration=f(3)); neutral()

def juri_bnb_2():
    """
    Juri BnB #2 — cr.LP > cr.LP > cr.MK xx Shiku-sen (236+MK dive kick)
    Low starter BnB. Shiku-sen is a fast angled kick that combos from cr.MK.
    """
    motion("2", 2); press_buttons("LP", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("LP", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("MK", duration=f(3)); wait(25)
    # Shiku-sen: 236+MK
    qcf(2); press_buttons("MK", duration=f(3)); neutral()

def juri_punish_1():
    """
    Juri Punish #1 — st.HP xx Saihasho (QCF+HP Fuha release)
    Simple high-damage punish. HP version of Fuha release travels full screen.
    Requires 1 stored Fuha stock.
    """
    press_buttons("HP", duration=f(4)); wait(30)
    qcf(2); press_buttons("HP", duration=f(3)); neutral()

def juri_punish_2():
    """
    Juri Optimal Punish #2 — cr.MP > st.HP xx OD Shiku-sen > cr.HP > Fuha release
    Full meter punish with Fuha extension. OD Shiku-sen (236+MK+HK) launches.
    Requires Drive Meter + 1 Fuha stock for ender.
    """
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(30)
    # OD Shiku-sen: 236 + MK+HK
    qcf(2); press_od("MK", "HK", duration=f(3))
    wait(200)
    # Juggle: cr.HP
    motion("2", 2); press_buttons("HP", duration=f(4)); neutral(2); wait(50)
    # Fuha release ender: QCF+LP
    qcf(2); press_buttons("LP", duration=f(3)); neutral()

def juri_bnb_super():
    """
    Juri BnB into Super — cr.MK > st.HP xx Feng Shui Engine (214214+LK)
    Juri's Level 1 Super activates Feng Shui Engine for powered-up state.
    Combo into it for guaranteed activation and pressure setup.
    """
    motion("2", 2); press_buttons("MK", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(30)
    # Feng Shui Engine: 214214+LK
    qcb(2); qcb(2); press_buttons("LK", duration=f(3)); neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  CAMMY COMBOS
# ══════════════════════════════════════════════════════════════════════════════
# Cammy is a fast, rushdown/mixup character with strong pressure and oki.
# Key specials: Spiral Arrow (QCF+K — dive kick), Cannon Spike (623+K — DP),
#               Hooligan Combination (QCB+P), Quick Spin Knuckle (236+P).
# Super: Cammy Spin Drive Smasher (236236+K) Lv1, Delta Red Assault (236236+P) Lv2
# Her combos revolve around cr.MK xx Spiral Arrow as the core cancel route.

def cammy_bnb_1():
    """
    Cammy BnB #1 — cr.LK > cr.LP > cr.MK xx Spiral Arrow (QCF+MK)
    Fast low starter into her signature slide. Safe on block at range.
    """
    motion("2", 2); press_buttons("LK", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("LP", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("MK", duration=f(3)); wait(20)
    qcf(2); press_buttons("MK", duration=f(3)); neutral()

def cammy_bnb_2():
    """
    Cammy BnB #2 — st.MP > st.MP > cr.MK xx Spiral Arrow (QCF+HK)
    Target combo chain into HK Spiral Arrow. Great damage meterless.
    st.MP > st.MP is a target combo (auto-chain on the second hit).
    """
    press_buttons("MP", duration=f(3)); neutral(1); wait(35)
    press_buttons("MP", duration=f(3)); neutral(2); wait(40)
    motion("2", 2); press_buttons("MK", duration=f(3)); wait(20)
    qcf(2); press_buttons("HK", duration=f(3)); neutral()

def cammy_punish_1():
    """
    Cammy Punish #1 — st.HP xx Cannon Spike (623+HK)
    Bread-and-butter punish on large openings. Cannon Spike is a hard knockdown.
    """
    press_buttons("HP", duration=f(4)); wait(35)
    dp(2); press_buttons("HK", duration=f(3)); neutral()

def cammy_punish_2():
    """
    Cammy Optimal Punish #2 — cr.MP > st.HP xx OD Spiral Arrow > Cannon Spike juggle
    OD Spiral Arrow (QCF+MK+HK) launches for a juggle Cannon Spike follow-up.
    Spends one bar of Drive Meter. Maximum meterless-into-OD damage.
    """
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(35)
    # OD Spiral Arrow: QCF + MK+HK
    qcf(2); press_od("MK", "HK", duration=f(3))
    wait(220)
    # Juggle: Cannon Spike 623+HK
    dp(2); press_buttons("HK", duration=f(3)); neutral()

def cammy_bnb_super():
    """
    Cammy BnB into Super — cr.MK xx Spin Drive Smasher (236236+HK) Lv1
    Fast route into her Level 1 Super. Massive damage, cinematic finisher.
    """
    motion("2", 2); press_buttons("MK", duration=f(3)); wait(20)
    qcf(2); qcf(2); press_buttons("HK", duration=f(3)); neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  RYU COMBOS
# ══════════════════════════════════════════════════════════════════════════════
# Ryu is the quintessential SF character — balanced, fundamental-based.
# Key specials: Hadouken (QCF+P), Shoryuken (623+P), Tatsumaki (QCB+K),
#               Hashogeki (236+P — palm strike, chargeable), Denjin Charge (hold HP+HK).
# Super: Shin Hashogeki (236236+P) Lv1, Shin Shoryuken (236236+P Lv3)
# Ryu's combos are clean and punish-focused. Shoryuken is his best ender.

def ryu_bnb_1():
    """
    Ryu BnB #1 — cr.MK xx Hadouken (QCF+HP)
    The most fundamental SF combo ever. Safe fireball cancel from a poke.
    """
    motion("2", 2); press_buttons("MK", duration=f(3)); wait(20)
    qcf(2); press_buttons("HP", duration=f(3)); neutral()

def ryu_bnb_2():
    """
    Ryu BnB #2 — cr.LP > cr.LP > cr.MK xx Hashogeki (236+HP palm)
    Low starter into Hashogeki palm strike. More plus-on-hit than Hadouken.
    """
    motion("2", 2); press_buttons("LP", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("LP", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("MK", duration=f(3)); wait(20)
    # Hashogeki: 236+HP
    qcf(2); press_buttons("HP", duration=f(3)); neutral()

def ryu_punish_1():
    """
    Ryu Punish #1 — st.HP xx HP Shoryuken (623+HP)
    Classic big punish. st.HP into Shoryuken is Ryu's best meterless damage.
    """
    press_buttons("HP", duration=f(4)); wait(35)
    dp(2); press_buttons("HP", duration=f(3)); neutral()

def ryu_punish_2():
    """
    Ryu Optimal Punish #2 — cr.MP > st.HP xx OD Shoryuken > juggle Tatsumaki (QCB+HK)
    OD Shoryuken (623+LP+HP) launches. Tatsumaki juggle adds solid damage.
    Costs one Drive bar. Best damage punish in his kit.
    """
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(35)
    # OD Shoryuken: 623 + LP+HP
    dp(2); press_od("LP", "HP", duration=f(3))
    wait(270)
    # Juggle: Tatsumaki QCB+HK
    qcb(2); press_buttons("HK", duration=f(3)); neutral()

def ryu_bnb_super():
    """
    Ryu BnB into Super — cr.MK xx Shin Hashogeki (236236+HP) Lv1
    Ryu's fastest super route. Level 1 Shin Hashogeki is a full-screen palm blast.
    """
    motion("2", 2); press_buttons("MK", duration=f(3)); wait(20)
    qcf(2); qcf(2); press_buttons("HP", duration=f(3)); neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  ED COMBOS
# ══════════════════════════════════════════════════════════════════════════════
# Ed is a Psycho Power rushdown character with unique motion inputs —
# most of his specials use *hold-then-release* or charge mechanics rather
# than traditional QCF/DP motions, making him one of the easiest characters
# to execute optimally.
# Key specials:
#   Psycho Spark     — hold back, forward + P  (projectile)
#   Psycho Blitz     — hold back, forward + K  (rush punch)
#   Psycho Upper     — hold down, up + P       (uppercut / anti-air)
#   Flicker          — 236 + P                 (quick jab series)
# Super: Psycho Cannon Barrage (236236+P) Lv1, Psycho Seize (hold then release)
# NOTE: Ed's charge inputs are simplified here using hold-motion sequences.

def ed_bnb_1():
    """
    Ed BnB #1 — cr.LP > cr.LP > st.MP xx Psycho Blitz (hold 4→6+MK)
    Easy low starter. Psycho Blitz is his main cancel target. Charge held during normals.
    """
    # Build charge during the normals (hold back)
    motion("4", 2)
    motion("24", 1); press_buttons("LP", duration=f(2)); wait(35)
    motion("24", 1); press_buttons("LP", duration=f(2)); wait(35)
    # st.MP (release back briefly, re-engage charge during recovery)
    motion("4", 3); press_buttons("MP", duration=f(3)); wait(25)
    # Psycho Blitz: hold 4 → 6 + MK
    motion("4", 4); motion("6", 2); press_buttons("MK", duration=f(3)); neutral()

def ed_bnb_2():
    """
    Ed BnB #2 — cr.MK xx Flicker (236+LP) > Psycho Spark (hold 4→6+HP)
    Flicker chains into Spark for a double-cancel combo. Decent corner carry.
    """
    motion("2", 2); press_buttons("MK", duration=f(3)); wait(20)
    # Flicker: 236+LP
    qcf(2); press_buttons("LP", duration=f(3))
    wait(80)
    # Psycho Spark: hold 4 → 6 + HP
    motion("4", 5); motion("6", 2); press_buttons("HP", duration=f(3)); neutral()

def ed_punish_1():
    """
    Ed Punish #1 — st.HP xx Psycho Upper (hold 2→8+HP)
    Straightforward punish. Psycho Upper is Ed's DP equivalent — great damage.
    """
    press_buttons("HP", duration=f(4)); wait(35)
    # Psycho Upper: hold 2 → 8 + HP
    motion("2", 6); motion("8", 2); press_buttons("HP", duration=f(3)); neutral()

def ed_punish_2():
    """
    Ed Optimal Punish #2 — cr.MP > st.HP xx OD Psycho Upper > juggle Psycho Blitz
    OD Psycho Upper (hold 2→8 + LP+HP) launches for a juggle follow-up.
    Costs one Drive bar. Ed's highest damage punish route.
    """
    motion("2", 2); press_buttons("MP", duration=f(3)); neutral(2); wait(50)
    press_buttons("HP", duration=f(4)); wait(35)
    # OD Psycho Upper: hold 2 → 8 + LP+HP
    motion("2", 6); motion("8", 2); press_od("LP", "HP", duration=f(3))
    wait(240)
    # Juggle: Psycho Blitz hold 4→6+HK
    motion("4", 4); motion("6", 2); press_buttons("HK", duration=f(3)); neutral()

def ed_bnb_super():
    """
    Ed BnB into Super — cr.MK xx Psycho Cannon Barrage (236236+HP) Lv1
    Ed's Level 1 Super. Massive Psycho Power beam, great combo ender damage.
    """
    motion("2", 2); press_buttons("MK", duration=f(3)); wait(20)
    qcf(2); qcf(2); press_buttons("HP", duration=f(3)); neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  JP COMBOS
# ══════════════════════════════════════════════════════════════════════════════
# JP (Judgment Day) is a zoner/puppet character with unique long-range tools.
# He can summon Amnesia (a puppet) to create screen presence and extend combos.
# Key specials:
#   Amnesia Surge    — QCF+P  (summon/detonate Amnesia at distance)
#   Amnesia Trap     — QCB+P  (place Amnesia trap on screen)
#   Departure        — 623+K  (DP-like teleport kick)
#   Consume          — 214+K  (command grab at close range)
# Super: Interdiction (236236+P) Lv1 — full-screen purple explosion
# JP's normals hit at long range (his cane extends reach significantly).
# Combos are simpler than other chars but very damaging due to his power level.

def jp_bnb_1():
    """
    JP BnB #1 — st.MP > st.HP xx Amnesia Surge (QCF+HP)
    Core JP combo. Long-range poke chain into his signature purple orb.
    st.MP > st.HP is a natural chain on hit.
    """
    press_buttons("MP", duration=f(3)); neutral(2); wait(45)
    press_buttons("HP", duration=f(4)); wait(30)
    qcf(2); press_buttons("HP", duration=f(3)); neutral()

def jp_bnb_2():
    """
    JP BnB #2 — cr.LP > cr.MP xx Amnesia Surge (QCF+MP) > Departure (623+HK)
    Low-poke confirm into double special. Departure (623+HK) adds juggle damage.
    """
    motion("2", 2); press_buttons("LP", duration=f(2)); neutral(1); wait(40)
    motion("2", 2); press_buttons("MP", duration=f(3)); wait(25)
    # Amnesia Surge: QCF+MP
    qcf(2); press_buttons("MP", duration=f(3))
    wait(150)
    # Departure: 623+HK
    dp(2); press_buttons("HK", duration=f(3)); neutral()

def jp_punish_1():
    """
    JP Punish #1 — st.HP xx Amnesia Surge (QCF+HP) > Departure (623+MK)
    JP's best meterless punish. Two-special cancel for big damage and corner push.
    """
    press_buttons("HP", duration=f(4)); wait(30)
    qcf(2); press_buttons("HP", duration=f(3))
    wait(120)
    dp(2); press_buttons("MK", duration=f(3)); neutral()

def jp_punish_2():
    """
    JP Optimal Punish #2 — st.MP > st.HP xx OD Amnesia Surge > juggle Departure (623+HK)
    OD Surge (QCF+LP+HP) detonates on-screen Amnesia for massive juggle damage.
    Costs one Drive bar. JP's highest punish damage route.
    """
    press_buttons("MP", duration=f(3)); neutral(2); wait(45)
    press_buttons("HP", duration=f(4)); wait(30)
    # OD Amnesia Surge: QCF + LP+HP
    qcf(2); press_od("LP", "HP", duration=f(3))
    wait(230)
    # Juggle: Departure 623+HK
    dp(2); press_buttons("HK", duration=f(3)); neutral()

def jp_bnb_super():
    """
    JP BnB into Super — st.HP xx Interdiction (236236+HP) Lv1
    JP's full-screen Level 1 Super. Enormous damage, screen-filling purple chaos.
    Works from almost any range thanks to JP's long-range st.HP.
    """
    press_buttons("HP", duration=f(4)); wait(30)
    qcf(2); qcf(2); press_buttons("HP", duration=f(3)); neutral()


# ─── Combo Registry ────────────────────────────────────────────────────────────

ALL_COMBOS = {
    "Akuma": [
        {"fn": akuma_bnb_1,    "label": "BnB #1 — cr.MP xx cr.MP xx HP Goshoryuken",     "slot": "F1"},
        {"fn": akuma_bnb_2,    "label": "BnB #2 — cr.LK > cr.LP > cr.MP xx Gohadouken",  "slot": "F2"},
        {"fn": akuma_punish_1, "label": "Punish #1 — st.HP xx HP Goshoryuken",            "slot": "F3"},
        {"fn": akuma_punish_2, "label": "Punish #2 — OD Goshoryuken juggle",              "slot": "F4"},
        {"fn": akuma_bnb_super,"label": "Super — cr.MP > cr.HP xx Messatsu-Goshoryu",     "slot": "F5"},
    ],
    "Chun-Li": [
        {"fn": chunli_bnb_1,    "label": "BnB #1 — cr.MK xx Spinning Bird Kick",           "slot": "F1"},
        {"fn": chunli_bnb_2,    "label": "BnB #2 — cr.LP > cr.LP > cr.MK xx Kikoken",      "slot": "F2"},
        {"fn": chunli_punish_1, "label": "Punish #1 — st.MP > st.HP xx Hyakuretsukyaku",   "slot": "F3"},
        {"fn": chunli_punish_2, "label": "Punish #2 — OD SBK juggle",                       "slot": "F4"},
        {"fn": chunli_bnb_super,"label": "Super — cr.MP > cr.HP xx Kikosho",                "slot": "F5"},
    ],
    "Mai": [
        {"fn": mai_bnb_1,    "label": "BnB #1 — cr.LK > cr.LP > st.MP xx Kachousen",     "slot": "F1"},
        {"fn": mai_bnb_2,    "label": "BnB #2 — st.MP > st.HP xx Ryuuenbu",               "slot": "F2"},
        {"fn": mai_punish_1, "label": "Punish #1 — cr.MP > st.HP xx Kachousen",           "slot": "F3"},
        {"fn": mai_punish_2, "label": "Punish #2 — OD Ryuuenbu juggle",                   "slot": "F4"},
        {"fn": mai_bnb_super,"label": "Super — cr.MP > st.HP xx Hissatsu Shinobibachi",   "slot": "F5"},
    ],
    "Ken": [
        {"fn": ken_bnb_1,    "label": "BnB #1 — cr.MK xx Hadouken",                       "slot": "F1"},
        {"fn": ken_bnb_2,    "label": "BnB #2 — cr.LP > cr.LP > cr.MK xx Jinrai Kick",    "slot": "F2"},
        {"fn": ken_punish_1, "label": "Punish #1 — st.MP > st.HP xx HP Shoryuken",        "slot": "F3"},
        {"fn": ken_punish_2, "label": "Punish #2 — OD Shoryuken > Tatsumaki juggle",      "slot": "F4"},
        {"fn": ken_bnb_super,"label": "Super — cr.MK xx Shinryuken",                      "slot": "F5"},
    ],
    "Juri": [
        {"fn": juri_bnb_1,    "label": "BnB #1 — cr.MK > st.HP xx Fuha Release (needs stock)", "slot": "F1"},
        {"fn": juri_bnb_2,    "label": "BnB #2 — cr.LP > cr.LP > cr.MK xx Shiku-sen",          "slot": "F2"},
        {"fn": juri_punish_1, "label": "Punish #1 — st.HP xx Fuha Release HP (needs stock)",    "slot": "F3"},
        {"fn": juri_punish_2, "label": "Punish #2 — OD Shiku-sen > cr.HP > Fuha Release",      "slot": "F4"},
        {"fn": juri_bnb_super,"label": "Super — cr.MK > st.HP xx Feng Shui Engine",            "slot": "F5"},
    ],
    "Cammy": [
        {"fn": cammy_bnb_1,    "label": "BnB #1 — cr.LK > cr.LP > cr.MK xx Spiral Arrow",       "slot": "F1"},
        {"fn": cammy_bnb_2,    "label": "BnB #2 — st.MP > st.MP > cr.MK xx Spiral Arrow HK",    "slot": "F2"},
        {"fn": cammy_punish_1, "label": "Punish #1 — st.HP xx Cannon Spike",                     "slot": "F3"},
        {"fn": cammy_punish_2, "label": "Punish #2 — OD Spiral Arrow > Cannon Spike juggle",     "slot": "F4"},
        {"fn": cammy_bnb_super,"label": "Super — cr.MK xx Spin Drive Smasher",                   "slot": "F5"},
    ],
    "Ryu": [
        {"fn": ryu_bnb_1,    "label": "BnB #1 — cr.MK xx Hadouken",                             "slot": "F1"},
        {"fn": ryu_bnb_2,    "label": "BnB #2 — cr.LP > cr.LP > cr.MK xx Hashogeki",            "slot": "F2"},
        {"fn": ryu_punish_1, "label": "Punish #1 — st.HP xx HP Shoryuken",                      "slot": "F3"},
        {"fn": ryu_punish_2, "label": "Punish #2 — OD Shoryuken > Tatsumaki juggle",            "slot": "F4"},
        {"fn": ryu_bnb_super,"label": "Super — cr.MK xx Shin Hashogeki",                        "slot": "F5"},
    ],
    "Ed": [
        {"fn": ed_bnb_1,    "label": "BnB #1 — cr.LP > cr.LP > st.MP xx Psycho Blitz",         "slot": "F1"},
        {"fn": ed_bnb_2,    "label": "BnB #2 — cr.MK xx Flicker > Psycho Spark",               "slot": "F2"},
        {"fn": ed_punish_1, "label": "Punish #1 — st.HP xx Psycho Upper",                       "slot": "F3"},
        {"fn": ed_punish_2, "label": "Punish #2 — OD Psycho Upper > Psycho Blitz juggle",      "slot": "F4"},
        {"fn": ed_bnb_super,"label": "Super — cr.MK xx Psycho Cannon Barrage",                  "slot": "F5"},
    ],
    "JP": [
        {"fn": jp_bnb_1,    "label": "BnB #1 — st.MP > st.HP xx Amnesia Surge",                "slot": "F1"},
        {"fn": jp_bnb_2,    "label": "BnB #2 — cr.LP > cr.MP xx Surge > Departure",            "slot": "F2"},
        {"fn": jp_punish_1, "label": "Punish #1 — st.HP xx Surge > Departure",                 "slot": "F3"},
        {"fn": jp_punish_2, "label": "Punish #2 — OD Amnesia Surge > Departure juggle",        "slot": "F4"},
        {"fn": jp_bnb_super,"label": "Super — st.HP xx Interdiction",                           "slot": "F5"},
    ],
}

CHARACTER_ORDER = list(ALL_COMBOS.keys())

# ─── State ────────────────────────────────────────────────────────────────────

current_char_index = 0
combo_lock = threading.Lock()
executing = False
log_callback = None
char_change_callback = None

def get_current_char():
    return CHARACTER_ORDER[current_char_index]

def execute_combo(combo_info):
    global executing
    if executing:
        return
    with combo_lock:
        executing = True
        char = get_current_char()
        name = combo_info["label"]
        if log_callback:
            log_callback(f"▶ [{char}] {name}")
        try:
            combo_info["fn"]()
            if log_callback:
                log_callback(f"✓ Done")
        except Exception as e:
            if log_callback:
                log_callback(f"✗ Error: {e}")
        finally:
            executing = False

def fire_slot(slot_index):
    char = get_current_char()
    combos = ALL_COMBOS[char]
    if slot_index < len(combos):
        threading.Thread(target=execute_combo, args=(combos[slot_index],), daemon=True).start()

def cycle_character(direction=1):
    global current_char_index
    current_char_index = (current_char_index + direction) % len(CHARACTER_ORDER)
    char = get_current_char()
    if log_callback:
        log_callback(f"◈ Character switched to: {char}")
    if char_change_callback:
        char_change_callback(char)

def register_hotkeys():
    # F1-F5: fire combo slots 0-4 for current character
    for i, key in enumerate(["F1","F2","F3","F4","F5"]):
        keyboard.add_hotkey(key, lambda idx=i: fire_slot(idx))
    # F6: next character, F7: previous character
    keyboard.add_hotkey("F6", lambda: cycle_character(+1))
    keyboard.add_hotkey("F7", lambda: cycle_character(-1))


# ─── GUI ──────────────────────────────────────────────────────────────────────

CHAR_COLORS = {
    "Akuma":   "#8b2be2",
    "Chun-Li": "#4fc3f7",
    "Mai":     "#ff6b35",
    "Ken":     "#ffcc02",
    "Juri":    "#e040fb",
    "Cammy":   "#00e5a0",
    "Ryu":     "#e8251a",
    "Ed":      "#3a9bdc",
    "JP":      "#c8a850",
}

class ComboApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SF6 World Tour Combo Bot")
        self.configure(bg="#09090f")
        self.resizable(False, False)
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self, bg="#09090f")
        header.pack(fill="x", padx=20, pady=(16, 0))
        tk.Label(header, text="SF6", font=("Impact", 38, "bold"),
                 bg="#09090f", fg="#e8251a").pack(side="left")
        tk.Label(header, text=" COMBO BOT", font=("Impact", 38),
                 bg="#09090f", fg="#f0f0f0").pack(side="left")
        tk.Label(self, text="World Tour Edition  ·  Classic Controls  ·  v3.0",
                 font=("Consolas", 9), bg="#09090f", fg="#444").pack(anchor="w", padx=22)

        # ── Status ──
        self.status_var = tk.StringVar(value="● Initializing...")
        tk.Label(self, textvariable=self.status_var,
                 font=("Consolas", 10), bg="#111118", fg="#e8251a",
                 anchor="w", padx=10, pady=5).pack(fill="x", padx=20, pady=(10, 0))

        # ── Red divider ──
        tk.Frame(self, bg="#e8251a", height=2).pack(fill="x", padx=20, pady=8)

        # ── Character selector tabs (two rows for 9 chars) ──
        tab_outer = tk.Frame(self, bg="#09090f")
        tab_outer.pack(fill="x", padx=20, pady=(0, 6))

        tk.Label(tab_outer, text="CHARACTER:", font=("Consolas", 9, "bold"),
                 bg="#09090f", fg="#555").pack(anchor="w", pady=(0, 3))

        ROW_SIZE = 5
        self.char_buttons = {}
        for row_idx in range(0, len(CHARACTER_ORDER), ROW_SIZE):
            row_frame = tk.Frame(tab_outer, bg="#09090f")
            row_frame.pack(fill="x", pady=1)
            for char in CHARACTER_ORDER[row_idx:row_idx + ROW_SIZE]:
                color = CHAR_COLORS[char]
                btn = tk.Button(row_frame, text=char,
                                font=("Consolas", 10, "bold"),
                                bg="#1a1a28", fg="#888",
                                activebackground=color, activeforeground="#000",
                                relief="flat", padx=10, pady=4, cursor="hand2",
                                command=lambda c=char: self._select_char(c))
                btn.pack(side="left", padx=2)
                self.char_buttons[char] = btn

        tk.Label(tab_outer, text="F6 = Next character   F7 = Previous character",
                 font=("Consolas", 9), bg="#09090f", fg="#333").pack(anchor="w", pady=(3, 0))

        # ── Active character label ──
        self.active_char_var = tk.StringVar(value="")
        self.char_label = tk.Label(self, textvariable=self.active_char_var,
                                   font=("Impact", 20), bg="#09090f", fg="#e8251a",
                                   anchor="w", padx=22)
        self.char_label.pack(fill="x")

        # ── Combo table ──
        tree_frame = tk.Frame(self, bg="#09090f")
        tree_frame.pack(fill="both", padx=20, pady=(4, 0))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("SF6.Treeview",
            background="#111118", foreground="#c0c0c0",
            fieldbackground="#111118", font=("Consolas", 10), rowheight=28)
        style.configure("SF6.Treeview.Heading",
            background="#16162a", foreground="#e8251a",
            font=("Consolas", 10, "bold"), relief="flat")
        style.map("SF6.Treeview", background=[("selected", "#2a1a2e")])

        cols = ("slot", "type", "combo")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  style="SF6.Treeview", height=5)
        self.tree.heading("slot",  text="KEY")
        self.tree.heading("type",  text="TYPE")
        self.tree.heading("combo", text="COMBO ROUTE")
        self.tree.column("slot",  width=55,  anchor="center")
        self.tree.column("type",  width=100, anchor="center")
        self.tree.column("combo", width=450, anchor="w")
        self.tree.pack(fill="both")

        # ── Separator ──
        tk.Frame(self, bg="#222", height=1).pack(fill="x", padx=20, pady=8)

        # ── Settings row ──
        settings = tk.Frame(self, bg="#09090f")
        settings.pack(fill="x", padx=20, pady=(0, 8))

        tk.Label(settings, text="Frame Scale:", font=("Consolas", 10),
                 bg="#09090f", fg="#666").pack(side="left")
        self.scale_var = tk.DoubleVar(value=FRAME_SCALE)
        tk.Spinbox(settings, from_=0.5, to=3.0, increment=0.1,
                   textvariable=self.scale_var, width=5,
                   font=("Consolas", 10), bg="#1a1a2e", fg="#f0f0f0",
                   buttonbackground="#333", relief="flat",
                   command=self._update_scale).pack(side="left", padx=(6, 16))
        tk.Label(settings, text="↑ Raise if inputs drop on slow CPUs",
                 font=("Consolas", 9), bg="#09090f", fg="#333").pack(side="left")

        # ── Log ──
        log_frame = tk.Frame(self, bg="#09090f")
        log_frame.pack(fill="x", padx=20, pady=(0, 16))
        tk.Label(log_frame, text="LOG", font=("Consolas", 9, "bold"),
                 bg="#09090f", fg="#e8251a").pack(anchor="w")
        self.log_text = tk.Text(log_frame, height=5, bg="#060610", fg="#00ff88",
                                font=("Consolas", 9), relief="flat",
                                state="disabled", cursor="arrow")
        self.log_text.pack(fill="x")

        # Init display
        self._select_char(CHARACTER_ORDER[0])
        self._log("Bot ready. F1-F5: combos | F6/F7: switch character")
        self._log("Tip: Raise Frame Scale if combos drop inputs on your PC.")

    def _select_char(self, char):
        global current_char_index
        current_char_index = CHARACTER_ORDER.index(char)
        color = CHAR_COLORS[char]

        # Update button highlights
        for c, btn in self.char_buttons.items():
            if c == char:
                btn.configure(bg=color, fg="#000")
            else:
                btn.configure(bg="#1a1a28", fg="#888")

        self.char_label.configure(text=f"▸ {char.upper()}", fg=color)

        # Rebuild combo table
        for row in self.tree.get_children():
            self.tree.delete(row)

        type_labels = ["BnB", "BnB", "Punish", "Punish (OD)", "Super"]
        for i, combo in enumerate(ALL_COMBOS[char]):
            tag = "odd" if i % 2 else "even"
            self.tree.insert("", "end",
                             values=(combo["slot"], type_labels[i], combo["label"]),
                             tags=(tag,))

        self.tree.tag_configure("odd",  background="#0e0e1c")
        self.tree.tag_configure("even", background="#111118")

    def _update_scale(self):
        global FRAME_SCALE
        FRAME_SCALE = self.scale_var.get()
        self._log(f"Frame scale → {FRAME_SCALE:.1f}x")

    def _log(self, msg):
        def _do():
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.after(0, _do)

    def set_status(self, msg):
        self.after(0, lambda: self.status_var.set(f"● {msg}"))

    def _on_close(self):
        keyboard.unhook_all()
        self.destroy()
        sys.exit(0)


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    app = ComboApp()

    global log_callback, char_change_callback
    log_callback = app._log
    char_change_callback = lambda char: app.after(0, lambda: app._select_char(char))

    if init_gamepad():
        app.set_status("Gamepad OK — F1-F5: Combos | F6/F7: Switch Character | 9 Characters loaded")
        app._log("✓ Virtual Xbox 360 gamepad created.")
        app._log("✓ Hotkeys: F1-F5 (combos), F6 (next char), F7 (prev char)")
        register_hotkeys()
    else:
        app.set_status("ERROR: ViGEmBus not found — install driver first")
        app._log("✗ Gamepad init failed. Install ViGEmBus:")
        app._log("  https://github.com/ViGEm/ViGEmBus/releases")

    app.mainloop()


if __name__ == "__main__":
    main()
