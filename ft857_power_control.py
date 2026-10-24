#!/usr/bin/env python3
"""FT-857D RF power control (unofficial, community tool).

Shows and changes the Yaesu FT-857D RF output power setting for the band the
radio is currently on, using Flrig's XML-RPC interface (127.0.0.1:12345).

WARNING: Applying a change writes directly to the radio's EEPROM. Read the
README first. Use at your own risk. Never use while transmitting.
"""
import datetime
import json
import re
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import xmlrpc.client

URL = "http://127.0.0.1:12345"
CONFIG = Path.home() / ".ft857_power_presets.json"
LOG = Path.home() / "ft857_write_log.txt"
HEX1 = re.compile(r"^[0-9A-Fa-f]{2}$")

DEFAULTS = {
    "HF": [5, 15, 20, 30, 50, 95],
    "6m": [5, 15, 20, 30, 50, 95],
    "2m": [5, 10, 15, 20, 30, 50],
    "70cm": [2, 5, 10, 15, 20]
}

LIMITS = {"HF": 100, "6m": 100, "2m": 50, "70cm": 20}

# band: (EEPROM address, byte index, minimum watts, maximum watts)
ADDRESSES = {
    "HF":   (0x009A, 1, 5, 100),
    "6m":   (0x00AA, 0, 5, 100),
    "2m":   (0x00AA, 1, 5, 50),
    "70cm": (0x00AC, 0, 2, 20),
}
STATE_WORDS = (0x009A, 0x00AA, 0x00AC)

# US amateur transmitting allocations used for this first version.
HF_BANDS = [
    (1.8, 2.0), (3.5, 4.0), (5.3305, 5.4065),
    (7.0, 7.3), (10.1, 10.15), (14.0, 14.35),
    (18.068, 18.168), (21.0, 21.45),
    (24.89, 24.99), (28.0, 29.7)
]


class Refused(Exception):
    """Something looked wrong BEFORE any write; nothing was changed."""


class VerifyFailed(Exception):
    """A write was sent but the read-back did not confirm it."""


def detect_band(mhz):
    if any(lo <= mhz <= hi for lo, hi in HF_BANDS):
        return "HF"
    if 50 <= mhz <= 54:
        return "6m"
    if 144 <= mhz <= 148:
        return "2m"
    if 420 <= mhz <= 450:
        return "70cm"
    return None


def log(msg):
    try:
        with open(LOG, "a") as f:
            f.write(f"{datetime.datetime.now().isoformat()} GUI {msg}\n")
    except OSError:
        pass


def encode_power(watts):
    return watts if watts < 20 else watts + 128


def decode_power(raw):
    return raw - 128 if raw >= 128 else raw


def cat(radio, cmd):
    r = radio.rig.cat_string(cmd).strip()
    log(f"SENT {cmd} -> {r!r}")
    return r


def check_idle(radio):
    if radio.rig.get_ptt() != 0:
        raise Refused("Flrig PTT is active")
    r = cat(radio, "x00 x00 x00 x00 xF7")
    if not HEX1.match(r):
        raise Refused(f"Radio TX status unreadable ({r!r})")
    if not int(r, 16) & 0x80:
        raise Refused("Radio is transmitting")


def read_word(radio, addr):
    r = cat(radio, f"x{addr >> 8:02X} x{addr & 0xFF:02X} x00 x00 xBB")
    parts = r.split()
    if len(parts) != 2 or not all(HEX1.match(p) for p in parts):
        raise Refused(f"Bad EEPROM response at {addr:04X}: {r!r}")
    return [int(p, 16) for p in parts]


