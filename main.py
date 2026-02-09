#!/usr/bin/env python3
"""
OBS Countdown Timer Script
Generates OUTPUT.txt for OBS text source display
"""

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

OUTPUT_FILE = Path(__file__).parent / "OUTPUT.txt"


class TimerState:
    """Holds the current state of the timer"""
    def __init__(self):
        self.running = True
        self.paused = False
        self.restart_requested = False
        self.quit_requested = False
        self.awaiting_confirm = None  # 'restart' or 'quit'
        self.pause_start = None  # When pause started
        self.total_paused = 0  # Total paused seconds


def parse_time(time_str: str) -> int:
    """Parse time string to total seconds"""
    parts = time_str.split(':')
    if len(parts) == 1:
        return int(parts[0])
    elif len(parts) == 2:
        minutes, seconds = int(parts[0]), int(parts[1])
        if seconds >= 60:
            raise ValueError("Seconds must be < 60 when using mm:ss format")
        return minutes * 60 + seconds
    elif len(parts) == 3:
        hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
        if minutes >= 60 or seconds >= 60:
            raise ValueError("Minutes and seconds must be < 60 when using hh:mm:ss format")
        return hours * 3600 + minutes * 60 + seconds
    else:
        raise ValueError("Invalid time format")


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object"""
    if not date_str or date_str.lower() == 'null':
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    parts = date_str.split('/')
    now = datetime.now()
    if len(parts) == 2:
        month, day = int(parts[0]), int(parts[1])
        return datetime(now.year, month, day)
    elif len(parts) == 3:
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        return datetime(year, month, day)
    else:
        raise ValueError("Invalid date format")


def format_time(total_seconds: int, display_mode: int) -> str:
    """Format seconds to display string based on display mode"""
    if total_seconds < 0:
        total_seconds = 0

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if display_mode == 0:
        # Shortest format, no leading zeros on hours/minutes
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        elif minutes > 0:
            return f"{minutes}:{seconds:02d}"
        else:
            return str(seconds)
    elif display_mode == 1:
        # Shortest but keep leading zeros except hours
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        elif minutes > 0:
            return f"{minutes:02d}:{seconds:02d}"
        else:
            return f"{seconds:02d}"
    else:  # display_mode == 2
        # Full format with leading zeros
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def write_output(text: str):
    """Write text to OUTPUT.txt"""
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(text)


def create_keyboard_listener(state: TimerState):
    """Create keyboard listener for r/p/q keys"""
    def on_press(key):
        try:
            char = key.char.lower() if hasattr(key, 'char') and key.char else None
        except AttributeError:
            return

        if state.awaiting_confirm:
            if char == 'y':
                if state.awaiting_confirm == 'restart':
                    state.restart_requested = True
                elif state.awaiting_confirm == 'quit':
                    state.quit_requested = True
                state.awaiting_confirm = None
            elif char == 'n':
                print("\nCancelled.")
                state.awaiting_confirm = None
            return

        if char == 'r':
            print("\nRestart? (y/n): ", end='', flush=True)
            state.awaiting_confirm = 'restart'
        elif char == 'p':
            if state.paused:
                # Resuming - calculate paused duration
                if state.pause_start:
                    state.total_paused += (datetime.now() - state.pause_start).total_seconds()
                    state.pause_start = None
                state.paused = False
                print("\nResumed")
            else:
                # Pausing - record start time
                state.pause_start = datetime.now()
                state.paused = True
                print("\nPaused")
        elif char == 'q':
            print("\nQuit? (y/n): ", end='', flush=True)
            state.awaiting_confirm = 'quit'

    return keyboard.Listener(on_press=on_press)


def run_timer(mode: int, time_str: str, date_str: str, display: int):
    """Main timer loop"""
    state = TimerState()

    # Setup keyboard listener
    listener = None
    if HAS_PYNPUT:
        listener = create_keyboard_listener(state)
        listener.start()
        print("Keys: [r]estart, [p]ause, [q]uit")
    else:
        print("Warning: pynput not installed, keyboard controls disabled")

    while state.running:
        state.restart_requested = False
        state.total_paused = 0
        state.pause_start = None
        state.paused = False

        # Calculate target based on mode
        if mode == 0:
            # Countdown to specific time point
            target_date = parse_date(date_str)
            time_seconds = parse_time(time_str)
            target_time = target_date + timedelta(seconds=time_seconds)
        elif mode == 1:
            # Countdown from duration
            duration = parse_time(time_str)
            start_time = datetime.now()
        else:  # mode == 2
            # Count up
            start_time = datetime.now()

        print(f"Timer started (Mode {mode})")

        while not state.quit_requested and not state.restart_requested:
            if state.paused and mode != 0:
                # When paused (except mode 0), just sleep
                time.sleep(0.1)
                continue

            now = datetime.now()

            if mode == 0:
                remaining = (target_time - now).total_seconds()
                display_seconds = max(0, int(remaining))
                if remaining <= 0:
                    write_output(format_time(0, display))
                    print("\nTime's up!")
                    state.running = False
                    break
            elif mode == 1:
                elapsed = (now - start_time).total_seconds() - state.total_paused
                remaining = duration - elapsed
                display_seconds = max(0, int(remaining))
                if remaining <= 0:
                    write_output(format_time(0, display))
                    print("\nTime's up!")
                    state.running = False
                    break
            else:  # mode == 2
                elapsed = (now - start_time).total_seconds() - state.total_paused
                display_seconds = int(elapsed)

            output = format_time(display_seconds, display)
            write_output(output)
            print(f"\r{output}    ", end='', flush=True)

            time.sleep(0.1)

        if state.quit_requested:
            print("\nExiting...")
            state.running = False

        if state.restart_requested:
            print("\nRestarting...")

    if listener:
        listener.stop()
    print("Timer stopped.")


def show_tui() -> tuple:
    """Interactive TUI for parameter input"""
    print("=" * 40)
    print("  OBS Countdown Timer")
    print("=" * 40)
    print()

    # Mode selection
    print("Select mode:")
    print("  0 - Countdown to specific time point")
    print("  1 - Countdown from duration")
    print("  2 - Count up from now")
    while True:
        try:
            mode = int(input("Mode [0/1/2]: ").strip())
            if mode in [0, 1, 2]:
                break
            print("Invalid mode. Please enter 0, 1, or 2.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Time input
    print()
    if mode == 0:
        print("Enter target time (format: ss, mm:ss, or hh:mm:ss):")
    elif mode == 1:
        print("Enter countdown duration (format: ss, mm:ss, or hh:mm:ss):")
    else:
        print("Count up mode - time parameter not needed")
        time_str = "0"

    if mode != 2:
        while True:
            time_str = input("Time: ").strip()
            try:
                parse_time(time_str)
                break
            except ValueError as e:
                print(f"Invalid time format: {e}")

    # Date input (only for mode 0)
    date_str = None
    if mode == 0:
        print()
        print("Enter target date (format: mm/dd or yyyy/mm/dd, leave empty for today):")
        date_str = input("Date [empty=today]: ").strip() or None

    # Display format
    print()
    print("Select display format:")
    print("  0 - Shortest (4:03)")
    print("  1 - Short with padding (04:03)")
    print("  2 - Full format (00:04:03)")
    while True:
        try:
            display_input = input("Display [0/1/2, default=0]: ").strip()
            display = int(display_input) if display_input else 0
            if display in [0, 1, 2]:
                break
            print("Invalid display mode. Please enter 0, 1, or 2.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    return mode, time_str, date_str, display


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='OBS Countdown Timer - Generates OUTPUT.txt for OBS text source'
    )
    parser.add_argument(
        '-m', '--mode',
        type=int,
        choices=[0, 1, 2],
        help='Timer mode: 0=countdown to time, 1=countdown duration, 2=count up'
    )
    parser.add_argument(
        '-t', '--time',
        type=str,
        help='Time value (ss, mm:ss, or hh:mm:ss)'
    )
    parser.add_argument(
        '-d', '--date',
        type=str,
        default=None,
        help='Date for mode 0 (mm/dd or yyyy/mm/dd)'
    )
    parser.add_argument(
        '-f', '--format',
        type=int,
        choices=[0, 1, 2],
        default=0,
        dest='display',
        help='Display format: 0=shortest, 1=short padded, 2=full (default: 0)'
    )
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()

    # Check if CLI args provided
    if args.mode is not None and args.time is not None:
        mode = args.mode
        time_str = args.time
        date_str = args.date
        display = args.display
    elif args.mode is not None or args.time is not None:
        print("Error: Both --mode and --time are required for CLI mode")
        sys.exit(1)
    else:
        # No CLI args, show TUI
        mode, time_str, date_str, display = show_tui()

    print()
    try:
        run_timer(mode, time_str, date_str, display)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        write_output("")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
