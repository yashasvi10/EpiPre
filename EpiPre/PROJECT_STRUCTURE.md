# EpiPre project structure
- `app.py`: Flask app, SQLAlchemy models, authentication, connectors, NLP baseline, risk indicator, alerts and admin routes.
- `templates/`: Bootstrap pages for login, dashboard, social monitor, health/map, news, prediction, alerts and admin.
- `static/css/style.css`: custom styles.
- `static/js/main.js`: async API calls from the UI.
- `requirements.txt`: Python dependencies.
- `sample_health_data.csv`: sample import format.
- `run_windows.bat`, `run_mac_linux.sh`: local startup helpers.

## Frontend modules
Authentication; dashboard; social monitoring; health trends/geography; news; risk/anomaly/alerts; admin/source manager.

## Backend logical modules
User/auth; API ingestion; NLP feature extraction; health analytics; statistical risk/anomaly engine; alert/report/admin management.

No MLP or trained ML predictor is implemented.
