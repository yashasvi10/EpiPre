import os, csv, io, re, json, html, time
from datetime import datetime, date, timedelta
from functools import wraps
from collections import Counter
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "epipre-local-dev-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "epipre.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
db = SQLAlchemy(app)
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "EpiPre-CollegeResearch/1.0 (academic demonstration)"})

DISEASE_TERMS = {
    "dengue": ["dengue", "breakbone fever", "platelet", "mosquito fever"],
    "influenza": ["influenza", "flu", "seasonal flu"],
    "covid-19": ["covid", "coronavirus", "sars-cov-2", "long covid"],
    "malaria": ["malaria", "plasmodium", "malarial"],
    "cholera": ["cholera", "acute watery diarrhoea", "acute watery diarrhea"],
    "chikungunya": ["chikungunya", "chikungunya fever"],
    "typhoid": ["typhoid", "enteric fever"]
}
SYMPTOMS = ["fever", "high fever", "cough", "headache", "body pain", "body ache",
            "rash", "vomiting", "diarrhea", "diarrhoea", "fatigue", "chills",
            "joint pain", "sore throat", "breathlessness", "nausea"]
POSITIVE = {"recovering", "recovered", "better", "relief", "healing", "thankful"}
NEGATIVE = {"sick", "fever", "pain", "hospital", "ill", "worse", "outbreak", "infection", "severe"}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="analyst")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class HealthReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    disease = db.Column(db.String(80), nullable=False, index=True)
    location = db.Column(db.String(100), nullable=False, index=True)
    report_date = db.Column(db.Date, nullable=False, index=True)
    cases = db.Column(db.Integer, nullable=False)
    source = db.Column(db.String(120), default="Manual / sample")

class SocialPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(40), default="Manual")
    post_text = db.Column(db.Text, nullable=False)
    disease = db.Column(db.String(80), default="Unclassified", index=True)
    symptoms = db.Column(db.String(500), default="")
    sentiment = db.Column(db.String(20), default="neutral")
    location = db.Column(db.String(100), default="Unknown", index=True)
    post_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    relevance = db.Column(db.Float, default=0.0)
    source_id = db.Column(db.String(250), unique=True)

class WeatherRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100), index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    precipitation = db.Column(db.Float)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)

class NewsItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500))
    url = db.Column(db.String(1000), unique=True)
    source = db.Column(db.String(200))
    published_at = db.Column(db.String(80))
    query_term = db.Column(db.String(120))
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    disease = db.Column(db.String(80), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    risk_score = db.Column(db.Float, nullable=False)
    risk_level = db.Column(db.String(20), nullable=False)
    anomaly = db.Column(db.Boolean, default=False)
    rationale = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default="info")
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class APIStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(80), unique=True)
    status = db.Column(db.String(30), default="Not checked")
    detail = db.Column(db.String(500), default="")
    last_checked = db.Column(db.DateTime)

def clean_html(value):
    return html.unescape(re.sub(r"<[^>]+>", " ", value or "")).strip()

def classify_text(text):
    t = (text or "").lower()
    scores = {d: sum(1 for term in terms if term in t) for d, terms in DISEASE_TERMS.items()}
    disease, score = max(scores.items(), key=lambda x: x[1])
    symptoms = [s for s in SYMPTOMS if s in t]
    words = set(re.findall(r"[a-z]+", t))
    neg = len(words & NEGATIVE); pos = len(words & POSITIVE)
    sentiment = "negative" if neg > pos else "positive" if pos > neg else "neutral"
    return (disease if score else "Unclassified"), symptoms, sentiment, min(score / 3, 1.0)

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        user = db.session.get(User, session["user_id"])
        if not user or user.role != "admin":
            flash("Administrator access required.", "danger")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper

def set_api_status(source, status, detail=""):
    item = APIStatus.query.filter_by(source=source).first()
    if not item:
        item = APIStatus(source=source); db.session.add(item)
    item.status = status
    item.detail = (detail or "")[:490]
    item.last_checked = datetime.utcnow()
    db.session.commit()

