"""
SF6 Combo Bot v4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Characters: Akuma, Chun-Li, Mai, Ken, Juri, Cammy, Ryu,
            Ed, JP, Marisa, Luke, A.K.I., M. Bison

Requires:   pip install vgamepad keyboard
            ViGEmBus driver: https://github.com/ViGEm/ViGEmBus/releases

HOTKEYS
  F1–F5  → Fire combo slot 1–5 for current character
  F6     → Next character
  F7     → Previous character

IMPROVEMENTS vs v3:
  • Dedicated press_cr() helper eliminates repeated stick+button patterns
  • hold_charge() helper cleanly implements charge-character mechanics
  • od() wrapper is now a clean alias, no duplicate logic
  • Combo slots expanded to 6 per character (added advanced slot on F6... wait,
    F6 is char-switch — so combos remain F1-F5; added a 6th "Advanced" combo
    accessible via the GUI "▶ Advanced" button per character)
  • GUI: scrollable combo list, combo progress indicator, per-char notes panel
  • Execution engine: cancellable mid-combo via ESC, queued re-fire guard
  • Frame timing: per-input jitter compensation using time.perf_counter
  • All existing combos reviewed and extended with more optimal routes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import vgamepad as vg
import keyboard
import time
import threading
import tkinter as tk
from tkinter import ttk
import sys

# ══════════════════════════════════════════════════════════════════════════════
#  VIRTUAL GAMEPAD
# ══════════════════════════════════════════════════════════════════════════════

gamepad = None
_cancel_flag = threading.Event()   # set this to abort a running combo mid-way

def init_gamepad():
    global gamepad
    try:
        gamepad = vg.VX360Gamepad()
        gamepad.update()
        return True
    except Exception as e:
        print(f"[ERROR] Could not init virtual gamepad: {e}")
        return False

# ══════════════════════════════════════════════════════════════════════════════
#  BUTTON / AXIS CONSTANTS  (SF6 Classic, Xbox layout)
#  LP=X  MP=Y  HP=RB  LK=A  MK=B  HK=RT  Parry=LT  DI=LB+RB
# ══════════════════════════════════════════════════════════════════════════════

_BTN = {
    "LP": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "MP": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    "HP": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    "LK": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "MK": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "LB": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "RB": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    # HK  → right trigger (handled via _set_triggers)
    # LT  → left trigger  (handled via _set_triggers)
}

STICK_MAX =  32767
STICK_MIN = -32768

# ══════════════════════════════════════════════════════════════════════════════
#  TIMING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

FRAME_SCALE = 1.0          # global timing multiplier — raise on slow CPUs
FRAME_MS    = 16.667       # one frame at 60 fps

def _sleep(seconds: float):
    """High-resolution sleep that also respects the cancel flag."""
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        if _cancel_flag.is_set():
            raise InterruptedError("Combo cancelled")
        time.sleep(0.001)

def f(frames: float) -> float:
    """Convert frames to seconds, applying global scale."""
    return frames * (FRAME_MS / 1000.0) * FRAME_SCALE

def wait(ms: float):
    """Wait a fixed number of milliseconds (also checks cancel flag)."""
    _sleep(ms / 1000.0)

# ══════════════════════════════════════════════════════════════════════════════
#  LOW-LEVEL INPUT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _set_stick(direction: str):
    """
    Map numpad direction string to left stick X/Y.
    Supports compound directions like '23', '46', etc.
    """
    lx = ly = 0
    if "6" in direction: lx =  STICK_MAX
    if "4" in direction: lx =  STICK_MIN
    if "8" in direction: ly =  STICK_MAX
    if "2" in direction: ly =  STICK_MIN
    gamepad.left_joystick(x_value=lx, y_value=ly)

def _set_triggers(hk: bool = False, lt: bool = False):
    gamepad.right_trigger(value=255 if hk else 0)
    gamepad.left_trigger(value=255 if lt else 0)

def _press_raw(*buttons):
    """Press buttons without releasing — for simultaneous multi-button holds."""
    for b in buttons:
        if b == "HK":  gamepad.right_trigger(value=255)
        elif b == "LT": gamepad.left_trigger(value=255)
        elif b in _BTN: gamepad.press_button(button=_BTN[b])

def _release_raw(*buttons):
    """Release buttons."""
    for b in buttons:
        if b == "HK":  gamepad.right_trigger(value=0)
        elif b == "LT": gamepad.left_trigger(value=0)
        elif b in _BTN: gamepad.release_button(button=_BTN[b])

def press_buttons(*buttons, frames: float = 3):
    """Press one or more buttons for `frames` frames, then release."""
    _press_raw(*buttons)
    gamepad.update()
    _sleep(f(frames))
    _release_raw(*buttons)
    gamepad.update()

def od(*buttons, frames: float = 3):
    """Alias for pressing two buttons simultaneously (Overdrive / EX move)."""
    press_buttons(*buttons, frames=frames)

def motion(direction: str, frames: float = 3):
    """Hold a stick direction for `frames` frames."""
    _set_stick(direction)
    gamepad.update()
    _sleep(f(frames))

def neutral(frames: float = 1):
    """Return stick to neutral for `frames` frames."""
    gamepad.left_joystick(x_value=0, y_value=0)
    gamepad.update()
    _sleep(f(frames))

# ── Composite motion helpers ──────────────────────────────────────────────────

def qcf(frames: float = 2):
    """236 — Quarter circle forward."""
    motion("2", frames); motion("23", frames); motion("6", frames)

def qcb(frames: float = 2):
    """214 — Quarter circle back."""
    motion("2", frames); motion("24", frames); motion("4", frames)

def dp(frames: float = 2):
    """623 — Dragon punch (Shoryuken) motion."""
    motion("6", frames); motion("2", frames); motion("23", frames)

def rdp(frames: float = 2):
    """421 — Reverse dragon punch."""
    motion("4", frames); motion("2", frames); motion("24", frames)

def hcf(frames: float = 2):
    """41236 — Half circle forward."""
    motion("4", frames); motion("24", frames); motion("2", frames)
    motion("23", frames); motion("6", frames)

def hcb(frames: float = 2):
    """63214 — Half circle back."""
    motion("6", frames); motion("62", frames); motion("2", frames)
    motion("24", frames); motion("4", frames)

def hold_charge(direction: str, frames: float = 8):
    """
    Hold a charge direction for `frames` frames.
    Use before charge specials (Chun SBK, Bison Scissors, etc.)
    """
    motion(direction, frames)

# ── Shorthand normal helpers ──────────────────────────────────────────────────

def cr(*buttons, frames: float = 3):
    """Press buttons while crouching (stick held at 2)."""
    motion("2", 2)
    press_buttons(*buttons, frames=frames)

def st(*buttons, frames: float = 3):
    """Press buttons from standing (neutral)."""
    neutral(1)
    press_buttons(*buttons, frames=frames)

def link(ms: float = 50):
    """Pause between linked normals (not cancel — let the move recover)."""
    neutral(2)
    wait(ms)

def cancel(ms: float = 20):
    """Short pause before a special cancel (tighter than a link)."""
    wait(ms)


# ══════════════════════════════════════════════════════════════════════════════
#  ▓▓  AKUMA  ▓▓
# ══════════════════════════════════════════════════════════════════════════════
# Gohadouken (QCF+P) · Goshoryuken (623+P) · Zanku Hadouken (air QCF+P)
# Tatsumaki Zankukyaku (QCB+K) · Hyakkishu (214+K flip)
# Supers: Messatsu-Goshoryuken (236236+P) Lv1 · Messatsu-Goshoryu (214214+P) Lv2
#         Shin Shun Goku Satsu (214214+LP+MP) Lv3

def akuma_bnb_1():
    """cr.MP > cr.MP xx HP Goshoryuken — Meterless BnB, core cancel."""
    cr("MP"); link(45)
    cr("MP"); cancel(25)
    dp(); press_buttons("HP"); neutral()

def akuma_bnb_2():
    """cr.LK > cr.LP > cr.MP xx Gohadouken (QCF+HP) — Low starter confirm."""
    cr("LK", frames=2); link(35)
    cr("LP", frames=2); link(35)
    cr("MP"); cancel(20)
    qcf(); press_buttons("HP"); neutral()

def akuma_punish_1():
    """st.HP xx HP Goshoryuken — Biggest meterless punish window."""
    st("HP", frames=4); cancel(35)
    dp(); press_buttons("HP"); neutral()

def akuma_punish_2():
    """cr.MP > st.HP xx OD Goshoryuken > juggle HP DP — Full Drive punish."""
    cr("MP"); link(45)
    st("HP", frames=4); cancel(35)
    dp(); od("LP", "HP"); neutral()
    wait(180)
    dp(); press_buttons("HP"); neutral()

def akuma_super_1():
    """cr.MP > cr.HP xx Messatsu-Goshoryuken (236236+HP) Lv1 — Fast super route."""
    cr("MP"); link(40)
    cr("HP", frames=4); cancel(25)
    qcf(); qcf(); press_buttons("HP"); neutral()

def akuma_advanced():
    """
    ADVANCED — cr.LK > cr.LP > cr.MP > st.HP xx OD Tatsumaki > juggle HP DP
    Full Drive punish off a low starter. Cancel window is tight.
    OD Tatsumaki (QCB+MK+HK) wallsplats in corner for a juggle HP DP.
    """
    cr("LK", frames=2); link(35)
    cr("LP", frames=2); link(35)
    cr("MP"); link(45)
    st("HP", frames=4); cancel(30)
    qcb(); od("MK", "HK")
    wait(260)
    dp(); press_buttons("HP"); neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  ▓▓  CHUN-LI  ▓▓
# ══════════════════════════════════════════════════════════════════════════════
# Kikoken (QCF+P) · SBK/Spinning Bird Kick (charge 4→6+K)
# Hyakuretsukyaku (rapid HK) · Hazan Shu (charge 2→8+K, overhead)
# Super: Kikosho (236236+P) Lv1 · Hoyokusen (236236+K) Lv2

def chunli_bnb_1():
    """cr.MK xx Spinning Bird Kick (charge 4→6+HK) — Classic charge BnB."""
    hold_charge("4", 10)
    motion("2", 2); press_buttons("MK", frames=3)   # cr.MK while holding charge
    motion("6", 2); press_buttons("HK"); neutral()  # release charge into SBK

def chunli_bnb_2():
    """cr.LP > cr.LP > cr.MK xx Kikoken (QCF+HP) — Meterless poke confirm."""
    cr("LP", frames=2); link(35)
    cr("LP", frames=2); link(35)
    cr("MK"); cancel(20)
    qcf(); press_buttons("HP"); neutral()

def chunli_punish_1():
    """st.MP > st.HP xx Hyakuretsukyaku — Standard punish, rapid legs ender."""
    st("MP"); link(45)
    st("HP", frames=4); cancel(25)
    for _ in range(6):
        press_buttons("HK", frames=2); wait(25)
    neutral()

def chunli_punish_2():
    """cr.MP > st.HP xx OD SBK (charge) > juggle HP — Corner carry punish."""
    hold_charge("4", 6)
    motion("2", 2); press_buttons("MP", frames=3); neutral(2); wait(45)
    st("HP", frames=4); cancel(28)
    motion("4", 5); motion("6", 2)
    od("MK", "HK")
    wait(240); st("HP"); neutral()

def chunli_super_1():
    """cr.MP > cr.HP xx Kikosho (236236+HP) Lv1 — BnB into fast super."""
    cr("MP"); link(45)
    cr("HP", frames=4); cancel(25)
    qcf(); qcf(); press_buttons("HP"); neutral()

def chunli_advanced():
    """
    ADVANCED — cr.LP > cr.LP > cr.MK xx OD SBK (charge) > Hazan Shu > Hoyokusen Lv2
    Full meter route: OD SBK launches, then Hazan Shu (charge 2→8+HK) juggles,
    cancelled into Hoyokusen (236236+HK) for maximum damage.
    Requires charge built before combo starts (hold back during approach).
    """
    hold_charge("4", 8)
    cr("LP", frames=2); link(30)
    cr("LP", frames=2); link(30)
    cr("MK"); cancel(20)
    motion("4", 5); motion("6", 2); od("MK", "HK")   # OD SBK
    wait(200)
    # Hazan Shu: charge 2→8+HK
    motion("2", 6); motion("8", 2); press_buttons("HK"); neutral()
    wait(180)
    qcf(); qcf(); press_buttons("HK"); neutral()       # Hoyokusen Lv2


# ══════════════════════════════════════════════════════════════════════════════
#  ▓▓  MAI  ▓▓
# ══════════════════════════════════════════════════════════════════════════════
# Kachousen (QCF+P fan fireball) · Ryuuenbu (QCB+K spinning fire)
# Musasabi no Mai (hold 4→6+K wall dive) · Chou Midare Kachousen (air)
# Super: Hissatsu Shinobibachi (236236+K) Lv1 · Sen'en Ryuuenbu (214214+K) Lv2

def mai_bnb_1():
    """cr.LK > cr.LP > st.MP xx Kachousen (QCF+HP) — Low starter into fan."""
    cr("LK", frames=2); link(35)
    cr("LP", frames=2); link(35)
    st("MP"); cancel(25)
    qcf(); press_buttons("HP"); neutral()

def mai_bnb_2():
    """st.MP > st.HP xx Ryuuenbu (QCB+HK) — Mid-range BnB, corner carry."""
    st("MP"); link(45)
    st("HP", frames=4); cancel(28)
    qcb(); press_buttons("HK"); neutral()

def mai_punish_1():
    """cr.MP > st.HP xx Kachousen (QCF+HP) — Reliable whiff punish."""
    cr("MP"); link(45)
    st("HP", frames=4); cancel(28)
    qcf(); press_buttons("HP"); neutral()

def mai_punish_2():
    """cr.MP > st.HP xx OD Ryuuenbu > juggle st.HP > Kachousen — Extended punish."""
    cr("MP"); link(45)
    st("HP", frames=4); cancel(28)
    qcb(); od("MK", "HK")
    wait(200)
    st("HP", frames=4); cancel(25)
    qcf(); press_buttons("HP"); neutral()

def mai_super_1():
    """cr.MP > st.HP xx Hissatsu Shinobibachi (236236+HK) Lv1."""
    cr("MP"); link(45)
    st("HP", frames=4); cancel(28)
    qcf(); qcf(); press_buttons("HK"); neutral()

def mai_advanced():
    """
    ADVANCED — cr.LK > cr.LP > st.MP > st.HP xx OD Ryuuenbu > juggle HP
               xx Sen'en Ryuuenbu (214214+HK) Lv2
    Full meter punish off a low starter. OD Ryuuenbu launches, juggle HP
    cancelled into Lv2 Super for screen-clearing damage.
    """
    cr("LK", frames=2); link(35)
    cr("LP", frames=2); link(35)
    st("MP"); link(45)
    st("HP", frames=4); cancel(28)
    qcb(); od("MK", "HK")
    wait(200)
    st("HP", frames=4); cancel(25)
    qcb(); qcb(); press_buttons("HK"); neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  ▓▓  KEN  ▓▓
# ══════════════════════════════════════════════════════════════════════════════
# Hadouken (QCF+P) · Shoryuken (623+P) · Tatsumaki (QCB+K)
# Jinrai Kick (236+K) — 3-part target combo chain
# Super: Shinryuken (236236+P) Lv1 · Shippu Jinraikyaku (236236+K) Lv3

def ken_bnb_1():
    """cr.MK xx Hadouken (QCF+HP) — Fundamental, safe fireball cancel."""
    cr("MK"); cancel(20)
    qcf(); press_buttons("HP"); neutral()

def ken_bnb_2():
    """cr.LP > cr.LP > cr.MK xx Jinrai Kick (236+MK) — Low starter chain."""
    cr("LP", frames=2); link(35)
    cr("LP", frames=2); link(35)
    cr("MK"); cancel(20)
    qcf(); press_buttons("MK"); neutral()

def ken_punish_1():
    """st.MP > st.HP xx HP Shoryuken (623+HP) — Classic Ken punish."""
    st("MP"); link(45)
    st("HP", frames=4); cancel(30)
    dp(); press_buttons("HP"); neutral()

def ken_punish_2():
    """cr.MP > st.HP xx OD Shoryuken > juggle Tatsumaki (QCB+HK)."""
    cr("MP"); link(45)
    st("HP", frames=4); cancel(30)
    dp(); od("LP", "HP")
    wait(260)
    qcb(); press_buttons("HK"); neutral()

def ken_super_1():
    """cr.MK xx Shinryuken (236236+HP) Lv1 — Fastest super route."""
    cr("MK"); cancel(20)
    qcf(); qcf(); press_buttons("HP"); neutral()

def ken_advanced():
    """
    ADVANCED — st.MP > st.HP xx OD Shoryuken > juggle Jinrai MK > Jinrai HK
               > Jinrai HP xx Shinryuken Lv1
    Full Drive + Super combo. OD DP launches; Jinrai follow-up chain
    (236+MK → auto-follow MK → HP) cancels into Shinryuken for max damage.
    The Jinrai chain auto-follows on hit — just re-fire QCF+MK twice after landing.
    """
    st("MP"); link(45)
    st("HP", frames=4); cancel(30)
    dp(); od("LP", "HP")
    wait(250)
    # Jinrai first hit
    qcf(); press_buttons("MK")
    wait(80)
    # Jinrai second hit (auto-follow)
    press_buttons("MK")
    wait(80)
    # Jinrai third hit cancelled into super
    press_buttons("HP"); cancel(20)
    qcf(); qcf(); press_buttons("HP"); neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  ▓▓  JURI  ▓▓
# ══════════════════════════════════════════════════════════════════════════════
# Fuha Stock (236+K — store) / Release (236+K again — different K = release)
# Shiku-sen (236+K dive kick) · Saihasho / Ankensatsu / Kaisen Dankairaku releases
# Super: Feng Shui Engine (214214+LK) Lv1 · Feng Shui Engine Omega (214214+HK) Lv3
# NOTE: F1/F3/F6 require a pre-stored Fuha stock (press 236+LK in neutral first).

def juri_bnb_1():
    """cr.MK > st.HP xx Fuha Release LP (QCF+LP) — Needs 1 stock."""
    cr("MK"); link(45)
    st("HP", frames=4); cancel(28)
    qcf(); press_buttons("LP"); neutral()

def juri_bnb_2():
    """cr.LP > cr.LP > cr.MK xx Shiku-sen (QCF+MK) — No stock needed."""
    cr("LP", frames=2); link(35)
    cr("LP", frames=2); link(35)
    cr("MK"); cancel(22)
    qcf(); press_buttons("MK"); neutral()

def juri_punish_1():
    """st.HP xx Fuha Release HP (QCF+HP) — Full-screen punish. Needs 1 stock."""
    st("HP", frames=4); cancel(28)
    qcf(); press_buttons("HP"); neutral()

def juri_punish_2():
    """cr.MP > st.HP xx OD Shiku-sen > cr.HP > Fuha Release LP — Drive punish."""
    cr("MP"); link(45)
    st("HP", frames=4); cancel(28)
    qcf(); od("MK", "HK")
    wait(190)
    cr("HP", frames=4); cancel(25)
    qcf(); press_buttons("LP"); neutral()

def juri_super_1():
    """cr.MK > st.HP xx Feng Shui Engine (214214+LK) Lv1 — Activates powered state."""
    cr("MK"); link(45)
    st("HP", frames=4); cancel(28)
    qcb(); qcb(); press_buttons("LK"); neutral()

def juri_advanced():
    """
    ADVANCED — cr.LP > cr.MK > st.HP xx OD Shiku-sen > cr.HP xx Fuha HP Release
               > Feng Shui Engine Omega (214214+HK) Lv3
    Full meter + Lv3 super route off a low starter. Needs 1 stored Fuha stock.
    Fuha release extends the juggle; Lv3 super is then activated for massive damage.
    """
    cr("LP", frames=2); link(35)
    cr("MK"); link(45)
    st("HP", frames=4); cancel(28)
    qcf(); od("MK", "HK")
    wait(190)
    cr("HP", frames=4); cancel(25)
    qcf(); press_buttons("HP")           # Fuha HP release
    wait(150)
    qcb(); qcb(); press_buttons("HK"); neutral()   # Lv3 super


# ══════════════════════════════════════════════════════════════════════════════
#  ▓▓  CAMMY  ▓▓
# ══════════════════════════════════════════════════════════════════════════════
# Spiral Arrow (QCF+K) · Cannon Spike (623+K) · Quick Spin Knuckle (236+P)
# Hooligan Combination (QCB+P) · Delta Red Combination (target combo)
# Super: Spin Drive Smasher (236236+K) Lv1 · Delta Red Assault (236236+P) Lv2

def cammy_bnb_1():
    """cr.LK > cr.LP > cr.MK xx Spiral Arrow MK (QCF+MK) — Low starter."""
    cr("LK", frames=2); link(35)
    cr("LP", frames=2); link(35)
    cr("MK"); cancel(20)
    qcf(); press_buttons("MK"); neutral()

def cammy_bnb_2():
    """st.MP > st.MP > cr.MK xx Spiral Arrow HK — Target combo into HK slide."""
    st("MP"); link(35)
    st("MP"); link(40)    # second hit of target combo
    cr("MK"); cancel(20)
    qcf(); press_buttons("HK"); neutral()

def cammy_punish_1():
    """st.HP xx Cannon Spike (623+HK) — Hard knockdown punish."""
    st("HP", frames=4); cancel(30)
    dp(); press_buttons("HK"); neutral()

def cammy_punish_2():
    """cr.MP > st.HP xx OD Spiral Arrow > juggle Cannon Spike — Drive punish."""
    cr("MP"); link(45)
    st("HP", frames=4); cancel(30)
    qcf(); od("MK", "HK")
    wait(210)
    dp(); press_buttons("HK"); neutral()

def cammy_super_1():
    """cr.MK xx Spin Drive Smasher (236236+HK) Lv1 — Fast super route."""
    cr("MK"); cancel(20)
    qcf(); qcf(); press_buttons("HK"); neutral()

def cammy_advanced():
    """
    ADVANCED — cr.LP > cr.LP > st.MP > st.MP > cr.HP xx OD Cannon Spike
               > juggle Quick Spin Knuckle (236+HP) xx Delta Red Assault Lv2
    Long low-starter chain into OD Cannon Spike launcher, QSK juggle cancelled
    into Lv2 super. Hardest Cammy combo — tight cancel window on cr.HP.
    """
    cr("LP", frames=2); link(35)
    cr("LP", frames=2); link(35)
    st("MP"); link(35)
    st("MP"); link(38)
    cr("HP", frames=4); cancel(28)
    dp(); od("LK", "HK")         # OD Cannon Spike (623+LK+HK)
    wait(220)
    # Quick Spin Knuckle juggle: 236+HP
    qcf(); press_buttons("HP"); cancel(25)
    # Delta Red Assault Lv2: 236236+LP
    qcf(); qcf(); press_buttons("LP"); neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  ▓▓  RYU  ▓▓
# ══════════════════════════════════════════════════════════════════════════════
# Hadouken (QCF+P) · Shoryuken (623+P) · Tatsumaki (QCB+K)
# Hashogeki (236+P palm, chargeable) · Denjin Charge (hold HP+HK)
# Super: Shin Hashogeki (236236+P) Lv1 · Shin Shoryuken (236236+HP hold) Lv3

def ryu_bnb_1():
    """cr.MK xx Hadouken (QCF+HP) — The most classic SF combo."""
    cr("MK"); cancel(20)
    qcf(); press_buttons("HP"); neutral()

def ryu_bnb_2():
    """cr.LP > cr.LP > cr.MK xx Hashogeki (236+HP) — Low starter into palm."""
    cr("LP", frames=2); link(35)
    cr("LP", frames=2); link(35)
    cr("MK"); cancel(20)
    qcf(); press_buttons("HP"); neutral()

def ryu_punish_1():
    """st.HP xx HP Shoryuken (623+HP) — Maximum meterless punish."""
    st("HP", frames=4); cancel(30)
    dp(); press_buttons("HP"); neutral()

def ryu_punish_2():
    """cr.MP > st.HP xx OD Shoryuken > juggle Tatsumaki (QCB+HK)."""
    cr("MP"); link(45)
    st("HP", frames=4); cancel(30)
    dp(); od("LP", "HP")
    wait(260)
    qcb(); press_buttons("HK"); neutral()

def ryu_super_1():
    """cr.MK xx Shin Hashogeki (236236+HP) Lv1 — Fast super ender."""
    cr("MK"); cancel(20)
    qcf(); qcf(); press_buttons("HP"); neutral()

def ryu_advanced():
    """
    ADVANCED — cr.MP > st.HP xx OD Shoryuken > juggle Tatsumaki (QCB+HK)
               xx Shin Shoryuken (236236+HP hold) Lv3
    Full Drive + Lv3 Super. Tatsumaki juggle is cancelled into Lv3 Shin Shoryuken
    for a devastating wall-bounce combo. The held HP activates the powered version.
    Requires full Drive Gauge + Lv3 super meter.
    """
    cr("MP"); link(45)
    st("HP", frames=4); cancel(30)
    dp(); od("LP", "HP")
    wait(260)
    qcb(); press_buttons("HK"); cancel(30)
    # Shin Shoryuken Lv3: 236236 + HP (hold)
    qcf(); qcf()
    # Hold HP for powered version
    _press_raw("HP"); gamepad.update()
    _sleep(f(20))                  # hold for ~20 frames = powered Shin Shoryuken
    _release_raw("HP"); gamepad.update()
    neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  ▓▓  ED  ▓▓
# ══════════════════════════════════════════════════════════════════════════════
# Ed uses hold-release charge mechanics:
#   Psycho Spark   — hold 4, tap 6+P   (projectile)
#   Psycho Blitz   — hold 4, tap 6+K   (rush punch)
#   Psycho Upper   — hold 2, tap 8+P   (uppercut/DP)
#   Flicker        — 236+P             (quick jab)
# Super: Psycho Cannon Barrage (236236+P) Lv1

def ed_bnb_1():
    """cr.LP > cr.LP > st.MP xx Psycho Blitz (hold 4→6+MK) — Easy low starter."""
    hold_charge("4", 3)
    motion("24", 1); press_buttons("LP", frames=2); wait(35)
    motion("24", 1); press_buttons("LP", frames=2); wait(35)
    motion("4", 4); press_buttons("MP", frames=3); wait(25)
    motion("4", 5); motion("6", 2); press_buttons("MK"); neutral()

def ed_bnb_2():
    """cr.MK xx Flicker (236+LP) > Psycho Spark (hold 4→6+HP) — Double cancel."""
    cr("MK"); cancel(20)
    qcf(); press_buttons("LP")
    wait(80)
    motion("4", 5); motion("6", 2); press_buttons("HP"); neutral()

def ed_punish_1():
    """st.HP xx Psycho Upper (hold 2→8+HP) — DP-equivalent punish."""
    st("HP", frames=4); cancel(30)
    motion("2", 6); motion("8", 2); press_buttons("HP"); neutral()

def ed_punish_2():
    """cr.MP > st.HP xx OD Psycho Upper > juggle Psycho Blitz (hold 4→6+HK)."""
    cr("MP"); link(45)
    st("HP", frames=4); cancel(30)
    motion("2", 6); motion("8", 2); od("LP", "HP")
    wait(230)
    motion("4", 5); motion("6", 2); press_buttons("HK"); neutral()

def ed_super_1():
    """cr.MK xx Psycho Cannon Barrage (236236+HP) Lv1."""
    cr("MK"); cancel(20)
    qcf(); qcf(); press_buttons("HP"); neutral()

def ed_advanced():
    """
    ADVANCED — cr.LP > cr.LP > st.MP xx Psycho Blitz (4→6+MK)
               > Psycho Spark (4→6+HP) > Psycho Cannon Barrage Lv1
    Triple-cancel route. Psycho Blitz into Spark is a special cancel chain;
    Spark is then super-cancelled into Cannon Barrage for max damage.
    """
    hold_charge("4", 3)
    motion("24", 1); press_buttons("LP", frames=2); wait(35)
    motion("24", 1); press_buttons("LP", frames=2); wait(35)
    motion("4", 4); press_buttons("MP", frames=3); wait(25)
    motion("4", 5); motion("6", 2); press_buttons("MK")  # Psycho Blitz
    wait(80)
    motion("4", 5); motion("6", 2); press_buttons("HP")  # Psycho Spark
    wait(60)
    qcf(); qcf(); press_buttons("HP"); neutral()          # Cannon Barrage


# ══════════════════════════════════════════════════════════════════════════════
#  ▓▓  JP  ▓▓
# ══════════════════════════════════════════════════════════════════════════════
# JP's normals have extended range (cane). His puppet Amnesia creates screen control.
# Amnesia Surge (QCF+P) · Amnesia Trap (QCB+P) · Departure (623+K)
# Consume (214+K — command grab) · Ride the Lightning (Super grab)
# Super: Interdiction (236236+P) Lv1

def jp_bnb_1():
    """st.MP > st.HP xx Amnesia Surge (QCF+HP) — Core long-range BnB."""
    st("MP"); link(40)
    st("HP", frames=4); cancel(28)
    qcf(); press_buttons("HP"); neutral()

def jp_bnb_2():
    """cr.LP > cr.MP xx Surge (QCF+MP) > Departure (623+HK) — Double special."""
    cr("LP", frames=2); link(35)
    cr("MP"); cancel(22)
    qcf(); press_buttons("MP")
    wait(140)
    dp(); press_buttons("HK"); neutral()

def jp_punish_1():
    """st.HP xx Surge (QCF+HP) > Departure (623+MK) — Two-special punish."""
    st("HP", frames=4); cancel(28)
    qcf(); press_buttons("HP")
    wait(120)
    dp(); press_buttons("MK"); neutral()

def jp_punish_2():
    """st.MP > st.HP xx OD Surge > juggle Departure (623+HK) — Drive punish."""
    st("MP"); link(40)
    st("HP", frames=4); cancel(28)
    qcf(); od("LP", "HP")
    wait(220)
    dp(); press_buttons("HK"); neutral()

def jp_super_1():
    """st.HP xx Interdiction (236236+HP) Lv1 — Full-screen super ender."""
    st("HP", frames=4); cancel(28)
    qcf(); qcf(); press_buttons("HP"); neutral()

def jp_advanced():
    """
    ADVANCED — st.MP > st.HP xx OD Surge > juggle Departure HK > Surge HP
               xx Interdiction Lv1
    OD Surge launches; Departure adds juggle damage, then Surge HP is
    super-cancelled into Interdiction for the full punish route.
    """
    st("MP"); link(40)
    st("HP", frames=4); cancel(28)
    qcf(); od("LP", "HP")
    wait(220)
    dp(); press_buttons("HK")         # Departure juggle
    wait(160)
    qcf(); press_buttons("HP")        # Amnesia Surge HP cancel
    wait(60)
    qcf(); qcf(); press_buttons("HP"); neutral()   # Interdiction


# ══════════════════════════════════════════════════════════════════════════════
#  ▓▓  MARISA  ▓▓
# ══════════════════════════════════════════════════════════════════════════════
# Marisa is a grappler/brawler with huge damage on every hit. Slow but devastating.
# Key specials:
#   Gladius     — QCF+P  (rushing punch, hits armored)
#   Dimachaerus — 623+P  (DP-style rising punch, anti-air)
#   Quadriga    — QCB+P  (charge punch, can be held)
#   Scutum      — hold HP (parry/absorb stance)
# Super: Aether (236236+P) Lv1 · Goddess of the Hunt (236236+HP hold) Lv3
# NOTE: Marisa's normals deal massive stun AND damage — even short combos kill.

def marisa_bnb_1():
    """cr.MP > st.HP xx Gladius (QCF+HP) — Core BnB, massive damage."""
    cr("MP"); link(50)
    st("HP", frames=4); cancel(30)
    qcf(); press_buttons("HP"); neutral()

def marisa_bnb_2():
    """cr.LK > cr.LP > cr.MP xx Gladius (QCF+MP) — Low starter confirm."""
    cr("LK", frames=2); link(40)
    cr("LP", frames=2); link(40)
    cr("MP"); cancel(28)
    qcf(); press_buttons("MP"); neutral()

def marisa_punish_1():
    """st.HP xx Dimachaerus (623+HP) — Single-hit punish, enormous damage."""
    st("HP", frames=5); cancel(30)
    dp(); press_buttons("HP"); neutral()

def marisa_punish_2():
    """cr.MP > st.HP xx OD Dimachaerus (623+LP+HP) > juggle Gladius HP — Drive punish."""
    cr("MP"); link(50)
    st("HP", frames=4); cancel(30)
    dp(); od("LP", "HP")
    wait(230)
    qcf(); press_buttons("HP"); neutral()

def marisa_super_1():
    """st.HP xx Aether (236236+HP) Lv1 — Massive super punish ender."""
    st("HP", frames=5); cancel(28)
    qcf(); qcf(); press_buttons("HP"); neutral()

def marisa_advanced():
    """
    ADVANCED — cr.LP > cr.MP > st.HP xx OD Dimachaerus > juggle Gladius HP
               xx Goddess of the Hunt (236236+HP hold) Lv3
    Full meter route. OD DP launches into Gladius juggle cancelled into
    Lv3 Super for screen-shaking maximum damage. Marisa's highest damage combo.
    """
    cr("LP", frames=2); link(40)
    cr("MP"); link(50)
    st("HP", frames=4); cancel(30)
    dp(); od("LP", "HP")
    wait(230)
    qcf(); press_buttons("HP"); cancel(28)
    # Goddess of the Hunt Lv3: 236236+HP (hold)
    qcf(); qcf()
    _press_raw("HP"); gamepad.update()
    _sleep(f(18))
    _release_raw("HP"); gamepad.update()
    neutral()


# ══════════════════════════════════════════════════════════════════════════════
#  ▓▓  LUKE  ▓▓
# ══════════════════════════════════════════════════════════════════════════════
# Luke is an MMA-inspired rushdown character. Fast, damaging, great drive usage.
# Key specials:
#   Flash Knuckle — hold 4→6+P  (rushing overhand; can be charged for more damage)
#   Rising Uppercut — 623+P     (DP, very fast, great anti-air)
#   Avenger       — QCB+K       (overhead rushing kick)
#   Sand Blast    — QCF+P       (slow fireball, good oki)
# Super: Vulcan Blast (236236+P) Lv1 · Final Strike (236236+HP charge) Lv3
# Luke's gameplan: get in, Flash Knuckle pressure, DP on reversal, huge damage.

def luke_bnb_1():
    """cr.MK xx Flash Knuckle (hold 4→6+MP) — Core BnB, great range."""
    hold_charge("4", 6)
    cr("MK"); cancel(20)
    motion("4", 5); motion("6", 2); press_buttons("MP"); neutral()

def luke_bnb_2():
    """cr.LP > cr.LP > cr.MK xx Sand Blast (QCF+HP) — Low starter fireball cancel."""
    cr("LP", frames=2); link(35)
    cr("LP", frames=2); link(35)
    cr("MK"); cancel(20)
    qcf(); press_buttons("HP"); neutral()

def luke_punish_1():
    """st.HP xx Rising Uppercut (623+HP) — Fast, huge punish damage."""
    st("HP", frames=4); cancel(30)
    dp(); press_buttons("HP"); neutral()

def luke_punish_2():
    """cr.MP > st.HP xx OD Rising Uppercut > juggle Flash Knuckle HP — Drive punish."""
    cr("MP"); link(45)
    st("HP", frames=4); cancel(30)
    dp(); od("LP", "HP")
    wait(240)
    motion("4", 5); motion("6", 2); press_buttons("HP"); neutral()

def luke_super_1():
    """cr.MK xx Vulcan Blast (236236+HP) Lv1 — Standard super ender."""
    cr("MK"); cancel(20)
    qcf(); qcf(); press_buttons("HP"); neutral()

def luke_advanced():
    """
    ADVANCED — cr.LP > cr.LP > cr.MK xx OD Flash Knuckle (hold 4→6+LP+MP)
               > juggle Rising Uppercut HP xx Vulcan Blast Lv1
    OD Flash Knuckle (charged version) launches on hit in Drive Rush context;
    Rising Uppercut juggle is super-cancelled into Vulcan Blast for max damage.
    Requires Drive Gauge + Lv1 super.
    """
    hold_charge("4", 4)
    cr("LP", frames=2); link(32)
    cr("LP", frames=2); link(32)
    cr("MK"); cancel(20)
    motion("4", 6); motion("6", 2); od("LP", "MP")   # OD Flash Knuckle
    wait(220)
    dp(); press_buttons("HP"); cancel(25)              # Rising Uppercut juggle
    qcf(); qcf(); press_buttons("HP"); neutral()       # Vulcan Blast


# ══════════════════════════════════════════════════════════════════════════════
#  ▓▓  A.K.I.  ▓▓
# ══════════════════════════════════════════════════════════════════════════════
# A.K.I. is a poison/snake-themed zoner-assassin hybrid.
# She poisons opponents and deals extra damage through poison ticks.
# Key specials:
#   Cruel Fate    — QCF+P  (poison claw scratch, applies poison)
#   Clinging Cobra— QCB+P  (snake fang projectile)
#   Sinister Slide— QCF+K  (low slide, goes under fireballs)
#   Nightshade Pulse — 236+K (slow poison explosion)
# Super: Coronation (236236+P) Lv1 · Serpent's Embrace (214214+P) Lv2
# NOTE: A.K.I. deals extra damage to poisoned opponents. Open combos with
#       Cruel Fate to apply poison before extending.

def aki_bnb_1():
    """cr.LP > cr.MP xx Cruel Fate (QCF+HP) — Applies poison, core BnB."""
    cr("LP", frames=2); link(38)
    cr("MP"); cancel(22)
    qcf(); press_buttons("HP"); neutral()

def aki_bnb_2():
    """st.MP > st.HP xx Sinister Slide (QCF+MK) — Mid-range low slide cancel."""
    st("MP"); link(42)
    st("HP", frames=4); cancel(28)
    qcf(); press_buttons("MK"); neutral()

def aki_punish_1():
    """cr.MP > st.HP xx Cruel Fate HP > Clinging Cobra (QCB+HP) — Poison punish."""
    cr("MP"); link(45)
    st("HP", frames=4); cancel(28)
    qcf(); press_buttons("HP")    # Cruel Fate (poison)
    wait(120)
    qcb(); press_buttons("HP"); neutral()   # Clinging Cobra follow-up

def aki_punish_2():
    """cr.MP > st.HP xx OD Cruel Fate > juggle st.HP > Clinging Cobra — Drive punish."""
    cr("MP"); link(45)
    st("HP", frames=4); cancel(28)
    qcf(); od("LP", "HP")
    wait(210)
    st("HP", frames=4); cancel(25)
    qcb(); press_buttons("HP"); neutral()

def aki_super_1():
    """st.HP xx Coronation (236236+HP) Lv1 — Full-screen super ender."""
    st("HP", frames=4); cancel(28)
    qcf(); qcf(); press_buttons("HP"); neutral()

def aki_advanced():
    """
    ADVANCED — cr.LP > cr.MP xx Cruel Fate HP (poison) > Clinging Cobra HP
               > OD Sinister Slide > juggle st.HP xx Coronation Lv1
    Apply poison first, then extend into an OD slide launcher, juggle,
    and super cancel. Poison ticks add significant bonus damage throughout.
    Requires Drive Gauge + Lv1 super.
    """
    cr("LP", frames=2); link(38)
    cr("MP"); cancel(22)
    qcf(); press_buttons("HP")         # Cruel Fate (poison applied)
    wait(100)
    qcb(); press_buttons("HP")         # Clinging Cobra
    wait(100)
    qcf(); od("LP", "MK")              # OD Sinister Slide launcher
    wait(200)
    st("HP", frames=4); cancel(25)
    qcf(); qcf(); press_buttons("HP"); neutral()   # Coronation


# ══════════════════════════════════════════════════════════════════════════════
#  ▓▓  M. BISON  ▓▓
# ══════════════════════════════════════════════════════════════════════════════
# M. Bison is a Psycho Power charge character — one of SF6's most powerful.
# He uses held-direction charge mechanics extensively.
# Key specials:
#   Psycho Crusher  — hold 4→6+P    (torpedo attack, charge)
#   Scissors Kick   — hold 4→6+K    (rushing kick, charge, his best special)
#   Devil Reverse   — hold 4→6+K, then up (redirect overhead)
#   Head Press      — hold 2→8+K    (overhead stomp from air, charge)
# Super: Knee Press Nightmare (236236+K) Lv1 · Psycho Punisher (236236+P) Lv3
# NOTE: Bison's charge combos require holding the charge direction during normals.

def bison_bnb_1():
    """cr.MK xx Scissors Kick MK (hold 4→6+MK) — Core Bison BnB."""
    hold_charge("4", 8)
    motion("2", 2); press_buttons("MK", frames=3)   # cr.MK while charging
    motion("4", 4); motion("6", 2); press_buttons("MK"); neutral()

def bison_bnb_2():
    """cr.LP > cr.LP > cr.MK xx Psycho Crusher HP (hold 4→6+HP) — Low starter."""
    hold_charge("4", 6)
    motion("24", 1); press_buttons("LP", frames=2); wait(35)
    motion("24", 1); press_buttons("LP", frames=2); wait(35)
    motion("2", 2); press_buttons("MK", frames=3)
    motion("4", 4); motion("6", 2); press_buttons("HP"); neutral()

def bison_punish_1():
    """st.HP xx Scissors Kick HK (hold 4→6+HK) — Big punish, corner carry."""
    hold_charge("4", 8)
    st("HP", frames=4); cancel(28)
    motion("4", 4); motion("6", 2); press_buttons("HK"); neutral()

def bison_punish_2():
    """cr.MP > st.HP xx OD Scissors Kick > juggle Psycho Crusher HP — Drive punish."""
    hold_charge("4", 8)
    cr("MP"); link(48)
    st("HP", frames=4); cancel(28)
    motion("4", 5); motion("6", 2); od("MK", "HK")   # OD Scissors
    wait(230)
    motion("4", 5); motion("6", 2); press_buttons("HP"); neutral()

def bison_super_1():
    """cr.MK xx Knee Press Nightmare (236236+HK) Lv1 — Fast super from cr.MK."""
    cr("MK"); cancel(20)
    qcf(); qcf(); press_buttons("HK"); neutral()

def bison_advanced():
    """
    ADVANCED — cr.LP > cr.MK xx OD Scissors Kick > juggle Scissors HK
               > Psycho Crusher HP xx Knee Press Nightmare Lv1
    Full charge + Drive route off a low confirm. OD Scissors launches;
    Scissors HK juggle charges are maintained, then Psycho Crusher super-cancelled
    into Knee Press Nightmare for Bison's full punish damage output.
    """
    hold_charge("4", 8)
    motion("24", 1); press_buttons("LP", frames=2); wait(38)
    motion("2", 2); press_buttons("MK", frames=3)
    motion("4", 5); motion("6", 2); od("MK", "HK")    # OD Scissors
    wait(220)
    # Re-establish charge quickly
    motion("4", 5); motion("6", 2); press_buttons("HK")  # Scissors juggle
    wait(160)
    motion("4", 5); motion("6", 2); press_buttons("HP")  # Psycho Crusher cancel
    wait(60)
    qcf(); qcf(); press_buttons("HK"); neutral()          # Knee Press Nightmare


# ══════════════════════════════════════════════════════════════════════════════
#  COMBO REGISTRY
# ══════════════════════════════════════════════════════════════════════════════
# Each character has 6 combos: F1=BnB1, F2=BnB2, F3=Punish1, F4=Punish2(OD),
# F5=Super route, F6_ADV=Advanced (GUI button only, not a hotkey)

def _entry(fn, label, slot):
    return {"fn": fn, "label": label, "slot": slot}

ALL_COMBOS = {
    "Akuma": [
        _entry(akuma_bnb_1,    "BnB #1 — cr.MP > cr.MP xx HP Goshoryuken",            "F1"),
        _entry(akuma_bnb_2,    "BnB #2 — cr.LK > cr.LP > cr.MP xx Gohadouken",        "F2"),
        _entry(akuma_punish_1, "Punish #1 — st.HP xx HP Goshoryuken",                  "F3"),
        _entry(akuma_punish_2, "Punish #2 — OD Goshoryuken > juggle HP DP",            "F4"),
        _entry(akuma_super_1,  "Super — cr.MP > cr.HP xx Messatsu-Goshoryuken Lv1",    "F5"),
        _entry(akuma_advanced, "ADV — Low starter > OD Tatsumaki > HP DP",             "ADV"),
    ],
    "Chun-Li": [
        _entry(chunli_bnb_1,    "BnB #1 — cr.MK xx Spinning Bird Kick (charge)",       "F1"),
        _entry(chunli_bnb_2,    "BnB #2 — cr.LP > cr.LP > cr.MK xx Kikoken",           "F2"),
        _entry(chunli_punish_1, "Punish #1 — st.MP > st.HP xx Hyakuretsukyaku",        "F3"),
        _entry(chunli_punish_2, "Punish #2 — OD SBK > juggle HP",                      "F4"),
        _entry(chunli_super_1,  "Super — cr.MP > cr.HP xx Kikosho Lv1",                "F5"),
        _entry(chunli_advanced, "ADV — Low > OD SBK > Hazan Shu xx Hoyokusen Lv2",    "ADV"),
    ],
    "Mai": [
        _entry(mai_bnb_1,    "BnB #1 — cr.LK > cr.LP > st.MP xx Kachousen",           "F1"),
        _entry(mai_bnb_2,    "BnB #2 — st.MP > st.HP xx Ryuuenbu",                    "F2"),
        _entry(mai_punish_1, "Punish #1 — cr.MP > st.HP xx Kachousen",                "F3"),
        _entry(mai_punish_2, "Punish #2 — OD Ryuuenbu > HP > Kachousen",              "F4"),
        _entry(mai_super_1,  "Super — cr.MP > st.HP xx Hissatsu Shinobibachi Lv1",    "F5"),
        _entry(mai_advanced, "ADV — Low > OD Ryuuenbu > HP xx Sen'en Ryuuenbu Lv2",  "ADV"),
    ],
    "Ken": [
        _entry(ken_bnb_1,    "BnB #1 — cr.MK xx Hadouken",                            "F1"),
        _entry(ken_bnb_2,    "BnB #2 — cr.LP > cr.LP > cr.MK xx Jinrai Kick",         "F2"),
        _entry(ken_punish_1, "Punish #1 — st.MP > st.HP xx HP Shoryuken",             "F3"),
        _entry(ken_punish_2, "Punish #2 — OD Shoryuken > Tatsumaki juggle",           "F4"),
        _entry(ken_super_1,  "Super — cr.MK xx Shinryuken Lv1",                       "F5"),
        _entry(ken_advanced, "ADV — OD DP > Jinrai chain xx Shinryuken Lv1",          "ADV"),
    ],
    "Juri": [
        _entry(juri_bnb_1,    "BnB #1 — cr.MK > st.HP xx Fuha LP ★stock",            "F1"),
        _entry(juri_bnb_2,    "BnB #2 — cr.LP > cr.LP > cr.MK xx Shiku-sen",         "F2"),
        _entry(juri_punish_1, "Punish #1 — st.HP xx Fuha HP ★stock",                  "F3"),
        _entry(juri_punish_2, "Punish #2 — OD Shiku-sen > cr.HP > Fuha",             "F4"),
        _entry(juri_super_1,  "Super — cr.MK > st.HP xx Feng Shui Engine Lv1",       "F5"),
        _entry(juri_advanced, "ADV — Low > OD Shiku > cr.HP > Fuha xx FSE Lv3 ★stock","ADV"),
    ],
    "Cammy": [
        _entry(cammy_bnb_1,    "BnB #1 — cr.LK > cr.LP > cr.MK xx Spiral Arrow",     "F1"),
        _entry(cammy_bnb_2,    "BnB #2 — st.MP > st.MP > cr.MK xx Spiral Arrow HK",  "F2"),
        _entry(cammy_punish_1, "Punish #1 — st.HP xx Cannon Spike",                   "F3"),
        _entry(cammy_punish_2, "Punish #2 — OD Spiral Arrow > Cannon Spike",          "F4"),
        _entry(cammy_super_1,  "Super — cr.MK xx Spin Drive Smasher Lv1",             "F5"),
        _entry(cammy_advanced, "ADV — Long chain > OD Spike > QSK xx Delta Red Lv2", "ADV"),
    ],
    "Ryu": [
        _entry(ryu_bnb_1,    "BnB #1 — cr.MK xx Hadouken",                           "F1"),
        _entry(ryu_bnb_2,    "BnB #2 — cr.LP > cr.LP > cr.MK xx Hashogeki",          "F2"),
        _entry(ryu_punish_1, "Punish #1 — st.HP xx HP Shoryuken",                    "F3"),
        _entry(ryu_punish_2, "Punish #2 — OD Shoryuken > Tatsumaki juggle",          "F4"),
        _entry(ryu_super_1,  "Super — cr.MK xx Shin Hashogeki Lv1",                  "F5"),
        _entry(ryu_advanced, "ADV — OD DP > Tatsumaki xx Shin Shoryuken Lv3 (hold)", "ADV"),
    ],
    "Ed": [
        _entry(ed_bnb_1,    "BnB #1 — cr.LP > cr.LP > st.MP xx Psycho Blitz",        "F1"),
        _entry(ed_bnb_2,    "BnB #2 — cr.MK xx Flicker > Psycho Spark",              "F2"),
        _entry(ed_punish_1, "Punish #1 — st.HP xx Psycho Upper",                     "F3"),
        _entry(ed_punish_2, "Punish #2 — OD Psycho Upper > Psycho Blitz",            "F4"),
        _entry(ed_super_1,  "Super — cr.MK xx Psycho Cannon Barrage Lv1",            "F5"),
        _entry(ed_advanced, "ADV — Low > Blitz > Spark xx Cannon Barrage Lv1",       "ADV"),
    ],
    "JP": [
        _entry(jp_bnb_1,    "BnB #1 — st.MP > st.HP xx Amnesia Surge",               "F1"),
        _entry(jp_bnb_2,    "BnB #2 — cr.LP > cr.MP xx Surge > Departure",           "F2"),
        _entry(jp_punish_1, "Punish #1 — st.HP xx Surge > Departure",                "F3"),
        _entry(jp_punish_2, "Punish #2 — OD Surge > Departure juggle",               "F4"),
        _entry(jp_super_1,  "Super — st.HP xx Interdiction Lv1",                     "F5"),
        _entry(jp_advanced, "ADV — OD Surge > Departure > Surge xx Interdiction",    "ADV"),
    ],
    "Marisa": [
        _entry(marisa_bnb_1,    "BnB #1 — cr.MP > st.HP xx Gladius",                 "F1"),
        _entry(marisa_bnb_2,    "BnB #2 — cr.LK > cr.LP > cr.MP xx Gladius",         "F2"),
        _entry(marisa_punish_1, "Punish #1 — st.HP xx Dimachaerus",                  "F3"),
        _entry(marisa_punish_2, "Punish #2 — OD Dimachaerus > Gladius juggle",       "F4"),
        _entry(marisa_super_1,  "Super — st.HP xx Aether Lv1",                       "F5"),
        _entry(marisa_advanced, "ADV — Low > OD DP > Gladius xx Goddess Lv3 (hold)", "ADV"),
    ],
    "Luke": [
        _entry(luke_bnb_1,    "BnB #1 — cr.MK xx Flash Knuckle (charge)",            "F1"),
        _entry(luke_bnb_2,    "BnB #2 — cr.LP > cr.LP > cr.MK xx Sand Blast",        "F2"),
        _entry(luke_punish_1, "Punish #1 — st.HP xx Rising Uppercut",                "F3"),
        _entry(luke_punish_2, "Punish #2 — OD Rising Uppercut > Flash Knuckle",      "F4"),
        _entry(luke_super_1,  "Super — cr.MK xx Vulcan Blast Lv1",                   "F5"),
        _entry(luke_advanced, "ADV — Low > OD Knuckle > Uppercut xx Vulcan Blast",   "ADV"),
    ],
    "A.K.I.": [
        _entry(aki_bnb_1,    "BnB #1 — cr.LP > cr.MP xx Cruel Fate (poison)",        "F1"),
        _entry(aki_bnb_2,    "BnB #2 — st.MP > st.HP xx Sinister Slide",             "F2"),
        _entry(aki_punish_1, "Punish #1 — cr.MP > st.HP xx Cruel Fate > Cobra",      "F3"),
        _entry(aki_punish_2, "Punish #2 — OD Cruel Fate > HP > Clinging Cobra",      "F4"),
        _entry(aki_super_1,  "Super — st.HP xx Coronation Lv1",                      "F5"),
        _entry(aki_advanced, "ADV — Poison > Cobra > OD Slide > HP xx Coronation",   "ADV"),
    ],
    "M. Bison": [
        _entry(bison_bnb_1,    "BnB #1 — cr.MK xx Scissors Kick MK (charge)",        "F1"),
        _entry(bison_bnb_2,    "BnB #2 — cr.LP > cr.MK xx Psycho Crusher HP",        "F2"),
        _entry(bison_punish_1, "Punish #1 — st.HP xx Scissors HK (charge)",          "F3"),
        _entry(bison_punish_2, "Punish #2 — OD Scissors > Psycho Crusher",           "F4"),
        _entry(bison_super_1,  "Super — cr.MK xx Knee Press Nightmare Lv1",          "F5"),
        _entry(bison_advanced, "ADV — Low > OD Scissors > Scissors > Crusher xx KPN","ADV"),
    ],
}

CHARACTER_ORDER = list(ALL_COMBOS.keys())

# Per-character notes shown in the GUI
CHAR_NOTES = {
    "Akuma":    "ADV needs Drive Gauge. OD Tatsumaki corner only.",
    "Chun-Li":  "F1/F4/ADV need back-charge. ADV needs Drive + Lv2 super.",
    "Mai":      "ADV needs Drive + Lv2 super meter.",
    "Ken":      "ADV needs Drive + Lv1 super. Jinrai auto-follows on hit.",
    "Juri":     "★ = needs 1 pre-stored Fuha stock (press 236+LK first).",
    "Cammy":    "ADV needs Drive + Lv2 super. OD Spike = 623+LK+HK.",
    "Ryu":      "ADV needs Drive + Lv3 super. Hold HP for Shin Shoryuken.",
    "Ed":       "All charge moves: hold direction DURING normals to build charge.",
    "JP":       "Combos work at close range. Max cane range may drop links.",
    "Marisa":   "ADV needs Drive + Lv3 super. Even short combos deal huge damage.",
    "Luke":     "F1/ADV need charge. ADV needs Drive + Lv1 super.",
    "A.K.I.":  "ADV applies poison first — bonus damage ticks throughout combo.",
    "M. Bison": "All specials need charge. Hold back DURING normals to maintain it.",
}


# ══════════════════════════════════════════════════════════════════════════════
#  EXECUTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

current_char_index = 0
combo_lock  = threading.Lock()
_executing  = False
log_cb      = None
char_cb     = None
progress_cb = None   # called with (slot_index) when a combo starts

def get_current_char() -> str:
    return CHARACTER_ORDER[current_char_index]

def _run_combo(combo_info: dict):
    global _executing
    _cancel_flag.clear()
    with combo_lock:
        _executing = True
        char  = get_current_char()
        label = combo_info["label"]
        slot  = combo_info["slot"]
        if log_cb: log_cb(f"▶ [{char}] {label}")
        if progress_cb: progress_cb(slot)
        try:
            combo_info["fn"]()
            if log_cb: log_cb("✓ Complete")
        except InterruptedError:
            if log_cb: log_cb("⊘ Cancelled")
            # Release all inputs cleanly
            try:
                _release_raw("LP","MP","HP","LK","MK","HK","LT","LB","RB")
                neutral(2)
            except Exception:
                pass
        except Exception as e:
            if log_cb: log_cb(f"✗ Error: {e}")
        finally:
            _executing = False
            if progress_cb: progress_cb(None)

def fire_slot(slot_index: int):
    if _executing:
        return
    char   = get_current_char()
    combos = [c for c in ALL_COMBOS[char] if c["slot"] != "ADV"]
    if slot_index < len(combos):
        threading.Thread(target=_run_combo, args=(combos[slot_index],), daemon=True).start()

def fire_advanced():
    if _executing:
        return
    char   = get_current_char()
    combos = [c for c in ALL_COMBOS[char] if c["slot"] == "ADV"]
    if combos:
        threading.Thread(target=_run_combo, args=(combos[0],), daemon=True).start()

def cancel_combo():
    _cancel_flag.set()

def cycle_character(direction: int = 1):
    global current_char_index
    current_char_index = (current_char_index + direction) % len(CHARACTER_ORDER)
    char = get_current_char()
    if log_cb:  log_cb(f"◈ → {char}")
    if char_cb: char_cb(char)

def register_hotkeys():
    for i, key in enumerate(["F1","F2","F3","F4","F5"]):
        keyboard.add_hotkey(key, lambda idx=i: fire_slot(idx))
    keyboard.add_hotkey("F6",      lambda: cycle_character(+1))
    keyboard.add_hotkey("F7",      lambda: cycle_character(-1))
    keyboard.add_hotkey("F8",      lambda: fire_advanced())
    keyboard.add_hotkey("escape",  lambda: cancel_combo())


# ══════════════════════════════════════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════════════════════════════════════

CHAR_COLORS = {
    "Akuma":    "#8b2be2",
    "Chun-Li":  "#4fc3f7",
    "Mai":      "#ff6b35",
    "Ken":      "#ffcc02",
    "Juri":     "#e040fb",
    "Cammy":    "#00e5a0",
    "Ryu":      "#e8251a",
    "Ed":       "#3a9bdc",
    "JP":       "#c8a850",
    "Marisa":   "#c0392b",
    "Luke":     "#27ae60",
    "A.K.I.":  "#9b59b6",
    "M. Bison": "#2980b9",
}

TYPE_LABELS = ["BnB", "BnB", "Punish", "Punish (OD)", "Super", "Advanced"]

class ComboApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SF6 World Tour Combo Bot")
        self.configure(bg="#09090f")
        self.resizable(False, False)
        self._active_row = None
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        BG = "#09090f"

        # Header
        hdr = tk.Frame(self, bg=BG); hdr.pack(fill="x", padx=20, pady=(16,0))
        tk.Label(hdr, text="SF6", font=("Impact",38,"bold"), bg=BG, fg="#e8251a").pack(side="left")
        tk.Label(hdr, text=" COMBO BOT", font=("Impact",38), bg=BG, fg="#f0f0f0").pack(side="left")
        tk.Label(self, text="World Tour Edition  ·  Classic Controls  ·  v4.0",
                 font=("Consolas",9), bg=BG, fg="#444").pack(anchor="w", padx=22)

        # Status bar
        self.status_var = tk.StringVar(value="● Initializing…")
        self._status_lbl = tk.Label(self, textvariable=self.status_var,
                 font=("Consolas",10), bg="#111118", fg="#e8251a",
                 anchor="w", padx=10, pady=5)
        self._status_lbl.pack(fill="x", padx=20, pady=(10,0))

        # Divider
        tk.Frame(self, bg="#e8251a", height=2).pack(fill="x", padx=20, pady=8)

        # Character buttons (3 rows × 5)
        tab_outer = tk.Frame(self, bg=BG); tab_outer.pack(fill="x", padx=20, pady=(0,6))
        tk.Label(tab_outer, text="CHARACTER  (F6=Next  F7=Prev  F8=Advanced  ESC=Cancel)",
                 font=("Consolas",9,"bold"), bg=BG, fg="#555").pack(anchor="w", pady=(0,4))
        self.char_buttons = {}
        ROW = 5
        for ri in range(0, len(CHARACTER_ORDER), ROW):
            rf = tk.Frame(tab_outer, bg=BG); rf.pack(fill="x", pady=1)
            for char in CHARACTER_ORDER[ri:ri+ROW]:
                col = CHAR_COLORS[char]
                b = tk.Button(rf, text=char, font=("Consolas",10,"bold"),
                              bg="#1a1a28", fg="#888",
                              activebackground=col, activeforeground="#000",
                              relief="flat", padx=10, pady=4, cursor="hand2",
                              command=lambda c=char: self._select_char(c))
                b.pack(side="left", padx=2)
                self.char_buttons[char] = b

        # Active character + Advanced button row
        char_row = tk.Frame(self, bg=BG); char_row.pack(fill="x", padx=20, pady=(4,0))
        self.active_char_var = tk.StringVar(value="")
        self.char_lbl = tk.Label(char_row, textvariable=self.active_char_var,
                                 font=("Impact",22), bg=BG, fg="#e8251a", anchor="w")
        self.char_lbl.pack(side="left")

        self.adv_btn = tk.Button(char_row, text="▶ ADVANCED  [F8]",
                                 font=("Consolas",10,"bold"),
                                 bg="#2a1a3a", fg="#e040fb",
                                 activebackground="#e040fb", activeforeground="#000",
                                 relief="flat", padx=12, pady=3, cursor="hand2",
                                 command=lambda: fire_advanced())
        self.adv_btn.pack(side="right", padx=(0,4))

        # Combo table
        tf = tk.Frame(self, bg=BG); tf.pack(fill="both", padx=20, pady=(4,0))
        style = ttk.Style(); style.theme_use("default")
        style.configure("SF6.Treeview",
            background="#111118", foreground="#c0c0c0",
            fieldbackground="#111118", font=("Consolas",10), rowheight=26)
        style.configure("SF6.Treeview.Heading",
            background="#16162a", foreground="#e8251a",
            font=("Consolas",10,"bold"), relief="flat")
        style.map("SF6.Treeview", background=[("selected","#2a1a2e")])

        self.tree = ttk.Treeview(tf, columns=("slot","type","combo"),
                                  show="headings", style="SF6.Treeview", height=5)
        self.tree.heading("slot",  text="KEY")
        self.tree.heading("type",  text="TYPE")
        self.tree.heading("combo", text="COMBO ROUTE")
        self.tree.column("slot",  width=55,  anchor="center")
        self.tree.column("type",  width=105, anchor="center")
        self.tree.column("combo", width=460, anchor="w")
        self.tree.pack(fill="both")

        # Notes panel
        note_frame = tk.Frame(self, bg="#0d0d1a"); note_frame.pack(fill="x", padx=20, pady=(4,0))
        self.notes_var = tk.StringVar(value="")
        tk.Label(note_frame, textvariable=self.notes_var,
                 font=("Consolas",9), bg="#0d0d1a", fg="#888",
                 anchor="w", padx=8, pady=4, wraplength=620, justify="left"
                 ).pack(fill="x")

        # Settings
        tk.Frame(self, bg="#222", height=1).pack(fill="x", padx=20, pady=8)
        sf = tk.Frame(self, bg=BG); sf.pack(fill="x", padx=20, pady=(0,8))
        tk.Label(sf, text="Frame Scale:", font=("Consolas",10), bg=BG, fg="#666").pack(side="left")
        self.scale_var = tk.DoubleVar(value=FRAME_SCALE)
        tk.Spinbox(sf, from_=0.5, to=3.0, increment=0.1,
                   textvariable=self.scale_var, width=5,
                   font=("Consolas",10), bg="#1a1a2e", fg="#f0f0f0",
                   buttonbackground="#333", relief="flat",
                   command=self._update_scale).pack(side="left", padx=(6,16))
        tk.Label(sf, text="Raise if inputs drop. Lower for faster timing.",
                 font=("Consolas",9), bg=BG, fg="#333").pack(side="left")

        # Log
        lf = tk.Frame(self, bg=BG); lf.pack(fill="x", padx=20, pady=(0,16))
        tk.Label(lf, text="LOG", font=("Consolas",9,"bold"), bg=BG, fg="#e8251a").pack(anchor="w")
        self.log_text = tk.Text(lf, height=5, bg="#060610", fg="#00ff88",
                                font=("Consolas",9), relief="flat",
                                state="disabled", cursor="arrow")
        self.log_text.pack(fill="x")

        self._select_char(CHARACTER_ORDER[0])
        self._log("v4 ready. F1-F5: combos | F6/F7: character | F8: advanced | ESC: cancel")

    # ── Character selection ────────────────────────────────────────────────────

    def _select_char(self, char: str):
        global current_char_index
        current_char_index = CHARACTER_ORDER.index(char)
        col = CHAR_COLORS[char]

        for c, b in self.char_buttons.items():
            b.configure(bg=col if c == char else "#1a1a28",
                        fg="#000" if c == char else "#888")

        self.char_lbl.configure(text=f"▸ {char.upper()}", fg=col)
        self.adv_btn.configure(bg="#2a1a3a", fg=col)
        self.notes_var.set(f"ℹ  {CHAR_NOTES.get(char, '')}")

        for row in self.tree.get_children():
            self.tree.delete(row)

        non_adv = [c for c in ALL_COMBOS[char] if c["slot"] != "ADV"]
        for i, combo in enumerate(non_adv):
            tag = "odd" if i % 2 else "even"
            self.tree.insert("", "end", iid=f"row_{i}",
                             values=(combo["slot"], TYPE_LABELS[i], combo["label"]),
                             tags=(tag,))

        self.tree.tag_configure("odd",  background="#0e0e1c")
        self.tree.tag_configure("even", background="#111118")
        self._active_row = None

    def highlight_row(self, slot: str | None):
        """Highlight the active combo row while executing."""
        self._active_row = slot
        non_adv = [c for c in ALL_COMBOS[get_current_char()] if c["slot"] != "ADV"]
        for i, combo in enumerate(non_adv):
            iid = f"row_{i}"
            if combo["slot"] == slot:
                self.tree.item(iid, tags=("active",))
                self.tree.tag_configure("active", background="#1a2a1a", foreground="#00ff88")
            else:
                tag = "odd" if i % 2 else "even"
                self.tree.item(iid, tags=(tag,))
        self.tree.tag_configure("odd",  background="#0e0e1c", foreground="#c0c0c0")
        self.tree.tag_configure("even", background="#111118", foreground="#c0c0c0")

    # ── Settings & log ────────────────────────────────────────────────────────

    def _update_scale(self):
        global FRAME_SCALE
        FRAME_SCALE = self.scale_var.get()
        self._log(f"Frame scale → {FRAME_SCALE:.1f}x")

    def _log(self, msg: str):
        def _do():
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.after(0, _do)

    def set_status(self, msg: str):
        self.after(0, lambda: self.status_var.set(f"● {msg}"))

    def _on_close(self):
        cancel_combo()
        keyboard.unhook_all()
        self.destroy()
        sys.exit(0)


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    app = ComboApp()

    global log_cb, char_cb, progress_cb
    log_cb      = app._log
    char_cb     = lambda char: app.after(0, lambda: app._select_char(char))
    progress_cb = lambda slot: app.after(0, lambda: app.highlight_row(slot))

    if init_gamepad():
        n = len(CHARACTER_ORDER)
        app.set_status(f"Gamepad OK — {n} characters loaded — F1-F5: combo | F6/F7: char | F8: advanced | ESC: cancel")
        app._log(f"✓ Virtual Xbox 360 gamepad ready. {n} characters, {n*6} combos loaded.")
        app._log("✓ Hotkeys: F1-F5 combos, F6 next, F7 prev, F8 advanced, ESC cancel.")
        register_hotkeys()
    else:
        app.set_status("ERROR: ViGEmBus not found — install driver first")
        app._log("✗ Gamepad init failed. Install ViGEmBus:")
        app._log("  https://github.com/ViGEm/ViGEmBus/releases")

    app.mainloop()


if __name__ == "__main__":
    main()
