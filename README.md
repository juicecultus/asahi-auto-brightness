# Asahi Auto-Brightness

Automatic display brightness based on the ambient light sensor (ALS) for Apple Silicon laptops running [Asahi Linux](https://asahilinux.org/).

Works with the **VD6286** ALS sensor found in M2 MacBook Air (13" and 15") and other Apple Silicon laptops, driven by the `aop_als` kernel module from the [Asahi fairydust](https://github.com/AsahiLinux/linux/tree/fairydust) kernel.

## How It Works

```
VD6286 sensor → aop_als kernel module → IIO sysfs
    → auto-brightness daemon (reads lux from IIO sysfs)
    → KDE ScreenBrightness D-Bus API (SuppressIndicator flag)
```

The daemon reads lux directly from the IIO sensor sysfs node and controls brightness through KDE's D-Bus API with the `SuppressIndicator` flag — the slider tracks smoothly with no OSD popups.

Key features (inspired by [macbook-ambient-sensor](https://github.com/juicecultus/macbook-ambient-sensor)):
- **No OSD popups** — uses KDE `SetBrightness` with `SuppressIndicator` flag
- **Imperceptible transitions** — 0.5% brightness steps every 0.25s
- **Manual override** — respects user slider changes until ambient light shifts by ≥75% (or ≥5 lux absolute in low light)
- **Smooth slider tracking** — KDE slider and display brightness stay perfectly in sync
- **Minimum brightness floor** — prevents black screen

## Prerequisites

- **Kernel**: Asahi fairydust branch with `CONFIG_IIO_AOP_SENSOR_ALS=m`
- **Firmware**: `apple/aop-als-cal.bin` in `/lib/firmware/` (see [Extracting Calibration](#extracting-calibration-data))
- **Packages**: `python3-dbus`
- **Desktop**: KDE Plasma 6+

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
```

## Extracting Calibration Data

The ALS sensor requires factory calibration data from macOS. The `extract-als-cal.py` script parses a macOS `ioreg -l -a` XML dump and extracts the `CalibrationData` blob from the `AppleSPUVD6286` node.

**Without this calibration file, the ALS sensor will report 0 lux.**

The calibration data is device-specific (per-unit factory calibration), so you must extract it from your own machine's macOS installation.

## Desktop Integration

The daemon controls brightness through KDE's `SetBrightness` D-Bus method with the `SuppressIndicator` flag (`flag=1`). This means:
- The KDE brightness slider tracks the display brightness in real time
- No OSD (On-Screen Display) popup appears during automatic adjustments
- Manual brightness changes via the slider are detected and respected

If you change the slider manually, auto-brightness pauses until ambient light changes by ≥75%. This prevents the daemon from immediately overriding your preference.

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
| `POLL_INTERVAL` | 0.25s | How often to read the sensor |
| `SMOOTH_STEP` | 50 | KDE brightness units per cycle (0.5% of 10000) |
| `LUX_CHANGE_PCT` | 75% | Lux change to resume after manual override |
| `LUX_CHANGE_MIN` | 5 | Minimum absolute lux change (low-light) |
| `MIN_BRIGHTNESS` | 200 | Floor brightness (KDE units out of 10000) |

## Tested Hardware

- MacBook Air 15" M2 (J415) — VD6286 sensor, Asahi Fedora 42, KDE 6.6

## Troubleshooting

**ALS reads 0 lux**: Missing or wrong calibration file. Re-extract from macOS.

**Brightness doesn't change**: Make sure KDE Plasma is running. Check `systemctl --user status auto-brightness` for errors.

**Manual slider ignored**: The daemon detects slider changes and enters manual override mode. It resumes auto-brightness when ambient light changes by ≥75%.

## License

MIT
