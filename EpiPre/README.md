# EpiPre — Local College Project

EpiPre is a Flask + SQLite academic prototype for exploring public social signals, health-report trends, news coverage and environmental context.

## Included modules
1. Authentication and role-based user management (first registered user is admin).
2. Dashboard with disease totals, latest signals, predictions and alerts.
3. Social monitoring: Bluesky public search and Mastodon public hashtag timeline.
4. NLP baseline: disease keyword classification, symptom extraction and simple lexicon sentiment.
5. Health trends: CSV import/export, disease comparison charts and map of sample locations.
6. Environmental context: Open-Meteo geocoding + current weather.
7. News monitoring: GDELT DOC search.
8. Risk indicator: explainable rule-based score and simple statistical anomaly flag.
9. Smart alerts and API source status manager.

## Important scope decision
No MLP, trained ML model or black-box predictive model is included. The risk score is a transparent heuristic, and anomaly detection is a simple comparison of recent vs preceding 14-day averages. Do not use this for medical or official public-health decisions.

## Requirements
Python 3.10+, internet connection for pip installation and optional external APIs.

## Windows setup
1. Extract `EpiPre_Project.zip`.
2. Open the `EpiPre` folder.
3. Install Python from https://www.python.org/downloads/ and enable Add Python to PATH.
4. Double-click `run_windows.bat`.
5. Wait for Flask to start, then open http://127.0.0.1:5000.
6. Register. The first account becomes administrator.

Manual commands:
```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

## macOS / Linux
```bash
chmod +x run_mac_linux.sh
./run_mac_linux.sh
```
Then open http://127.0.0.1:5000.

Stop the server with Ctrl+C. SQLite database `epipre.db` is created automatically.

## Free API integrations included
- Bluesky public search: `https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts`
- Mastodon public hashtag timeline: `https://mastodon.social/api/v1/timelines/tag/{hashtag}`. The app uses mastodon.social by default. Public access is instance-dependent.
- Open-Meteo geocoding and weather: no key for free non-commercial use; fair-use limits and attribution apply.
- GDELT DOC API: global news search; no API key; provider rate limits apply.

These APIs are free/public as documented at the time this package was prepared, but availability, fair-use rules and terms may change. No X/Twitter connector is included because the official X API is not a dependable free option. Reddit is not included because developer access is subject to eligibility and usage rules. See links below.

## Official API references
- Bluesky: https://docs.bsky.app/ and https://bsky.network/docs/jetstream/
- Mastodon: https://docs.joinmastodon.org/methods/timelines/ and https://docs.joinmastodon.org/api/rate-limits/
- Open-Meteo: https://open-meteo.com/en/docs and https://open-meteo.com/en/pricing
- GDELT: https://www.gdeltproject.org/ and https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- WHO FluNet: https://www.who.int/tools/flunet (download CSV; import after mapping to required columns)
- India Open Government Data: https://www.data.gov.in/ (dataset API access depends on resource/API key)
- Reddit policies: https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki
- X developer platform: https://developer.x.com/

## Import health data
Use CSV with columns:
```csv
disease,location,date,cases
dengue,Meerut,2026-10-01,12
influenza,Delhi,2026-10-01,8
```
Date format YYYY-MM-DD. Only import data you have permission to use. WHO FluNet data is influenza virological surveillance and needs appropriate interpretation/mapping; it is not generic case-count data.

## Notes and limitations
- Seeded health records are synthetic demonstration records.
- Social media is not representative of the population and posts are not verified cases.
- User location is not inferred from post text; fetched posts are stored with location `Unknown`.
- NLP is keyword-based and sentiment is a tiny lexicon baseline; negation, sarcasm and multilingual content are not handled reliably.
- Open-Meteo weather is contextual only; it does not prove disease causation.
- GDELT returns news coverage, not verified disease incidence.
- Map markers are illustrative known demo cities; map tiles require internet access.
- Bootstrap, Chart.js and Leaflet are loaded from CDNs, so the UI needs internet access.
- First account becomes admin. This is convenient for local demo only; secure the registration/admin process before deployment.

## Before deployment
Set a strong SECRET_KEY, use HTTPS, disable debug mode, add CSRF protection and rate limiting, review API terms, validate all input, implement retention/deletion policies, and obtain required ethics/privacy approvals. This is not production-hardened.
