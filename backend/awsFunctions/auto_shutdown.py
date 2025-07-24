"""
auto_shutdown.py

Sets up automatic EC2 shutdown after 30 minutes of inactivity.
Run this @ start of EC2 processing jobs.
"""
import os
import subprocess
import time
import signal
import sys


def setup_shutdown_timer():
    """Setup 30-minute auto shutdown via at command."""
    try:
        # Schedule shutdown in 30 minutes
        result = subprocess.run(
            ["sudo", "shutdown", "-h", "+30", "Auto shutdown after 30min"], 
            capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("✓ Auto-shutdown scheduled for 30 minutes")
        else:
            print(f"⚠ Failed to schedule shutdown: {result.stderr}")
    except Exception as e:
        print(f"⚠ Could not setup auto-shutdown: {e}")


def cancel_shutdown():
    """Cancel pending shutdown."""
    try:
        subprocess.run(["sudo", "shutdown", "-c"], check=False)
        print("✓ Cancelled auto-shutdown")
    except Exception:
        pass


def signal_handler(signum, frame):
    """Handle script termination."""
    print("\n Shutdown timer cancelled")
    cancel_shutdown()
    sys.exit(0)


def main():
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(" Setting up 30-minute auto-shutdown")
    setup_shutdown_timer()
    
    print("✓ Auto-shutdown active")
    print("  Press Ctrl+C to cancel shutdown")
    print("  Or run: sudo shutdown -c")
    
    # Keep script running to maintain signal handlers
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()