def do_apply(band, watts):
    address, index, low, high = ADDRESSES[band]
    if not low <= watts <= high:
        raise Refused(
            f"{watts} W is outside the {band} range of {low}-{high} W"
        )

    radio = xmlrpc.client.ServerProxy(URL)
    log(f"===== APPLY REQUEST: {band} {watts} W =====")
    check_idle(radio)

    freq = int(radio.rig.get_vfo())
    if detect_band(freq / 1_000_000) != band:
        raise Refused("Radio is no longer on the displayed band. "
                      "Press Refresh.")

    before = {a: read_word(radio, a) for a in STATE_WORDS}
    word = before[address]
    raw = word[index]
    current = decode_power(raw)
    if not low <= current <= high or encode_power(current) != raw:
        raise Refused(f"Current power byte {raw:02X} looks unexpected")
    if current == watts:
        return f"{band} is already {watts} W - nothing written"

    if not messagebox.askokcancel(
            "Confirm power change",
            f"Change {band} RF power from {current} W to {watts} W?"):
        return "Cancelled - nothing written"

    check_idle(radio)
    if int(radio.rig.get_vfo()) != freq:
        raise Refused("Radio frequency changed")
    if read_word(radio, address) != word:
        raise Refused("Radio settings changed before the write")

    new = word[:]
    new[index] = encode_power(watts)
    cmd = (f"x{address >> 8:02X} x{address & 0xFF:02X} "
           f"x{new[0]:02X} x{new[1]:02X} xBC")
    log(f"MODE: change {band} {current} W -> {watts} W; "
        f"bytes {word[0]:02X} {word[1]:02X} -> {new[0]:02X} {new[1]:02X}")

    try:
        response = radio.rig.cat_string(cmd)
        log(f"WRITE SENT {cmd} -> {response!r}")
    except Exception as error:
        log(f"WRITE SENT {cmd} -> exception {error!r}")

    try:
        time.sleep(0.5)
        probe = cat(radio, "x00 x00 x00 x00 xF7")
        if not HEX1.match(probe):
            log(f"NOTE: after-write status probe was not one byte: {probe!r}")
            time.sleep(0.5)
            cat(radio, "x00 x00 x00 x00 xF7")
        time.sleep(0.3)
        r1 = read_word(radio, address)
        time.sleep(0.3)
        r2 = read_word(radio, address)
        others = {a: read_word(radio, a)
                  for a in STATE_WORDS if a != address}
    except Exception as error:
        raise VerifyFailed(
            f"A write was sent but the read-back failed ({error}). "
            f"Original bytes were {word[0]:02X} {word[1]:02X}."
        )

    unchanged = all(others[a] == before[a] for a in others)
    if r1 == new and r2 == new and unchanged:
        log(f"SUCCESS: {band} now {watts} W, bytes {r1[0]:02X} {r1[1]:02X}, "
            "confirmed on two reads; other settings unchanged")
        return f"{band} power set to {watts} W (verified)"

    log(f"PROBLEM: expected {new[0]:02X} {new[1]:02X}, "
        f"read {r1[0]:02X} {r1[1]:02X} then {r2[0]:02X} {r2[1]:02X}; "
        f"other words before {before}, after {others}")
    raise VerifyFailed(
        f"Read-back does not match. Expected {new[0]:02X} {new[1]:02X}, "
        f"read {r1[0]:02X} {r1[1]:02X} then {r2[0]:02X} {r2[1]:02X}. "
        f"Original bytes were {word[0]:02X} {word[1]:02X}."
    )


def load_presets():
    try:
        data = json.loads(CONFIG.read_text())
        for band in DEFAULTS:
            values = data[band]
            if (not isinstance(values, list) or not values
                    or len(values) > 12
                    or any(type(v) is not int or not 1 <= v <= LIMITS[band]
                           for v in values)):
                raise ValueError("Invalid presets")
        return data
    except (OSError, ValueError, KeyError, TypeError):
        return {k: v[:] for k, v in DEFAULTS.items()}


presets = load_presets()
root = tk.Tk()
root.title("FT-857D Power Control (Apply enabled)")
# Optional window icon: looks next to this script first, then in the
# user's icon folder. If neither exists the program simply runs without one.
for _icon_path in (Path(__file__).resolve().with_name("ft857-power.png"),
                   Path.home() / ".local/share/icons/ft857-power.png"):
    try:
        _icon = tk.PhotoImage(file=str(_icon_path))
        root.iconphoto(True, _icon)
        break
    except Exception:
        continue
root.geometry("420x430")

band_var = tk.StringVar(value="Unknown")
freq_var = tk.StringVar(value="Frequency: --")
mode_var = tk.StringVar(value="Mode: --")
power_var = tk.StringVar(value="-- W")
status_var = tk.StringVar(value="Waiting for radio")
selected_var = tk.IntVar(value=0)

ttk.Label(root, text="FT-857D RF POWER",
          font=("Arial", 16, "bold")).pack(pady=(15, 8))
ttk.Label(root, textvariable=freq_var).pack()
ttk.Label(root, textvariable=mode_var).pack()
ttk.Label(root, textvariable=band_var).pack(pady=5)
ttk.Label(root, textvariable=power_var,
          font=("Arial", 28, "bold")).pack(pady=10)

ttk.Label(root, text="Select a power preset:").pack()

buttons_frame = ttk.Frame(root)
buttons_frame.pack(pady=8)


def show_buttons(band):
    for widget in buttons_frame.winfo_children():
        widget.destroy()
    selected_var.set(0)

    if band is None:
        return

    for i, watts in enumerate(presets[band]):
        ttk.Radiobutton(
            buttons_frame,
            text=f"{watts} W",
            variable=selected_var,
            value=watts
        ).grid(row=i // 3, column=i % 3, padx=12, pady=5,
               sticky="w")


current_band = None