def seed_data():
    if HealthReport.query.count():
        return
    locations = [("Meerut", 28.9845, 77.7064), ("Delhi", 28.6139, 77.2090),
                 ("Lucknow", 26.8467, 80.9462), ("Jaipur", 26.9124, 75.7873)]
    diseases = list(DISEASE_TERMS.keys())[:5]
    today = date.today()
    for di, disease in enumerate(diseases):
        for li, (loc, _, _) in enumerate(locations):
            for day in range(56):
                base = 7 + ((day + li * 3 + di) % 8)
                bump = max(0, day - 42) * (1 + (di % 2))
                db.session.add(HealthReport(disease=disease, location=loc,
                    report_date=today - timedelta(days=55-day), cases=base+bump,
                    source="Synthetic demonstration data"))
    examples = [
        ("Bluesky", "Several neighbours in Meerut report high fever and body pain this week", "Meerut"),
        ("Mastodon", "Dengue awareness camp after mosquito fever reports in Delhi", "Delhi"),
        ("Manual", "Seasonal flu mentions: cough and fever in Lucknow", "Lucknow"),
        ("Manual", "Doctor advises testing for dengue when fever persists", "Meerut"),
        ("Bluesky", "I recovered and feeling better after a week", "Unknown")
    ]
    for platform, text, loc in examples:
        d, sy, sent, rel = classify_text(text)
        db.session.add(SocialPost(platform=platform, post_text=text, location=loc,
            disease=d, symptoms=", ".join(sy), sentiment=sent, relevance=rel))
    db.session.commit()

def geocode(city):
    r = HTTP.get("https://geocoding-api.open-meteo.com/v1/search",
                 params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=15)
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results: raise ValueError("Location not found by Open-Meteo geocoding.")
    x = results[0]
    return x["latitude"], x["longitude"], x.get("name", city)

def fetch_weather(city):
    lat, lon, canonical = geocode(city)
    r = HTTP.get("https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,precipitation"}, timeout=15)
    r.raise_for_status()
    current = r.json().get("current", {})
    item = WeatherRecord(location=canonical, latitude=lat, longitude=lon,
        temperature=current.get("temperature_2m"), humidity=current.get("relative_humidity_2m"),
        precipitation=current.get("precipitation"))
    db.session.add(item); db.session.commit()
    set_api_status("Open-Meteo", "Online", f"Weather fetched for {canonical}")
    return item

def save_social(platform, text, location="Unknown", source_id=None, post_date=None):
    if not text or (source_id and SocialPost.query.filter_by(source_id=source_id).first()):
        return False
    disease, symptoms, sentiment, relevance = classify_text(text)
    if disease == "Unclassified" and not symptoms:
        return False
    db.session.add(SocialPost(platform=platform, post_text=text[:5000], disease=disease,
        symptoms=", ".join(symptoms), sentiment=sentiment, relevance=relevance,
        location=location or "Unknown", source_id=source_id,
        post_date=post_date or datetime.utcnow()))
    return True

@app.route("/")
def home():
    return redirect(url_for("dashboard")) if session.get("user_id") else render_template("landing.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").lower().strip()
        password = request.form.get("password","")
        if not name or not email or len(password) < 8:
            flash("Enter a name, email and password of at least 8 characters.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("That email is already registered.", "danger")
        else:
            role = "admin" if User.query.count() == 0 else "analyst"
            user = User(name=name, email=email, password_hash=generate_password_hash(password), role=role)
            db.session.add(user); db.session.commit()
            session["user_id"] = user.id; session["user_name"] = user.name; session["role"] = user.role
            return redirect(url_for("dashboard"))
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form.get("email","").lower().strip()).first()
        if user and check_password_hash(user.password_hash, request.form.get("password","")):
            session.clear(); session["user_id"] = user.id; session["user_name"] = user.name; session["role"] = user.role
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    total_cases = db.session.query(db.func.sum(HealthReport.cases)).scalar() or 0
    latest_posts = SocialPost.query.order_by(SocialPost.post_date.desc()).limit(5).all()
    predictions = Prediction.query.order_by(Prediction.created_at.desc()).limit(5).all()
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
    locations = [x[0] for x in db.session.query(HealthReport.location).distinct().all()]
    disease_counts = db.session.query(HealthReport.disease, db.func.sum(HealthReport.cases)).group_by(HealthReport.disease).all()
    return render_template("dashboard.html", total_cases=total_cases, posts=SocialPost.query.count(),
        predictions=predictions, alerts=alerts, latest_posts=latest_posts, locations=locations,
        disease_labels=json.dumps([x[0] for x in disease_counts]),
        disease_values=json.dumps([int(x[1] or 0) for x in disease_counts]))

