#!/usr/bin/env python3

import os, sys, datetime, calendar, subprocess, requests, feedparser
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageStat
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------
load_dotenv()
KINDLE_HOST   = "192.168.15.244"
TODOIST_TOKEN = os.getenv("TODOIST_API_TOKEN")
CITY          = "Bangalore"
WIDTH, HEIGHT = 1448, 1072
OUTPUT_FILE   = "dashboard.png"


FONT_PATH = "/Users/zombie/projects/kindleboard/assets/fonts/DejaVuSans.ttf"
ICON_DIR  = "/Users/zombie/projects/kindleboard/assets/icons"  # local folder for icons

ICONS = {
    "todo": os.path.join(ICON_DIR, "todo.png"),
    "done": os.path.join(ICON_DIR, "completed.png"),
    "security": os.path.join(ICON_DIR, "security.png"),
    "calendar": os.path.join(ICON_DIR, "calendar.png"),
}

# ---------------------------------------------------------------------
# FETCHERS
# ---------------------------------------------------------------------
def fetch_todoist():
    if not TODOIST_TOKEN:
        print("❌ Missing TODOIST_API_TOKEN.")
        sys.exit(1)
    headers = {"Authorization": f"Bearer {TODOIST_TOKEN}"}
    tasks = requests.get("https://api.todoist.com/rest/v2/tasks", headers=headers, timeout=10).json()
    done  = requests.get("https://api.todoist.com/sync/v9/completed/get_all", headers=headers, timeout=10).json().get("items", [])
    return tasks, done[:5]

def fetch_battery():
    try:
        out = subprocess.check_output([
            "ssh", f"root@{KINDLE_HOST}",
            "cat /sys/devices/platform/imx-i2c.0/i2c-0/0-003c/max77696-battery.0/"
            "power_supply/max77696-battery/capacity"
        ], timeout=5)
        return out.decode().strip()
    except Exception:
        return "N/A"

def fetch_weather():
    try:
        from dotenv import load_dotenv
        load_dotenv()  # ensure environment vars are loaded

        API_KEY = os.getenv("WEATHER_API_KEY")
        CITY = "Bangalore"
        if not API_KEY:
            print("⚠️ Missing WEATHER_API_KEY in .env")
            return None

        url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={CITY}&aqi=no"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ Weather API returned HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        if "current" not in data:
            print(f"⚠️ Unexpected weather data format: {data}")
            return None

        current = data["current"]
        condition = current.get("condition", {}).get("text", "Unknown")
        temp = round(current.get("temp_c", 0))
        humidity = current.get("humidity", 0)
        icon_url = "https:" + current.get("condition", {}).get("icon", "")

        # Download weather icon safely
        icon_path = "/tmp/weather.png"
        try:
            icon = requests.get(icon_url, timeout=6)
            with open(icon_path, "wb") as f:
                f.write(icon.content)
        except Exception as e:
            print("⚠️ Could not download weather icon:", e)
            icon_path = None

        return {
            "temp": temp,
            "condition": condition,
            "humidity": humidity,
            "icon": icon_path
        }

    except Exception as e:
        print("Weather fetch error:", e)
        return None


def fetch_security_feeds():
    feeds = [
        "https://blog.projectdiscovery.io/rss/",
        "https://cvefeed.io/rss",
        "https://www.exploit-db.com/rss.xml"
    ]
    items = []
    try:
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]:
                title = entry.title.replace("\n", " ").strip()
                items.append(f"• {title}")
        if not items:
            items = ["No new security updates."]
    except Exception as e:
        items = [f"Feed error: {e}"]
    return items[:3]

# ---------------------------------------------------------------------
# DRAW HELPERS
# ---------------------------------------------------------------------
def draw_icon_with_text(draw, img, x, y, icon_path, label, font_text):
    """Draws an icon (auto-adjusted for e-ink visibility) next to a label."""
    try:
        icon = Image.open(icon_path).convert("RGBA")
        # Flatten transparency over white background
        bg = Image.new("RGBA", icon.size, (255, 255, 255, 255))
        icon = Image.alpha_composite(bg, icon).convert("L")

        # Auto-detect brightness
        brightness = ImageStat.Stat(icon).mean[0]
        if brightness > 180:  # Likely white icon
            icon = ImageOps.invert(icon)

        # Optional: contrast enhance
        icon = ImageOps.autocontrast(icon, cutoff=3)
        icon = icon.resize((40, 40))

        img.paste(icon, (x, y))
        draw.text((x + 55, y + 6), label, font=font_text, fill=0)
    except Exception as e:
        print(f"⚠️ Icon render failed ({icon_path}): {e}")
        draw.text((x, y), label, font=font_text, fill=0)