def refresh():
    global current_band
    try:
        radio = xmlrpc.client.ServerProxy(
            URL, transport=xmlrpc.client.Transport()
        )
        mhz = int(radio.rig.get_vfo()) / 1_000_000
        mode = str(radio.rig.get_mode())
        band = detect_band(mhz)

        freq_var.set(f"Frequency: {mhz:.6f} MHz")
        mode_var.set(f"Mode: {mode}")

        if band:
            band_var.set(
                f"Band: {band}  |  Maximum: {LIMITS[band]} W"
            )
        else:
            band_var.set("Band: Unsupported frequency")

        if band != current_band:
            current_band = band
            show_buttons(band)

        if band:
            address, index = ADDRESSES[band][:2]
            command = (
                f"x{address >> 8:02X} "
                f"x{address & 0xFF:02X} "
                "x00 x00 xBB"
            )

            response = radio.rig.cat_string(command)
            parts = response.split()

            if len(parts) != 2 or any(
                re.fullmatch(r"[0-9A-Fa-f]{2}", p) is None
                for p in parts
            ):
                raise ValueError("Invalid EEPROM response")

            raw = int(parts[index], 16)
            watts = decode_power(raw)

            if not 1 <= watts <= LIMITS[band]:
                raise ValueError(
                    f"Unexpected power value: 0x{raw:02X}"
                )

            power_var.set(f"{watts} W")
        else:
            power_var.set("-- W")

        status_var.set("Ready - choose a preset and click Apply")

    except Exception as error:
        current_band = None
        show_buttons(None)
        power_var.set("-- W")
        band_var.set("Radio unavailable")
        status_var.set(f"Error: {error}")


def apply_power():
    watts = selected_var.get()
    if not watts:
        messagebox.showinfo("Apply", "Select a power preset first.")
        return
    if current_band is None:
        messagebox.showerror("Apply",
                             "No supported band detected. Press Refresh.")
        return

    band = current_band
    try:
        message = do_apply(band, watts)
    except Refused as error:
        log(f"STOPPED (nothing written): {error}")
        status_var.set(f"NOT CHANGED: {error}")
        messagebox.showwarning("Not changed", str(error))
        return
    except VerifyFailed as error:
        log(f"VERIFY FAILED: {error}")
        refresh()
        status_var.set(f"WARNING: {error}")
        messagebox.showerror("Could not confirm the change", str(error))
        return
    except Exception as error:
        log(f"UNEXPECTED ERROR: {error!r}")
        refresh()
        status_var.set(f"Error: {error}. Check the radio's Menu 075.")
        messagebox.showerror("Unexpected error",
                             f"{error}\n\nPlease check Menu 075 "
                             "on the radio.")
        return

    refresh()
    status_var.set(message)


def configure():
    window = tk.Toplevel(root)
    window.title("Configure Power Presets")
    window.geometry("380x310")
    window.transient(root)
    window.grab_set()

    entries = {}

    ttk.Label(
        window,
        text="Enter preset wattages separated by commas:"
    ).pack(pady=12)

    for band in DEFAULTS:
        frame = ttk.Frame(window)
        frame.pack(fill="x", padx=15, pady=6)
        ttk.Label(frame, text=f"{band} (max {LIMITS[band]} W)",
                  width=16).pack(side="left")
        entry = ttk.Entry(frame, width=28)
        entry.insert(0, ", ".join(map(str, presets[band])))
        entry.pack(side="left", fill="x", expand=True)
        entries[band] = entry

    def save():
        global presets
        try:
            updated = {}
            for band, entry in entries.items():
                values = [
                    int(x.strip())
                    for x in entry.get().split(",")
                ]
                if (not values or len(values) > 12
                        or len(set(values)) != len(values)
                        or any(not 1 <= v <= LIMITS[band]
                               for v in values)):
                    raise ValueError(
                        f"Invalid power presets for {band}"
                    )
                updated[band] = sorted(values)

            CONFIG.write_text(json.dumps(updated, indent=2))
            presets = updated
            show_buttons(current_band)
            window.destroy()

        except (ValueError, OSError) as error:
            messagebox.showerror("Preset Error", str(error),
                                 parent=window)

    ttk.Button(window, text="Save Presets",
               command=save).pack(pady=15)


controls = ttk.Frame(root)
controls.pack(pady=12)

ttk.Button(controls, text="Refresh",
           command=refresh).pack(side="left", padx=5)
ttk.Button(controls, text="Settings",
           command=configure).pack(side="left", padx=5)
ttk.Button(controls, text="Apply",
           command=apply_power).pack(side="left", padx=5)

ttk.Label(root, textvariable=status_var,
          wraplength=390).pack(pady=5)

refresh()
root.mainloop()
