# Asahi Auto-Brightness

Automatic display brightness based on the ambient light sensor (ALS) for Apple Silicon laptops running [Asahi Linux](https://asahilinux.org/).

Works with the **VD6286** ALS sensor found in M2 MacBook Air (13" and 15") and other Apple Silicon laptops, driven by the `aop_als` kernel module from the [Asahi fairydust](https://github.com/AsahiLinux/linux/tree/fairydust) kernel.

## How It Works

```
VD6286 sensor → aop_als kernel module → IIO subsystem
    → iio-sensor-proxy (D-Bus) → auto-brightness daemon
    → KDE ScreenBrightness D-Bus API → display backlight
```

The daemon:
- Reads lux values from `iio-sensor-proxy` via the system D-Bus
- Applies a rolling average (5 samples) to filter sensor noise
- Maps lux to brightness via a configurable curve
- Uses hysteresis to prevent oscillation
- Ramps brightness smoothly (~5%/sec) through KDE's D-Bus API
- Respects manual slider changes (re-syncs each polling cycle)
- Enforces a minimum brightness floor (2%) to prevent black screen

## Prerequisites

- **Kernel**: Asahi fairydust branch with `CONFIG_IIO_AOP_SENSOR_ALS=m`
- **Firmware**: `apple/aop-als-cal.bin` in `/lib/firmware/` (see [Extracting Calibration](#extracting-calibration-data))
- **Packages**: `iio-sensor-proxy`, `python3-dbus`
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
cp auto-brightness ~/.local/bin/auto-brightness
chmod +x ~/.local/bin/auto-brightness

# Install the systemd user service
cp auto-brightness.service ~/.config/systemd/user/auto-brightness.service
systemctl --user daemon-reload
systemctl --user enable --now auto-brightness.service

# (Optional) Allow non-root backlight writes — only needed if
# something other than KDE needs direct sysfs access
sudo cp 99-backlight.rules /etc/udev/rules.d/
```

### 3. Reboot

After reboot, verify:

```bash
# ALS sensor is active
cat /sys/bus/iio/devices/iio:device1/in_illuminance_input

# iio-sensor-proxy sees it
gdbus call --system --dest net.hadess.SensorProxy \
  --object-path /net/hadess/SensorProxy \
  --method org.freedesktop.DBus.Properties.GetAll net.hadess.SensorProxy

# Daemon is running
systemctl --user status auto-brightness
```

## Extracting Calibration Data

The ALS sensor requires factory calibration data from macOS. The `extract-als-cal.py` script parses a macOS `ioreg -l -a` XML dump and extracts the `CalibrationData` blob from the `AppleSPUVD6286` node.

**Without this calibration file, the ALS sensor will report 0 lux.**

The calibration data is device-specific (per-unit factory calibration), so you must extract it from your own machine's macOS installation.

## Customizing the Brightness Curve

Edit the `LUX_CURVE` table in `auto-brightness`:

```python
LUX_CURVE = [
    (0,     4),    # 0 lux  →  4% brightness
    (1,     6),    # 1 lux  →  6% brightness
    (5,    12),    # 5 lux  → 12% brightness
    (20,   22),    # ...
    (50,   38),
    (100,  52),
    (200,  66),
    (400,  80),
    (700,  92),
    (1000, 100),   # 1000+ lux → 100% brightness
]
```

Values are linearly interpolated between points.

## Tuning Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `POLL_INTERVAL` | 1.0s | How often to sample the light sensor |
| `RAMP_RATE` | 500/s | Brightness change speed (KDE units, max 10000) |
| `AVG_WINDOW` | 5 | Rolling average window size |
| `HYSTERESIS_PCT` | 8% | Minimum change to trigger a ramp |
| `MIN_BRIGHTNESS` | 200 | Floor brightness (out of 10000) |

## Tested Hardware

- MacBook Air 15" M2 (J415) — VD6286 sensor, Asahi Fedora 42, KDE 6.6

## Troubleshooting

**ALS reads 0 lux**: Missing or wrong calibration file. Re-extract from macOS.

**Daemon exits immediately**: KDE ScreenBrightness D-Bus not available. Make sure Plasma is running.

**Brightness doesn't change**: Check `systemctl --user status auto-brightness` for errors. Verify `iio-sensor-proxy` is running: `systemctl status iio-sensor-proxy`.

## License

MIT
