Perfect — this project absolutely deserves a polished, developer-friendly README.
Here’s a complete, clean, and professional `README.md` tailored for your **Kindle Dashboard** project (v18).

---

## 🖥 Kindle Dashboard

Transform your old Kindle into a minimalist **always-on productivity dashboard** — showing your Todoist tasks, recent security feeds, weather updates, battery status, and calendar, all rendered beautifully in grayscale.



---

### ✨ Features

* 📋 **Todoist Integration** — shows your active and completed tasks (via Todoist REST API)
* 🌤 **Weather Data + Icons** — pulls real-time weather info and conditions from WeatherAPI
* 🔋 **Battery Monitor** — displays your Kindle’s battery percentage via SSH
* 🧩 **Security Feeds Summary** — fetches latest headlines from top infosec RSS feeds
* 📅 **Calendar View** — automatically generates a monthly calendar for quick reference
* 🕐 **Auto 12-hour time format** with AM/PM
* ⚡ **Icon-based cards** rendered as crisp e-ink graphics
* 🖼 **Full grayscale PNG rendering** for Kindle e-ink display

---

### 🧰 Requirements

#### Kindle

* A **jailbroken Kindle Paperwhite or later** (tested on PW7, FW 5.16.2.1.1)
* **KUAL** and **USBNetwork** installed and working
* SSH access as `root` (verify with `ssh root@<kindle-ip>`)
* `eips` utility available at `/usr/sbin/eips`

#### Host System

* macOS / Linux
* Python 3.9+
* `pip install -r requirements.txt`

---

### 📦 Setup Instructions

#### 1️⃣ Clone this repository

```bash
git clone https://github.com/<yourusername>/kindle-dashboard.git
cd kindle-dashboard
```

#### 2️⃣ Create a `.env` file

```bash
cp .env.example .env
```

Then fill in your credentials:

```bash
TODOIST_API_TOKEN=your_todoist_api_key_here
WEATHER_API_KEY=your_weatherapi_key_here
```

You can get a free key for WeatherAPI at:
👉 [https://www.weatherapi.com/](https://www.weatherapi.com/)

#### 3️⃣ Set your Kindle IP

Edit `generate_dashboard.py`:

```python
KINDLE_HOST = "192.168.xx.xxx"  # Replace with your Kindle’s IP (usbnet or Wi-Fi)
```

You can find it via:

```bash
ifconfig  # look for "enX" (usually 192.168.15.244 when using USBNetwork)
```

#### 4️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt**

```
Pillow
requests
feedparser
python-dotenv
```

#### 5️⃣ Add your fonts and icons

* Fonts go in: `assets/fonts/`

  * Example: `DejaVuSans.ttf`
* Icons go in: `assets/icons/`

  * Required files:

    ```
    todo.png
    completed.png
    calendar.png
    security.png
    ```

  You can use any small monochrome PNGs (40×40 works best).

#### 6️⃣ Run the dashboard generator

```bash
python3 generate_dashboard.py
```

This will:

* Fetch your data
* Render a new `dashboard.png`
* Upload it via SCP to your Kindle (`/mnt/us/dashboard.png`)
* Display it using:

  ```bash
  /usr/sbin/eips -g /mnt/us/dashboard.png
  ```

---

### ⚙️ Optional: Auto Refresh Every Hour

If you want your Kindle dashboard to update every hour automatically, run:

```bash
while true; do
  python3 /path/to/generate_dashboard.py >> dashboard.log 2>&1
  sleep 3600
done
```

Or add a cron job (macOS/Linux):

```bash
0 * * * * /usr/bin/python3 /Users/you/kindle-dashboard/generate_dashboard.py >> /Users/you/kindle-dashboard/dashboard.log 2>&1
```

---

### 📱 Kindle Tips

* **Prevent Sleep:**
  Stop Kindle’s framework before running:

  ```bash
  initctl stop framework
  ```

  This prevents touch inputs from “clicking” things underneath your dashboard.

* **View as Screensaver (optional):**
  If you have the `linkss` hack installed, copy your dashboard:

  ```bash
  cp /mnt/us/dashboard.png /mnt/us/linkss/screensavers/
  ```

* **Landscape Mode:**
  The image is automatically rotated to landscape during generation.

---

### 🧩 Troubleshooting

| Problem                          | Fix                                                                                  |
| -------------------------------- | ------------------------------------------------------------------------------------ |
| `Weather fetch error: 'current'` | Check your WeatherAPI key or `.env` file                                             |
| `eips: not found`                | Ensure `/usr/sbin/eips` exists on Kindle                                             |
| Icons appear blank               | Verify icons are white on transparent background (try inverting them)                |
| “No tasks found”                 | Ensure `TODOIST_API_TOKEN` is valid and has active tasks                             |
| SSH password prompt              | Make sure you’ve added your SSH key to Kindle (`/mnt/us/usbnet/etc/authorized_keys`) |

---

### 🧠 Future Ideas

* Google Calendar integration
* Notion task sync
* Automatic dark/light theme switch
* Wi-Fi signal indicator
* Daily quote or focus timer

---

### 🧑‍💻 Credits

ChadGPT

---

### 🪶 License

MIT License — do whatever you like ❤️
