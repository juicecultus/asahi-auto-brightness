# Asahi Auto-Brightness

Automatic display brightness based on the ambient light sensor (ALS) for Apple Silicon laptops running [Asahi Linux](https://asahilinux.org/).

Works with the **VD6286** ALS sensor found in M2 MacBook Air (13" and 15") and other Apple Silicon laptops, driven by the `aop_als` kernel module from the [Asahi fairydust](https://github.com/AsahiLinux/linux/tree/fairydust) kernel.

## How It Works

```
VD6286 sensor → aop_als kernel module → IIO sysfs
    → auto-brightness daemon (direct sysfs read/write)
    → periodic KDE slider sync via D-Bus
```

The daemon writes directly to the backlight sysfs interface, bypassing the desktop environment entirely. This prevents OSD (On-Screen Display) popups during automatic adjustments. It periodically syncs KDE's brightness slider via D-Bus after brightness stabilizes.

Key features (same architecture as [macbook-ambient-sensor](https://github.com/juicecultus/macbook-ambient-sensor)):
- **No OSD popups** — direct sysfs writes bypass KDE/GNOME entirely
- **Imperceptible transitions** — one small brightness step per poll cycle (2 units / 0.5s)
- **Manual override** — respects user slider/key changes until ambient light shifts by ≥50% (or ≥5 lux absolute in low light)
- **Periodic KDE sync** — slider stays accurate after brightness stabilizes (uses `SuppressIndicator` flag to avoid OSD)
- **Minimum brightness floor** — prevents black screen

## Prerequisites

- **Kernel**: Asahi fairydust branch with `CONFIG_IIO_AOP_SENSOR_ALS=m`
- **Firmware**: `apple/aop-als-cal.bin` in `/lib/firmware/` (see [Extracting Calibration](#extracting-calibration-data))
- **Packages**: `python3-dbus` (for optional KDE slider sync)
- **Backlight permissions**: udev rule for writable sysfs (included)

## Installation

### 1. Extract ALS calibration from macOS

Boot into macOS and capture the ioreg dump:

```bash
ioreg -l -a > ioreg-full.xml
```

Copy `ioreg-full.xml` to your Linux system, then extract the calibration:

```bash
python3 extract-als-cal.py ioreg-full.xml
sudo cp aop-als-cal.bin /lib/firmware/apple/aop-als-cal.bin
sudo dracut --force --kver $(uname -r)
```

### 2. Install the auto-brightness daemon

```bash
# Allow non-root backlight writes (required)
sudo cp 99-backlight.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules

# Install the script
mkdir -p ~/.local/bin
cp auto-brightness ~/.local/bin/auto-brightness
chmod +x ~/.local/bin/auto-brightness

# Install the systemd user service
mkdir -p ~/.config/systemd/user
cp auto-brightness.service ~/.config/systemd/user/auto-brightness.service
systemctl --user daemon-reload
systemctl --user enable --now auto-brightness.service
```

### 3. Reboot

After reboot, verify:

```bash
# ALS sensor is active
cat /sys/bus/iio/devices/iio:device1/in_illuminance_input

# Daemon is running
systemctl --user status auto-brightness

# Backlight is writable
ls -l /sys/class/backlight/apple-panel-bl/brightness
```

## Extracting Calibration Data

The ALS sensor requires factory calibration data from macOS. The `extract-als-cal.py` script parses a macOS `ioreg -l -a` XML dump and extracts the `CalibrationData` blob from the `AppleSPUVD6286` node.

**Without this calibration file, the ALS sensor will report 0 lux.**

The calibration data is device-specific (per-unit factory calibration), so you must extract it from your own machine's macOS installation.

## Desktop Integration

The daemon writes brightness directly to sysfs, completely bypassing the desktop environment. This prevents the brightness OSD from appearing during automatic adjustments. Manual brightness changes via the KDE slider or keyboard shortcuts still work normally and are respected by the daemon — it pauses auto-brightness until the ambient light changes significantly.

After brightness stabilizes, the daemon syncs the KDE slider via D-Bus (with `SuppressIndicator` flag) so the slider position stays accurate.

## Customizing the Brightness Curve

Edit the `LUX_CURVE` table in `auto-brightness`. Values are percentages of `max_brightness` (read from sysfs at startup):

```python
LUX_CURVE = [
    (0,     2),    # 0 lux    →  2% brightness
    (1,     3),    # 1 lux    →  3% brightness
    (5,     6),    # 5 lux    →  6% brightness
    (20,   12),    # 20 lux   → 12% brightness
    (50,   24),    # 50 lux   → 24% brightness
    (100,  40),    # 100 lux  → 40% brightness
    (200,  60),    # 200 lux  → 60% brightness
    (400,  80),    # 400 lux  → 80% brightness
    (700,  92),    # 700 lux  → 92% brightness
    (1000, 100),   # 1000+ lux → 100% brightness
]
```

Values are linearly interpolated between points.

## Tuning Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `POLL_INTERVAL` | 0.5s | How often to read the sensor |
| `SMOOTH_STEP` | 2 | Sysfs brightness units per cycle |
| `LUX_CHANGE_PCT` | 50% | Lux change to resume after manual override |
| `LUX_CHANGE_MIN` | 5 | Minimum absolute lux change (low-light) |
| `MIN_BRIGHTNESS` | 10 | Floor brightness (sysfs units) |
| `STABLE_SYNC_AFTER` | 10 | Cycles before syncing KDE slider (~5s) |

## Tested Hardware

- MacBook Air 15" M2 (J415) — VD6286 sensor, Asahi Fedora 42, KDE 6.6

## Troubleshooting

**ALS reads 0 lux**: Missing or wrong calibration file. Re-extract from macOS.

**Brightness doesn't change**: Check backlight permissions: `ls -l /sys/class/backlight/apple-panel-bl/brightness` should be world-writable. Check `systemctl --user status auto-brightness` for errors.

**Manual slider ignored**: The daemon detects slider changes and enters manual override mode. It resumes auto-brightness when ambient light changes by ≥50%.

## License

MIT
