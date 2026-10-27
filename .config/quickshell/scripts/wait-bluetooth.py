#!/usr/bin/python3
"""Bound startup readiness; never power hardware on or block an absent adapter."""
import subprocess
import time

def ready():
    try:
        owner = subprocess.run(["busctl", "--system", "--timeout=1", "call",
            "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
            "NameHasOwner", "s", "org.bluez"], capture_output=True, text=True, timeout=1.5)
        if owner.returncode or owner.stdout.strip() != "b true":
            return False
        result = subprocess.run(["busctl", "--system", "--timeout=1", "call", "org.bluez",
            "/", "org.freedesktop.DBus.ObjectManager", "GetManagedObjects"], capture_output=True, timeout=1.5)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False

if __name__ == "__main__":
    deadline = time.monotonic() + 8
    while not ready() and time.monotonic() < deadline:
        time.sleep(0.2)