@app.route("/social")
@login_required
def social():
    q = request.args.get("q","").strip()
    disease = request.args.get("disease","")
    platform = request.args.get("platform","")
    query = SocialPost.query
    if q: query = query.filter(SocialPost.post_text.ilike(f"%{q}%"))
    if disease: query = query.filter_by(disease=disease)
    if platform: query = query.filter_by(platform=platform)
    posts = query.order_by(SocialPost.post_date.desc()).limit(150).all()
    symptom_counts = Counter(s for p in posts for s in (p.symptoms or "").split(", ") if s)
    return render_template("social.html", posts=posts, q=q, disease=disease, platform=platform,
        diseases=sorted(DISEASE_TERMS), symptoms=symptom_counts.most_common(8))

@app.route("/health")
@login_required
def health():
    disease = request.args.get("disease", "dengue")
    location = request.args.get("location", "Meerut")
    rows = HealthReport.query.filter_by(disease=disease, location=location).order_by(HealthReport.report_date.asc()).all()
    labels = [r.report_date.strftime("%d %b") for r in rows]
    values = [r.cases for r in rows]
    locations = [x[0] for x in db.session.query(HealthReport.location).distinct().all()]
    all_diseases = sorted(DISEASE_TERMS)
    comparison = {}
    for d in all_diseases:
        comparison[d] = int(db.session.query(db.func.sum(HealthReport.cases)).filter_by(disease=d, location=location).scalar() or 0)
    weather = WeatherRecord.query.filter_by(location=location).order_by(WeatherRecord.fetched_at.desc()).first()
    return render_template("health.html", disease=disease, location=location, locations=locations,
        labels=json.dumps(labels), values=json.dumps(values), diseases=all_diseases,
        comparison=json.dumps(comparison), weather=weather)

@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    result = None
    locations = [x[0] for x in db.session.query(HealthReport.location).distinct().all()]
    if request.method == "POST":
        disease = request.form.get("disease","dengue")
        location = request.form.get("location","Meerut").strip()
        reports = HealthReport.query.filter_by(disease=disease, location=location).order_by(HealthReport.report_date.desc()).limit(14).all()
        previous = HealthReport.query.filter_by(disease=disease, location=location).order_by(HealthReport.report_date.desc()).offset(14).limit(14).all()
        vals = [r.cases for r in reports]; prev = [r.cases for r in previous]
        avg = sum(vals)/len(vals) if vals else 0
        prev_avg = sum(prev)/len(prev) if prev else avg
        posts = SocialPost.query.filter_by(disease=disease, location=location).count()
        growth = ((avg-prev_avg)/prev_avg) if prev_avg else 0
        social_signal = min(posts/10, 1)
        # Explainable rule-based indicator; intentionally no machine-learning model.
        score = max(0, min(100, 35 + growth*30 + social_signal*15))
        anomaly = bool(prev_avg and avg > prev_avg * 1.5)
        level = "High" if score >= 70 else "Moderate" if score >= 45 else "Low"
        rationale = (f"Recent 14-day case average: {avg:.1f}; previous 14-day average: {prev_avg:.1f}; "
                     f"matching local social posts: {posts}; period growth: {growth*100:.1f}%. "
                     f"Statistical anomaly flag: {'Yes' if anomaly else 'No'}. This is a transparent heuristic, not a trained ML forecast.")
        result = Prediction(disease=disease, location=location, risk_score=round(score,1),
            risk_level=level, anomaly=anomaly, rationale=rationale)
        db.session.add(result)
        if level in ("High","Moderate") or anomaly:
            db.session.add(Alert(title=f"{level} {disease} signal in {location}",
                message=rationale, severity="danger" if level=="High" or anomaly else "warning"))
        db.session.commit()
    return render_template("predict.html", result=result, diseases=sorted(DISEASE_TERMS), locations=locations)

@app.route("/alerts")
@login_required
def alerts():
    return render_template("alerts.html", alerts=Alert.query.order_by(Alert.created_at.desc()).all())

