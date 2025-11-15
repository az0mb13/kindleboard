#!/usr/bin/env python3
"""
Kindle Dashboard v18 – Refined
• Improved error handling and code clarity
• Centralized constants
• Uses 12-hour format
• Cleaner layout + automatic icon safety
"""

import os
import sys
import datetime
import calendar
import subprocess
import requests
import feedparser
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageStat
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------
load_dotenv()

KINDLE_HOST = "192.168.0.100"
TODOIST_TOKEN = os.getenv("TODOIST_API_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
CITY = "Bangalore"

WIDTH, HEIGHT = 1448, 1072
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "dashboard.png")


FONT_PATH = "/Users/zombie/projects/kindleboard/assets/fonts/DejaVuSans.ttf"
ICON_DIR = "/Users/zombie/projects/kindleboard/assets/icons"

ICONS = {
    "todo": os.path.join(ICON_DIR, "todo.png"),
    "done": os.path.join(ICON_DIR, "completed.png"),
    "security": os.path.join(ICON_DIR, "security.png"),
    "calendar": os.path.join(ICON_DIR, "calendar.png"),
}

PADDING = 40
DIVIDER_X = 900
CARD_SPACING = 25
CARD_RADIUS = 20
CARD_FILL = 240
CARD_OUTLINE = 180

# ---------------------------------------------------------------------
# FETCHERS
# ---------------------------------------------------------------------
def fetch_todoist():
    """Fetch active and completed Todoist tasks."""
    if not TODOIST_TOKEN:
        print("❌ Missing TODOIST_API_TOKEN in .env")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {TODOIST_TOKEN}"}
    try:
        tasks = requests.get("https://api.todoist.com/rest/v2/tasks", headers=headers, timeout=10).json()
        done = (
            requests.get("https://api.todoist.com/sync/v9/completed/get_all", headers=headers, timeout=10)
            .json()
            .get("items", [])
        )
        return tasks, done[:5]
    except Exception as e:
        print(f"⚠️ Todoist fetch failed: {e}")
        return [], []

def fetch_battery():
    """Read Kindle battery percentage over SSH."""
    try:
        cmd = [
            "ssh",
            f"root@{KINDLE_HOST}",
            "cat /sys/devices/platform/imx-i2c.0/i2c-0/0-003c/"
            "max77696-battery.0/power_supply/max77696-battery/capacity",
        ]
        out = subprocess.check_output(cmd, timeout=5)
        return out.decode().strip()
    except Exception:
        return "N/A"

def fetch_weather():
    """Fetch weather data and icon from WeatherAPI."""
    if not WEATHER_API_KEY:
        print("⚠️ Missing WEATHER_API_KEY in .env")
        return None

    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={CITY}&aqi=no"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ Weather API HTTP {resp.status_code}: {resp.text[:120]}")
            return None

        data = resp.json()
        current = data.get("current")
        if not current:
            print(f"⚠️ Unexpected weather data format: {data}")
            return None

        condition = current.get("condition", {}).get("text", "Unknown")
        temp = round(current.get("temp_c", 0))
        humidity = current.get("humidity", 0)
        icon_url = "https:" + current.get("condition", {}).get("icon", "")

        icon_path = "/tmp/weather.png"
        try:
            icon_data = requests.get(icon_url, timeout=6)
            with open(icon_path, "wb") as f:
                f.write(icon_data.content)
        except Exception:
            icon_path = None

        return {
            "temp": temp,
            "condition": condition,
            "humidity": humidity,
            "icon": icon_path,
        }

    except Exception as e:
        print("⚠️ Weather fetch error:", e)
        return None

def fetch_security_feeds():
    """Fetch a few latest headlines from security feeds."""
    feeds = [
        "https://blog.projectdiscovery.io/rss/",
        "https://cvefeed.io/rss",
        "https://www.exploit-db.com/rss.xml",
    ]
    items = []
    try:
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]:
                title = entry.title.replace("\n", " ").strip()
                items.append(f"• {title}")
        return items[:3] or ["No new security updates."]
    except Exception as e:
        return [f"Feed error: {e}"]

