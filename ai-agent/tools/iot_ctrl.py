"""
Jarvis IoT & Hardware Controller Tool
Controls ESP32/Arduino (Lights, Fans, Relays) via Serial/HTTP and Bluetooth devices.
"""
import subprocess
import glob
import json
import urllib.request

def scan_bluetooth() -> list:
    """Scan for nearby Bluetooth devices."""
    try:
        res = subprocess.run("bluetoothctl devices", shell=True, capture_output=True, text=True, timeout=5)
        lines = res.stdout.strip().split("\n")
        devices = []
        for line in lines:
            if line.startswith("Device"):
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    devices.append({"mac": parts[1], "name": parts[2]})
        return devices
    except Exception as e:
        return [{"error": str(e)}]

def connect_bluetooth(mac_address: str) -> str:
    """Connect to a Bluetooth device."""
    try:
        res = subprocess.run(f"bluetoothctl connect {mac_address}", shell=True, capture_output=True, text=True, timeout=10)
        return res.stdout.strip()
    except Exception as e:
        return f"Bluetooth connect failed: {e}"

def control_esp32_http(ip: str, endpoint: str, params: dict = None) -> str:
    """
    Control ESP32 over local WiFi:
    Example: http://192.168.1.50/relay?pin=5&state=1
    """
    try:
        url = f"http://{ip}/{endpoint}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url += f"?{query}"
        with urllib.request.urlopen(url, timeout=3) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return f"ESP32 HTTP Error: {e}"

def control_esp32_serial(command: str, port: str = None, baudrate: int = 115200) -> str:
    """
    Send raw commands over USB serial to connected ESP32/Arduino.
    Example: 'LIGHT_ON', 'FAN_OFF', 'PIN:13:HIGH'
    """
    try:
        import serial
    except ImportError:
        return "pyserial not installed. Run: pip install pyserial"

    ports = [port] if port else glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
    if not ports:
        return "No ESP32 or serial devices detected on /dev/ttyUSB* or /dev/ttyACM*"

    target_port = ports[0]
    try:
        with serial.Serial(target_port, baudrate, timeout=2) as ser:
            ser.write((command.strip() + "\n").encode())
            ack = ser.readline().decode("utf-8", errors="ignore").strip()
            return f"Sent '{command}' to {target_port}. Response: {ack or 'OK'}"
    except Exception as e:
        return f"Serial communication failed on {target_port}: {e}"
