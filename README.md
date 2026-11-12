# FT-857D Power Control

**New here? See [INSTALL.md](INSTALL.md) for step-by-step install directions.**

A small desktop program for Yaesu FT-857D owners. It shows the radio's current RF power setting for the band you are on (HF, 6m, 2m, 70cm) and lets you pick a preset (for example 5 W for digital modes) and apply it, without digging through Menu 075.

It talks to the radio through [Flrig](http://www.w1hkj.com/), so Flrig must be running and connected to your radio.

## READ THIS FIRST: safety warnings

- **The Apply button writes directly to the radio's EEPROM.** This uses an undocumented CAT command (0xBC). It is not an official Yaesu feature.
- **This was developed and tested on one radio** (one FT-857D, Flrig 2.0.04, Linux Mint). It has not been tested on other radios, firmware, or setups. A write that goes wrong could change radio settings.
- **Back up your radio first.** Save your radio's memory and settings with CHIRP (or another tool) before you use Apply for the first time.
- **Never use it while transmitting.** The program checks and refuses if the radio or Flrig reports transmit, but do not rely on that alone.
- **The program sets 5 W automatically when it starts**, on the band the radio is on at that moment, without asking first. If the band is already at 5 W, nothing is written. To change this, edit `STARTUP_WATTS = 5` near the top of `ft857_power_control.py`. Set it to another wattage, or to `None` to turn it off.
- After each change, the program reads the value back twice to confirm it, and checks that the other power settings did not change. If it reports a problem, check **Menu 075** on the radio.
- The radio does not acknowledge the write command in Flrig ("No response"). That is normal here; the read-back is the proof.
- **No warranty.** You are responsible for your own radio. See the LICENSE.

## What you need

- A Yaesu FT-857D connected to your computer, with Flrig set up and working
- Flrig's XML-RPC server on its default address, `127.0.0.1:12345`
- Python 3 with Tkinter
  - Debian, Ubuntu, Linux Mint: `sudo apt install python3-tk`

## How to run it

1. Start Flrig and make sure it shows the radio's frequency.
2. In a terminal, in the folder with the program, run:

   `python3 ft857_power_control.py`

3. The window shows the frequency, mode, band, and current power. A few seconds after it opens, it sets the current band to 5 W (see the safety warnings above).
4. To use a different power, pick a preset, click **Apply**, and confirm.

Buttons: **Refresh** re-reads the radio. **Settings** edits your preset lists (saved in `~/.ft857_power_presets.json`). **Apply** writes the selected power.

A log of everything sent to the radio is kept in `~/ft857_write_log.txt`.

### Optional window icon

Put a file named `ft857-power.png` in the same folder as the program (or in `~/.local/share/icons/`). If it is not there, the program runs without an icon.

## Limits and notes

- Power ranges: HF and 6m 5-100 W, 2m 5-50 W, 70cm 2-20 W.
- **The HF band list is the US amateur allocations only.** If you are outside the US, the band detection in the program (`HF_BANDS`) will need changing for your region.
- The program only works on the band the radio is currently tuned to.
- Not affiliated with Yaesu, Flrig, or anyone else.
