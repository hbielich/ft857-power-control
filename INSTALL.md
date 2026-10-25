# Installing FT-857D Power Control

These directions are for people who are not programmers. Take them one step at a time. They were written and tested on Linux Mint. Other Linux systems based on Ubuntu or Debian work the same way. Windows and Mac may work, but have not been tested.

**Please read the safety warnings in the README before you use the Apply button.** Apply writes to the radio's memory. Back up your radio with CHIRP first.

## Before you start

You need:
- A Yaesu FT-857D connected to your computer, turned on
- Flrig installed and working, showing your radio's frequency
- Python 3 (already included on Linux Mint and most Linux systems)

## Step 1: Download the program

1. Go to the program's page on GitHub (the repository named **ft857-power-control**).
2. Click the green **Code** button near the top right of the file list.
3. Click **Download ZIP**.

Your browser saves a file named `ft857-power-control-main.zip`, usually in your **Downloads** folder.

## Step 2: Unpack the ZIP

1. Open your **Downloads** folder.
2. Right-click `ft857-power-control-main.zip` and choose **Extract Here** (or **Extract**).
3. A folder named `ft857-power-control-main` appears. Open it.

You should see four files: `LICENSE`, `README.md`, `ft857-power.png`, and `ft857_power_control.py`.

## Step 3: Open a terminal in that folder

1. With the folder open, right-click an empty spot in the window (not on a file).
2. Choose **Open in Terminal**.

A window with text and a blinking cursor opens. The text before the cursor should end with `ft857-power-control-main`.

If your file manager has no "Open in Terminal" choice, open a terminal from your menu and type `cd ~/Downloads/ft857-power-control-main` followed by Enter.

## Step 4: Check that Tkinter is installed

Tkinter is the part of Python that draws the program's window. In the terminal, type this and press Enter:

`python3 -c "import tkinter; print('tkinter OK')"`

- If you see `tkinter OK`, go on to Step 5.
- If you see `No module named tkinter`, install it. On Linux Mint, Ubuntu, and Debian, type:

  `sudo apt install python3-tk`

  Enter your password when asked (nothing shows while you type; that is normal). Type `Y` and press Enter when it asks to continue. Then run the check line again. You should now see `tkinter OK`.

  On Fedora, the package is named `python3-tkinter`, installed with `sudo dnf install python3-tkinter`.

## Step 5: Start Flrig

1. Turn on the radio.
2. Start Flrig and make sure it shows your radio's frequency, matching the radio.

The program talks to the radio through Flrig. It expects Flrig's built-in server at its standard address, `127.0.0.1:12345`.

## Step 6: Start the power program

In the terminal, type this and press Enter:

`python3 ft857_power_control.py`

A window titled **FT-857D Power Control** opens. It should show your frequency, mode, band, and the radio's current RF power for that band.

## Step 7: Check the reading

Compare the large power number in the program with **Menu 075** on the radio for the band you are on. They should match. Do not use Apply until they do.

## Step 8: Try it

1. Make sure nothing is transmitting.
2. Write down the current power number.
3. Click a different preset, then click **Apply**.
4. Check the wattages in the confirmation box and click **OK**.
5. The bottom message should say the power was set and **verified**. Check Menu 075 on the radio.
6. Set the power back to your original number the same way.

## Changing the presets

Click **Settings**, edit the wattages for each band (separated by commas), and click **Save Presets**. Each band can have up to 12 presets. The program will not accept numbers above the band's maximum.

## If something goes wrong

- **"Radio unavailable" in the window:** Flrig is not running, or the radio is not connected in Flrig, or Flrig's server is not at `127.0.0.1:12345`. Start Flrig and click **Refresh**.
- **"NOT CHANGED" message:** The program stopped before writing anything, because something looked wrong (for example, the radio was transmitting, or you changed bands). Click **Refresh** and try again.
- **"Could not confirm the change":** A write was sent but the program could not verify it. Check **Menu 075** on the radio and set it by hand if needed.
- **The window does not open and you see an error about `tkinter`:** Repeat Step 4.

A record of everything sent to the radio is kept in a file named `ft857_write_log.txt` in your home folder. If you report a problem, that file helps.