# ---------------------------------------------------------------------
# DRAW HELPERS
# ---------------------------------------------------------------------
def draw_icon_with_text(draw, img, x, y, icon_path, label, font_text):
    """Draw an icon next to text with e-ink-safe preprocessing."""
    try:
        icon = Image.open(icon_path).convert("RGBA")
        bg = Image.new("RGBA", icon.size, (255, 255, 255, 255))
        icon = Image.alpha_composite(bg, icon).convert("L")

        brightness = ImageStat.Stat(icon).mean[0]
        if brightness > 180:
            icon = ImageOps.invert(icon)

        icon = ImageOps.autocontrast(icon, cutoff=3).resize((40, 40))
        img.paste(icon, (x, y))
        draw.text((x + 55, y + 6), label, font=font_text, fill=0)
    except Exception as e:
        print(f"⚠️ Icon render failed ({icon_path}): {e}")
        draw.text((x, y), label, font=font_text, fill=0)

def draw_calendar(draw, x, y, w, font_header, font_day, font_num):
    """Draw a centered, evenly spaced calendar for the current month."""
    now = datetime.datetime.now()
    month_name = now.strftime("%B %Y")

    left, top = x, y
    width = w - 80
    col_width = width // 7
    row_height = 32

    # Month title
    month_x = left + (width - draw.textlength(month_name, font=font_header)) // 2
    draw.text((month_x, top), month_name, font=font_header, fill=0)

    # Weekdays
    weekdays = ["M", "T", "W", "T", "F", "S", "S"]
    y_offset = top + 40
    for i, wd in enumerate(weekdays):
        wd_x = left + (col_width * i) + (col_width - draw.textlength(wd, font=font_day)) // 2
        draw.text((wd_x, y_offset), wd, font=font_day, fill=0)

    # Dates
    cal = calendar.Calendar(firstweekday=0)
    y_offset += 30
    col = row = 0
    for day in cal.itermonthdays(now.year, now.month):
        if day == 0:
            col += 1
            continue
        dx = left + (col_width * (col % 7)) + (col_width // 3)
        dy = y_offset + (row * row_height)
        if day == now.day:
            draw.rectangle((dx - 10, dy - 3, dx + 25, dy + 25), fill=0)
            draw.text((dx, dy), f"{day:2}", font=font_num, fill=255)
        else:
            draw.text((dx, dy), f"{day:2}", font=font_num, fill=0)
        col += 1
        if col % 7 == 0:
            row += 1

# ---------------------------------------------------------------------
# DRAW DASHBOARD
# ---------------------------------------------------------------------
def draw_dashboard(tasks, done, battery, weather, feeds):
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # Fonts
    title = ImageFont.truetype(FONT_PATH, 42)
    header = ImageFont.truetype(FONT_PATH, 30)
    sub = ImageFont.truetype(FONT_PATH, 26)
    small = ImageFont.truetype(FONT_PATH, 20)
    cal_font = ImageFont.truetype(FONT_PATH, 22)

    now = datetime.datetime.now()

    # ---------------- HEADER ----------------
    draw.rectangle((0, 0, WIDTH, 100), fill=235)
    left_text = f"{now.strftime('%a, %b %d')}  •  {now.strftime('%I:%M %p')}"
    draw.text((PADDING, 30), left_text, font=header, fill=0)

    right_x = WIDTH - 60

    battery_text = f"[BAT: {battery}%]"
    batt_width = draw.textlength(battery_text, font=sub)
    right_x -= batt_width
    draw.text((right_x, 34), battery_text, font=sub, fill=0)
    right_x -= 40

    if weather and isinstance(weather, dict):
        weather_text = f"{weather['temp']}°C  {weather['condition']}  Hum {weather['humidity']}%"
        weather_width = draw.textlength(weather_text, font=sub)
        right_x -= weather_width
        draw.text((right_x, 34), weather_text, font=sub, fill=0)

        if os.path.exists(weather.get("icon", "")):
            icon = Image.open(weather["icon"]).convert("L").resize((42, 42))
            icon_x = right_x - 50
            img.paste(icon, (int(icon_x), 27))
    else:
        fallback = "Weather: N/A"
        draw.text((right_x - draw.textlength(fallback, font=sub), 34), fallback, font=sub, fill=0)

    # ---------------- LEFT PANEL ----------------
    current_y = 130

    def card(label, icon, top, height):
        bottom = top + height
        draw.rounded_rectangle(
            (PADDING, top, DIVIDER_X - 60, bottom),
            radius=CARD_RADIUS,
            fill=CARD_FILL,
            outline=CARD_OUTLINE,
        )
        draw_icon_with_text(draw, img, PADDING + 30, top + 20, icon, label, title)
        return bottom

    # Todoist Card
    box_bottom = card("Todo List", ICONS["todo"], current_y, 250)
    y = current_y + 70
    for t in tasks[:6]:
        c = t.get("content", "").strip()
        if not c:
            continue
        due = f" ({t['due']['date']})" if t.get("due") and t["due"].get("date") else ""
        draw.text((PADDING + 50, y), f"• {c[:60]}{due}", font=sub, fill=0)
        y += 30

    # Completed Card
    current_y = box_bottom + CARD_SPACING
    height = 120 + len(done) * 30
    box_bottom = card("Completed (Latest 5)", ICONS["done"], current_y, height)
    y = current_y + 70
    for t in done:
        c = t.get("content", "").strip()
        if not c:
            continue
        draw.text((PADDING + 50, y), f"☑ {c[:55]}", font=sub, fill=100)
        y += 28

    # Security Feeds Card
    current_y = box_bottom + CARD_SPACING
    box_bottom = card("Security Feeds", ICONS["security"], current_y, 180)
    y = current_y + 70
    for line in feeds:
        draw.text((PADDING + 50, y), line[:85], font=sub, fill=0)
        y += 28

    # ---------------- RIGHT PANEL ----------------
    draw.line((DIVIDER_X, 110, DIVIDER_X, HEIGHT - 60), fill=180, width=2)

    # Calendar Card
    box_top = 130
    box_bottom = box_top + 320
    draw.rounded_rectangle((DIVIDER_X + 30, box_top, WIDTH - 40, box_bottom),
                           radius=CARD_RADIUS, fill=CARD_FILL, outline=CARD_OUTLINE)
    draw_icon_with_text(draw, img, DIVIDER_X + 60, box_top + 20, ICONS["calendar"], "Calendar", title)
    draw_calendar(draw, DIVIDER_X + 60, box_top + 70, WIDTH - (DIVIDER_X + 60),
                  font_header=header, font_day=small, font_num=cal_font)

    # ---------------- FOOTER ----------------
    draw.line((PADDING, HEIGHT - 60, WIDTH - PADDING, HEIGHT - 60), fill=180, width=1)
    draw.text((PADDING, HEIGHT - 45),
              f"Updated: {now.strftime('%I:%M %p')} | Dashboard v18",
              font=small, fill=0)

    img = img.rotate(90, expand=True)
    img.save(OUTPUT_FILE)
    print("✅ Dashboard v18 generated successfully.")

# ---------------------------------------------------------------------
# PUSH TO KINDLE
# ---------------------------------------------------------------------
def push_to_kindle():
    subprocess.run(["scp", OUTPUT_FILE, f"root@{KINDLE_HOST}:/mnt/us/linkss/screensavers/bg_ss00.png"], check=True)
    # subprocess.run(["ssh", f"root@{KINDLE_HOST}", "/usr/sbin/eips", "-g", "/mnt/us/linkss/screensavers/dashboard.png"], check=True)
    # Copy dashboard as Kindle screensaver
    # subprocess.run([
    #     "ssh", f"root@{KINDLE_HOST}",
    #     "cp /mnt/us/dashboard.png /mnt/us/linkss/screensavers/dashboard.png"
    # ], check=True)

    # Force screensaver refresh (optional)
    subprocess.run([
        "ssh", f"root@{KINDLE_HOST}",
        "lipc-set-prop com.lab126.powerd preventScreenSaver 0"
    ], check=False)

    print("✅ Dashboard pushed as Kindle screensaver.")
    print("✅ Display updated on Kindle.")

# ---------------------------------------------------------------------
if __name__ == "__main__":
    tasks, done = fetch_todoist()
    battery = fetch_battery()
    weather = fetch_weather()
    feeds = fetch_security_feeds()
    draw_dashboard(tasks, done, battery, weather, feeds)
    push_to_kindle()
