import sys
import time

spinner = "|/-\\"
for _ in range(20):  # Repeat for 20 frames
    for char in spinner:
        sys.stdout.write(f"\r{char}")
        sys.stdout.flush()
        time.sleep(0.2)