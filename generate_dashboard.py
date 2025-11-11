#!/usr/bin/env python3
"""
Kindle Dashboard v3.2
Minimalist Todoist + Weather + Battery dashboard rendered as PNG,
auto-uploaded and displayed on Kindle using /usr/sbin/eips.
"""

import os, sys, datetime, subprocess, requests
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------
KINDLE_HOST   = "192.168.15.244"                       # Kindle IP
TODOIST_TOKEN = os.getenv("TODOIST_API_TOKEN")          # export TODOIST_API_TOKEN=...
CITY          = "Bangalore"                             # for weather
WIDTH, HEIGHT = 1072, 1448
OUTPUT_FILE   = "dashboard.png"

# Fonts (macOS paths — update if needed)
FONT_DIR      = "/System/Library/Fonts/Supplemental"
FONT_BOLD     = os.path.join(FONT_DIR, "Arial Bold.ttf")
FONT_REG      = os.path.join(FONT_DIR, "Arial.ttf")

# ---------------------------------------------------------------------
# FETCHERS
# ---------------------------------------------------------------------
def fetch_todoist():
    if not TODOIST_TOKEN:
        print("❌ Missing TODOIST_API_TOKEN.")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {TODOIST_TOKEN}"}
    tasks = requests.get("https://api.todoist.com/rest/v2/tasks",
                         headers=headers, timeout=10).json()
    done  = requests.get("https://api.todoist.com/sync/v9/completed/get_all",
                         headers=headers, timeout=10).json().get("items", [])
    return tasks, done

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
        return requests.get(f"https://wttr.in/{CITY}?format=%t+%C", timeout=6).text.strip()
    except Exception:
        return "N/A"

# ---------------------------------------------------------------------
# DRAW DASHBOARD
# ---------------------------------------------------------------------
def draw_dashboard(tasks, done, battery, weather):
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    header = ImageFont.truetype(FONT_BOLD, 42)
    sub    = ImageFont.truetype(FONT_REG, 28)
    text   = ImageFont.truetype(FONT_REG, 26)
    small  = ImageFont.truetype(FONT_REG, 22)

    now = datetime.datetime.now()
    y = 40
    RIGHT_MARGIN = 50   # leave boundary on right side

    # --- Header Bar ----------------------------------------------------
    draw.rectangle((0, 0, WIDTH, 130), fill=240)
    draw.text((40, 40), now.strftime("%A, %b %d"), font=header, fill=0)

    # Right-aligned header text (battery + weather)
    right_text = f"{weather}   🔋 {battery}%"
    text_width = draw.textlength(right_text, font=sub)
    draw.text((WIDTH - text_width - RIGHT_MARGIN, 40),
              right_text, font=sub, fill=0)

    # --- Active Tasks --------------------------------------------------
    y = 150
    draw.text((40, y), "ACTIVE TASKS", font=header, fill=0)
    y += 50
    shown = 0
    for t in tasks:
        c = t.get("content", "").strip()
        if not c:
            continue
        due = ""
        if t.get("due") and t["due"].get("date"):
            due = " (" + t["due"]["date"] + ")"
        draw.text((60, y), "• " + c[:65] + due, font=text, fill=0)
        y += 34
        shown += 1
        if shown >= 8:
            break

    # --- Completed Tasks ----------------------------------------------
    y += 20
    draw.line((40, y, WIDTH-40, y), fill=0, width=1)
    y += 25
    draw.text((40, y), "COMPLETED (24h)", font=sub, fill=0)
    y += 35
    shown = 0
    for t in done:
        c = t.get("content", "").strip()
        if not c:
            continue
        completed = t.get("completed_at")
        if not completed:
            continue
        try:
            dt = datetime.datetime.strptime(completed[:19], "%Y-%m-%dT%H:%M:%S")
            if (datetime.datetime.utcnow() - dt).total_seconds() > 86400:
                continue
        except Exception:
            continue
        draw.text((60, y), f"[x] {c[:65]}", font=text, fill=128)
        y += 30
        shown += 1
        if shown >= 5:
            break

    # --- Footer --------------------------------------------------------
    y = HEIGHT - 70
    draw.line((40, y, WIDTH-40, y), fill=0, width=1)
    draw.text((40, y+10), "Updated: " + now.strftime("%H:%M"), font=small, fill=0)

    img.save(OUTPUT_FILE)
    print("✅ Dashboard PNG generated.")

# ---------------------------------------------------------------------
# PUSH TO KINDLE
# ---------------------------------------------------------------------
def push_to_kindle():
    print("📡 Uploading to Kindle...")
    subprocess.run(["scp", OUTPUT_FILE,
                    f"root@{KINDLE_HOST}:/mnt/us/dashboard.png"],
                   check=True)
    subprocess.run(["ssh", f"root@{KINDLE_HOST}",
                    "/usr/sbin/eips", "-g", "/mnt/us/dashboard.png"],
                   check=True)
    print("✅ Display updated.")

# ---------------------------------------------------------------------
if __name__ == "__main__":
    print("Fetching data...")
    tasks, done = fetch_todoist()
    battery = fetch_battery()
    weather = fetch_weather()
    draw_dashboard(tasks, done, battery, weather)
    push_to_kindle()
