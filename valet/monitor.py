import psutil
import datetime
import requests

def get_weather():
    try:
        res = requests.get("https://wttr.in/?format=3", timeout=3)
        return res.text.strip()
    except:
        return "Weather unavailable"

def get_system_stats() -> dict:
    """Returns live system monitoring data."""
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net = psutil.net_io_counters()
    
    # Calculate uptime
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.datetime.now() - boot_time
    
    return {
        "cpu_percent": cpu,
        "ram_percent": ram.percent,
        "ram_used": f"{ram.used / (1024**3):.1f}GB",
        "ram_total": f"{ram.total / (1024**3):.1f}GB",
        "disk_percent": disk.percent,
        "disk_free": f"{disk.free / (1024**3):.1f}GB",
        "net_sent": f"{net.bytes_sent / (1024**2):.1f}MB",
        "net_recv": f"{net.bytes_recv / (1024**2):.1f}MB",
        "uptime": str(uptime).split('.')[0],
        "weather": get_weather()
    }
