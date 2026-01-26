import subprocess
import time
import re

class ADBController:
    def __init__(self):
        self.device_id = None
        
    def check_connection(self):
        """Checks if a device is connected and returns its ID."""
        try:
            # Try local adb first
            adb_cmd = 'adb'
            import os
            if os.path.exists("adb.exe"):
                adb_cmd = os.path.abspath("adb.exe")
                
            self.adb_exe = adb_cmd # Store for later use in other methods

            result = subprocess.run([self.adb_exe, 'devices'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            # First line is "List of devices attached"
            for line in lines[1:]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        status = parts[1]
                        if status == 'device':
                            self.device_id = parts[0]
                            return self.device_id
                        elif status == 'offline':
                            return "Device Offline (Replug USB)"
                        elif status == 'unauthorized':
                            return "Unauthorized (Check Phone)"
            return None
        except FileNotFoundError:
            return "ADB not found"

    def get_screen_size(self):
        """Returns (width, height) of the screen."""
        if not self.device_id:
            return None
        
        try:
            cmd = [self.adb_exe, '-s', self.device_id, 'shell', 'wm', 'size']
            result = subprocess.run(cmd, capture_output=True, text=True)
            # Output examples:
            # Physical size: 1080x2400
            # Override size: 720x1600 (Optional)
            
            lines = result.stdout.split('\n')
            physical = None
            override = None
            
            for line in lines:
                if 'Override size:' in line:
                    match = re.search(r'(\d+)x(\d+)', line)
                    if match:
                        override = (int(match.group(1)), int(match.group(2)))
                elif 'Physical size:' in line:
                    match = re.search(r'(\d+)x(\d+)', line)
                    if match:
                        physical = (int(match.group(1)), int(match.group(2)))
                        
            return override if override else physical
        except Exception as e:
            print(f"Error getting screen size: {e}")
        return None

    def swipe(self, x1, y1, x2, y2, duration=100):
        """Executes a swipe command."""
        if not self.device_id:
            return
        
        cmd = [self.adb_exe, '-s', self.device_id, 'shell', 'input', 'swipe', 
               str(x1), str(y1), str(x2), str(y2), str(duration)]
        subprocess.run(cmd)

    def tap(self, x, y):
        """Executes a tap command."""
        if not self.device_id:
            return
            
        cmd = [self.adb_exe, '-s', self.device_id, 'shell', 'input', 'tap', str(x), str(y)]
        subprocess.run(cmd)

    def execute_batch(self, commands):
        """Executes a list of shell commands on the device via a script file."""
        if not self.device_id:
            return
            
        # Create local script
        local_script = "draw_script.sh"
        with open(local_script, "w", newline='\n') as f:
            f.write("#!/bin/sh\n")
            for cmd in commands:
                f.write(cmd + "\n")
                
        # Push to device
        remote_path = "/data/local/tmp/draw_script.sh"
        run_args = [self.adb_exe, '-s', self.device_id]
        
        subprocess.run(run_args + ['push', local_script, remote_path], capture_output=True)
        subprocess.run(run_args + ['shell', 'chmod', '+x', remote_path], capture_output=True)
        
        # Execute
        subprocess.run(run_args + ['shell', 'sh', remote_path])
        
        # Cleanup
        try:
            import os
            os.remove(local_script)
        except:
            pass

    def set_pointer_location(self, enabled):
        """Toggles the 'Pointer Location' overlay on the device."""
        if not self.device_id: return
        val = '1' if enabled else '0'
        subprocess.run([self.adb_exe, '-s', self.device_id, 'shell', 'settings', 'put', 'system', 'pointer_location', val])

    def get_screenshot(self, local_path):
        """Captures a screenshot from the device to a local file."""
        if not self.device_id: return False
        
        try:
            # Method 1: exec-out (Faster, pipe directly to file)
            cmd = [self.adb_exe, '-s', self.device_id, 'exec-out', 'screencap', '-p']
            with open(local_path, 'wb') as f:
                subprocess.run(cmd, stdout=f)
            return True
        except Exception as e:
            print(f"Screenshot failed: {e}")
            return False

    def detect_touch_device(self):
        """Detects the touch input device path (e.g., /dev/input/event2)."""
        if not self.device_id: return None
        try:
            # List input devices
            result = subprocess.run(
                [self.adb_exe, '-s', self.device_id, 'shell', 'getevent', '-pl'],
                capture_output=True, text=True, timeout=5
            )
            
            lines = result.stdout.split('\n')
            current_device = None
            for line in lines:
                if 'add device' in line:
                    # Extract path like /dev/input/event2
                    parts = line.split(':')
                    if len(parts) > 1:
                        current_device = parts[1].strip()
                if 'ABS_MT_POSITION_X' in line and current_device:
                    print(f"Detected touch device: {current_device}")
                    return current_device
            return None
        except Exception as e:
            print(f"Touch device detection failed: {e}")
            return None

    def execute_sendevent_batch(self, points, touch_device):
        """Executes a drawing path using sendevent (much faster)."""
        if not self.device_id or not touch_device or not points:
            return False
            
        try:
            cmds = []
            # Finger down
            cmds.append(f"sendevent {touch_device} 3 57 0")  # Tracking ID
            
            for x, y in points:
                cmds.append(f"sendevent {touch_device} 3 53 {x}")  # X
                cmds.append(f"sendevent {touch_device} 3 54 {y}")  # Y
                cmds.append(f"sendevent {touch_device} 3 58 50")   # Pressure
                cmds.append(f"sendevent {touch_device} 0 0 0")     # SYN_REPORT
            
            # Finger up
            cmds.append(f"sendevent {touch_device} 3 57 -1")  # Release tracking ID
            cmds.append(f"sendevent {touch_device} 0 0 0")    # SYN_REPORT
            
            self.execute_batch(cmds)
            return True
        except Exception as e:
            print(f"Sendevent batch failed: {e}")
            return False