@app.route("/alerts/<int:alert_id>/read", methods=["POST"])
@login_required
def mark_alert(alert_id):
    item = db.session.get(Alert, alert_id)
    if item:
        item.is_read = True; db.session.commit()
    return redirect(url_for("alerts"))

@app.route("/import-csv", methods=["GET", "POST"])
@login_required
def import_csv():
    if request.method == "POST":
        upload = request.files.get("file")
        if not upload or not upload.filename.lower().endswith(".csv"):
            flash("Choose a CSV file.", "danger"); return redirect(url_for("import_csv"))
        try:
            reader = csv.DictReader(io.StringIO(upload.stream.read().decode("utf-8-sig")))
            required = {"disease","location","date","cases"}
            if not required.issubset(set(reader.fieldnames or [])):
                raise ValueError("Required columns: disease, location, date, cases")
            count = 0
            for row in reader:
                db.session.add(HealthReport(disease=row["disease"].strip().lower(),
                    location=row["location"].strip(), report_date=datetime.strptime(row["date"],"%Y-%m-%d").date(),
                    cases=max(0,int(row["cases"])), source="CSV import")); count += 1
            db.session.commit(); flash(f"Imported {count} records.", "success")
        except Exception as e:
            db.session.rollback(); flash(f"Import failed: {e}", "danger")
        return redirect(url_for("health"))
    return render_template("import.html")

@app.route("/api/social/bluesky", methods=["POST"])
@login_required
def fetch_bluesky():
    term = (request.json or {}).get("term","dengue").strip()
    try:
        r = HTTP.get("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
                     params={"q":term,"limit":50},timeout=20); r.raise_for_status()
        added = 0
        for item in r.json().get("posts",[]):
            post = item.get("post",{}); rec = post.get("record",{})
            text = rec.get("text","")
            if save_social("Bluesky", text, "Unknown", post.get("uri")): added += 1
        db.session.commit(); set_api_status("Bluesky","Online",f"Fetched {added} relevant new posts for '{term}'")
        return jsonify(success=True, added=added, note="Public posts imported; author location is not inferred.")
    except Exception as e:
        db.session.rollback(); set_api_status("Bluesky","Error",str(e))
        return jsonify(success=False,error=str(e)),502

@app.route("/api/social/mastodon", methods=["POST"])
@login_required
def fetch_mastodon():
    data = request.json or {}
    tag = re.sub(r"[^a-zA-Z0-9_]", "", data.get("tag","dengue")).strip()
    instance = data.get("instance","https://mastodon.social").strip().rstrip("/")
    if not instance.startswith("https://"): return jsonify(success=False,error="Use an HTTPS Mastodon instance URL."),400
    try:
        r = HTTP.get(f"{instance}/api/v1/timelines/tag/{tag}",params={"limit":40},timeout=20); r.raise_for_status()
        added = 0
        for item in r.json():
            text = clean_html(item.get("content",""))
            if save_social("Mastodon",text,"Unknown",f"{instance}:{item.get('id')}"): added += 1
        db.session.commit(); set_api_status("Mastodon","Online",f"Fetched {added} relevant new posts for #{tag} from {instance}")
        return jsonify(success=True,added=added,note="Public hashtag timeline; access depends on instance settings.")
    except Exception as e:
        db.session.rollback(); set_api_status("Mastodon","Error",str(e))
        return jsonify(success=False,error=str(e)),502

@app.route("/api/weather", methods=["POST"])
@login_required
def weather_api():
    city = (request.json or {}).get("city","Meerut").strip()
    try:
        w = fetch_weather(city)
        return jsonify(success=True,location=w.location,temperature=w.temperature,humidity=w.humidity,
                       precipitation=w.precipitation,latitude=w.latitude,longitude=w.longitude)
    except Exception as e:
        set_api_status("Open-Meteo","Error",str(e)); return jsonify(success=False,error=str(e)),502