def draw_calendar(draw, x, y, w, font_header, font_day, font_num):
    """Draws a properly centered and evenly spaced monthly calendar."""
    now = datetime.datetime.now()
    month_name = now.strftime("%B %Y")

    # Card layout
    left, top = x, y
    width = w - 80  # leave some padding on right edge
    col_width = width // 7
    row_height = 32

    # Center the month name
    month_width = draw.textlength(month_name, font=font_header)
    month_x = left + (width - month_width) // 2
    draw.text((month_x, top), month_name, font=font_header, fill=0)

    # Weekday headers
    weekdays = ["M", "T", "W", "T", "F", "S", "S"]
    y_offset = top + 40
    for i, wd in enumerate(weekdays):
        wd_width = draw.textlength(wd, font=font_day)
        wd_x = left + (col_width * i) + (col_width - wd_width) // 2
        draw.text((wd_x, y_offset), wd, font=font_day, fill=0)

    # Draw day numbers
    cal = calendar.Calendar(firstweekday=0)
    month_days = list(cal.itermonthdays(now.year, now.month))
    y_offset += 30
    col = 0
    row = 0

    for day in month_days:
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
    PADDING = 40
    DIVIDER_X = 900
    CARD_SPACING = 25
    CARD_RADIUS = 20
    CARD_FILL = 240
    CARD_OUTLINE = 180

    # ---------------- HEADER ----------------
    draw.rectangle((0, 0, WIDTH, 100), fill=235)
    left_text = f"{now.strftime('%a, %b %d')}  •  {now.strftime('%I:%M %p')}"
    draw.text((PADDING, 30), left_text, font=header, fill=0)

    # Default starting point for right-aligned elements
    right_x = WIDTH - 60

    # Battery text (rightmost)
    battery_text = f"[BAT: {battery}%]"
    batt_width = draw.textlength(battery_text, font=sub)
    right_x -= batt_width
    draw.text((right_x, 34), battery_text, font=sub, fill=0)

    # Add spacing before weather info
    right_x -= 40

    # Weather text block
    if weather and isinstance(weather, dict):
        weather_text = f"{weather['temp']}°C  {weather['condition']}  Hum {weather['humidity']}%"
        weather_width = draw.textlength(weather_text, font=sub)
        right_x -= weather_width
        draw.text((right_x, 34), weather_text, font=sub, fill=0)

        # Weather icon to the left of weather text
        if os.path.exists(weather.get("icon", "")):
            icon = Image.open(weather["icon"]).convert("L").resize((42, 42))
            icon_x = right_x - 50  # leave some padding
            img.paste(icon, (int(icon_x), 27))
            right_x = icon_x - 20  # extra padding before icon
    else:
        weather_text = "Weather: N/A"
        weather_width = draw.textlength(weather_text, font=sub)
        right_x -= weather_width
        draw.text((right_x, 34), weather_text, font=sub, fill=0)


    # ---------------- LEFT PANEL ----------------
    current_y = 130

    # Todoist Card
    box_top = current_y
    box_bottom = box_top + 250
    draw.rounded_rectangle((PADDING, box_top, DIVIDER_X - 60, box_bottom),
                           radius=CARD_RADIUS, fill=CARD_FILL, outline=CARD_OUTLINE)
    draw_icon_with_text(draw, img, PADDING + 30, box_top + 20, ICONS["todo"], "Todo List", title)
    y = box_top + 70
    for t in tasks[:6]:
        c = t.get("content", "").strip()
        if not c:
            continue
        due = ""
        if t.get("due") and t["due"].get("date"):
            due = f" ({t['due']['date']})"
        draw.text((PADDING + 50, y), f"• {c[:60]}{due}", font=sub, fill=0)
        y += 30

    current_y = box_bottom + CARD_SPACING

    # Completed Card
    card_height = 120 + (len(done) * 30)
    box_top = current_y
    box_bottom = box_top + card_height
    draw.rounded_rectangle((PADDING, box_top, DIVIDER_X - 60, box_bottom),
                           radius=CARD_RADIUS, fill=CARD_FILL, outline=CARD_OUTLINE)
    draw_icon_with_text(draw, img, PADDING + 30, box_top + 20, ICONS["done"], "Completed (Latest 5)", title)
    y = box_top + 70
    for t in done:
        c = t.get("content", "").strip()
        if not c:
            continue
        draw.text((PADDING + 50, y), f"☑ {c[:55]}", font=sub, fill=100)
        y += 28

    current_y = box_bottom + CARD_SPACING

    # Security Feeds Card
    box_top = current_y
    box_bottom = box_top + 180
    draw.rounded_rectangle((PADDING, box_top, DIVIDER_X - 60, box_bottom),
                           radius=CARD_RADIUS, fill=CARD_FILL, outline=CARD_OUTLINE)
    draw_icon_with_text(draw, img, PADDING + 30, box_top + 20, ICONS["security"], "Security Feeds", title)
    y = box_top + 70
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
          f"Updated: {now.strftime('%I:%M %p')} | Dashboard v17 (Icon Edition)",
          font=small, fill=0)

    img = img.rotate(90, expand=True)
    img.save(OUTPUT_FILE)
    print("✅ Dashboard v17 generated successfully.")

# ---------------------------------------------------------------------
# PUSH TO KINDLE
# ---------------------------------------------------------------------
def push_to_kindle():
    subprocess.run(["scp", OUTPUT_FILE, f"root@{KINDLE_HOST}:/mnt/us/dashboard.png"], check=True)
    subprocess.run(["ssh", f"root@{KINDLE_HOST}", "/usr/sbin/eips", "-g", "/mnt/us/dashboard.png"], check=True)
    print("✅ Display updated on Kindle.")

# ---------------------------------------------------------------------
if __name__ == "__main__":
    tasks, done = fetch_todoist()
    battery = fetch_battery()
    weather = fetch_weather()
    feeds = fetch_security_feeds()
    draw_dashboard(tasks, done, battery, weather, feeds)
    push_to_kindle()
