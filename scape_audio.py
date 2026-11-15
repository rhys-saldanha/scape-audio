#!/usr/bin/env python3
"""Route audio to the Fractal Scape while it is off its dock, and back when docked.

The dongle (36bc:0001) answers the HID query 02 11 21 at all times. Byte 4 of the raw
reply is 1 while the headset is awake and 0 while it is docked. No answer is treated as docked.
"""
import glob
import os
import select
import subprocess
import time

DEBOUNCE = 2  # consecutive polls needed to accept a change; the dongle blips when docking


def find_hidraw():
    for uevent in glob.glob('/sys/class/hidraw/hidraw*/device/uevent'):
        with open(uevent) as f:
            if 'HID_ID=0003:000036BC:00000001' in f.read():
                return '/dev/' + uevent.split('/')[4]
    return None


def lifted(fd):
    try:
        while True:
            os.read(fd, 128)
    except BlockingIOError:
        pass
    os.write(fd, bytes([2, 0x11, 0x21] + [0] * 61))
    ready, _, _ = select.select([fd], [], [], 0.4)
    return bool(ready) and os.read(fd, 128)[4] == 1


def pactl(*args):
    return subprocess.run(['pactl', *args], capture_output=True, text=True).stdout.strip()


def scape_sink():
    for line in pactl('list', 'short', 'sinks').splitlines():
        name = line.split('\t')[1]
        if 'Fractal_Fractal_Scape' in name:
            return name
    return None


def fallback_sink():
    # shortcut: first non-Scape, non-controller sink; make it configurable if this picks wrongly
    for line in pactl('list', 'short', 'sinks').splitlines():
        name = line.split('\t')[1]
        if 'Fractal_Fractal_Scape' not in name and 'DualSense' not in name:
            return name
    return None


def main():
    fd = None
    state = None
    pending, count = None, 0
    previous = None
    while True:
        try:
            if fd is None:
                path = find_hidraw()
                if path:
                    fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
            now = lifted(fd) if fd is not None else False
        except OSError:
            if fd is not None:
                os.close(fd)
            fd, now = None, False

        if now == pending:
            count += 1
        else:
            pending, count = now, 1
        if count >= DEBOUNCE and now != state:
            state = now
            sink = scape_sink()
            if state and sink:
                current = pactl('get-default-sink')
                if current != sink:
                    previous = current
                    pactl('set-default-sink', sink)
            elif not state:
                # previous is unset when the daemon started with the Scape already the default
                target = previous or fallback_sink()
                if target:
                    pactl('set-default-sink', target)
                previous = None
        time.sleep(0.5)


if __name__ == '__main__':
    main()