@app.route("/api/news", methods=["POST"])
@login_required
def news_api():
    term = (request.json or {}).get("term","dengue").strip()
    try:
        params = {"query":f'"{term}" AND (outbreak OR disease OR cases OR health)',
            "mode":"ArtList","format":"json","maxrecords":30,"sort":"DateDesc"}
        r = HTTP.get("https://api.gdeltproject.org/api/v2/doc/doc",params=params,timeout=25); r.raise_for_status()
        articles = r.json().get("articles",[]); added=0
        for a in articles:
            url = a.get("url")
            if url and not NewsItem.query.filter_by(url=url).first():
                db.session.add(NewsItem(title=a.get("title","")[:500],url=url,
                    source=a.get("domain","GDELT"),published_at=a.get("seendate",""),query_term=term)); added+=1
        db.session.commit(); set_api_status("GDELT","Online",f"Fetched {added} new news links for {term}")
        return jsonify(success=True,added=added)
    except Exception as e:
        set_api_status("GDELT","Error",str(e)); return jsonify(success=False,error=str(e)),502

@app.route("/api/monitor", methods=["POST"])
@login_required
def monitor_all():
    """Convenience refresh: tries selected social connectors and news; each result is independent."""
    data = request.json or {}; term = data.get("term","dengue")
    results = {}
    with app.test_request_context():
        pass
    # Run the public connectors inline so one provider failure does not stop others.
    try:
        r=HTTP.get("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",params={"q":term,"limit":30},timeout=15); r.raise_for_status()
        n=0
        for x in r.json().get("posts",[]):
            p=x.get("post",{}); rec=p.get("record",{})
            if save_social("Bluesky",rec.get("text",""),"Unknown",p.get("uri")): n+=1
        db.session.commit(); set_api_status("Bluesky","Online",f"{n} new posts"); results["Bluesky"]=f"{n} new"
    except Exception as e:
        db.session.rollback(); set_api_status("Bluesky","Error",str(e)); results["Bluesky"]="Unavailable"
    try:
        params={"query":f'"{term}" AND (outbreak OR disease OR cases)',"mode":"ArtList","format":"json","maxrecords":20,"sort":"DateDesc"}
        r=HTTP.get("https://api.gdeltproject.org/api/v2/doc/doc",params=params,timeout=20); r.raise_for_status()
        n=0
        for a in r.json().get("articles",[]):
            u=a.get("url")
            if u and not NewsItem.query.filter_by(url=u).first():
                db.session.add(NewsItem(title=a.get("title","")[:500],url=u,source=a.get("domain","GDELT"),published_at=a.get("seendate",""),query_term=term)); n+=1
        db.session.commit(); set_api_status("GDELT","Online",f"{n} new articles"); results["GDELT"]=f"{n} new"
    except Exception as e:
        db.session.rollback(); set_api_status("GDELT","Error",str(e)); results["GDELT"]="Unavailable"
    return jsonify(success=True,results=results)

@app.route("/api/summary")
@login_required
def api_summary():
    return jsonify(health_records=HealthReport.query.count(),social_posts=SocialPost.query.count(),
        predictions=Prediction.query.count(),alerts=Alert.query.count(),news=NewsItem.query.count())

@app.route("/export/health.csv")
@login_required
def export_health():
    out=io.StringIO(); w=csv.writer(out); w.writerow(["disease","location","date","cases","source"])
    for r in HealthReport.query.order_by(HealthReport.report_date.desc()).all():
        w.writerow([r.disease,r.location,r.report_date.isoformat(),r.cases,r.source])
    return send_file(io.BytesIO(out.getvalue().encode()),mimetype="text/csv",as_attachment=True,download_name="epipre_health_data.csv")

@app.route("/admin")
@admin_required
def admin():
    users=User.query.order_by(User.created_at.asc()).all()
    statuses=APIStatus.query.order_by(APIStatus.source.asc()).all()
    return render_template("admin.html",users=users,statuses=statuses,
        totals={"health":HealthReport.query.count(),"social":SocialPost.query.count(),"news":NewsItem.query.count()})

@app.route("/admin/user/<int:user_id>/role",methods=["POST"])
@admin_required
def change_role(user_id):
    user=db.session.get(User,user_id)
    if user and user.id != session["user_id"]:
        user.role=request.form.get("role","analyst") if request.form.get("role") in ("admin","analyst") else "analyst"
        db.session.commit()
    return redirect(url_for("admin"))

@app.route("/news")
@login_required
def news():
    items=NewsItem.query.order_by(NewsItem.fetched_at.desc()).limit(100).all()
    return render_template("news.html",items=items)

with app.app_context():
    db.create_all()
    seed_data()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG","0")=="1")
