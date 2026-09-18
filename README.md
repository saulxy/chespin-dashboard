# Chespin Dashboard

A local, single-page web dashboard and submodule of the [chespin](https://github.com/saulxy/chespin) ecosystem designed for personal finance tracking, budget visualization, and kiosk display modes (e.g. on a dedicated Raspberry Pi screen or touchscreen).

---

## 🛠 Tech Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) (Python 3.10+)
- **Database**: SQLite3 (persistent budget, categories, and transactions)
- **Templating**: Jinja2
- **Frontend**: Single-Page HTML5 + [Tailwind CSS](https://tailwindcss.com/) (CDN)
- **Charts & Visuals**: [Chart.js](https://www.chartjs.org/) + [Lucide Icons](https://lucide.dev/)
- **Design Mode**: Dark mode aesthetic with emerald accents, glanceable typography, and touch-friendly kiosk UI

---

## 📁 Project Structure

```
chespin-dashboard/
├── requirements.txt         # FastAPI, Uvicorn, Jinja2, Pydantic
├── run.py                   # CLI runner script
├── init_db.py               # Database initialization & seeding script
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app setup, static/template mounting, DB lifespan
│   ├── config.py            # Dashboard settings & environment variables
│   ├── database.py          # SQLite database connection, tables, seeders, CRUD helpers
│   ├── routers/
│   │   ├── __init__.py
│   │   └── api.py           # REST API endpoints (summary, categories, transactions, system status)
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # Custom styles, glassmorphism, animations, kiosk tweaks
│   │   └── js/
│   │       └── app.js       # Frontend controller, Chart.js managers, live clock & polling
│   └── templates/
│       └── index.html       # Single-page kiosk interface
└── README.md
```

---

## 🚀 Getting Started

### 1. Install Dependencies

Navigate to the `chespin-dashboard` directory and install the requirements:

```bash
pip install -r requirements.txt
```

### 2. Start the Local Server

Run the dashboard using the included `run.py` script:

```bash
python run.py --reload
```

Or directly via `uvicorn`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open your browser and navigate to:
```
http://localhost:8000
```

---

## 🖥 Kiosk Mode Deployment

### Running Fullscreen on Raspberry Pi / Linux

To launch Chromium in dedicated kiosk mode pointing to the local dashboard upon boot:

```bash
chromium-browser --kiosk --noerrdialogs --disable-infobars --check-for-update-interval=31536000 http://localhost:8000
```

### Running on Windows / Desktop

Press the **Fullscreen button** on the top header, or press <kbd>F11</kbd> in your browser to toggle native kiosk fullscreen mode.

---

## 📡 API Endpoints

The dashboard exposes RESTful endpoints for integration with the core Chespin engine:

- `GET /api/v1/summary`: High-level monthly budget, total spend, savings rate, and daily average.
- `GET /api/v1/expenses/monthly`: Monthly expenses breakdown with budget caps.
- `GET /api/v1/transactions/recent`: Recent transaction records.
- `GET /api/v1/system/status`: Device diagnostics, uptime, and Chespin wake word status.
- `GET /health`: Watchdog health check.
