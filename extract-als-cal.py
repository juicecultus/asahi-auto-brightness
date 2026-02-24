#!/usr/bin/env python3
"""
extract-als-cal.py — Extract ALS calibration data from macOS ioreg dump

Parses a macOS `ioreg -l -a` XML plist dump and extracts the
CalibrationData blob from the AppleSPUVD6286 (or similar ALS) node.
Writes it to aop-als-cal.bin for use with the Asahi Linux aop_als driver.

Usage:
  # On macOS, capture the ioreg dump:
  ioreg -l -a > ioreg-full.xml

  # On Linux (or macOS), extract the calibration:
  python3 extract-als-cal.py ioreg-full.xml

  # Install the resulting firmware file:
  sudo cp aop-als-cal.bin /lib/firmware/apple/aop-als-cal.bin
  sudo dracut --force --kver $(uname -r)
"""

import base64
import sys
import xml.etree.ElementTree as ET


def find_calibration(elem):
    """Recursively search for CalibrationData in an ioreg XML plist."""
    if elem.tag == "dict":
        children = list(elem)
        i = 0
        has_vd6286 = False
        cal_data = None

        while i < len(children):
            if children[i].tag == "key" and i + 1 < len(children):
                key = children[i].text or ""
                val = children[i + 1]

                # Check if this dict belongs to the ALS sensor
                if key in ("IORegistryEntryName", "IOClass", "IOObjectClass"):
                    if val.tag == "string" and val.text:
                        if "VD6286" in val.text or "SPUALS" in val.text:
                            has_vd6286 = True

                # Grab CalibrationData if present
                if key == "CalibrationData" and val.tag == "data" and val.text:
                    cal_data = base64.b64decode(val.text)

                i += 2
            else:
                i += 1

        if has_vd6286 and cal_data:
            return cal_data

    for child in elem:
        result = find_calibration(child)
        if result:
            return result

    return None


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <ioreg-full.xml> [output.bin]")
        sys.exit(1)

    ioreg_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "aop-als-cal.bin"

    tree = ET.parse(ioreg_path)
    cal = find_calibration(tree.getroot())

    if cal is None:
        print("ERROR: No ALS CalibrationData found in ioreg dump.")
        print("Make sure you captured with: ioreg -l -a > ioreg-full.xml")
        sys.exit(1)

    with open(output_path, "wb") as f:
        f.write(cal)

    print(f"Extracted {len(cal)} bytes of ALS calibration data")
    print(f"Written to: {output_path}")
    print()
    print("To install:")
    print(f"  sudo cp {output_path} /lib/firmware/apple/aop-als-cal.bin")
    print("  sudo dracut --force --kver $(uname -r)")
    print("  # reboot")


if __name__ == "__main__":
    main()
