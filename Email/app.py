import os, csv, json, smtplib, ssl, uuid, shutil
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler # type: ignore
from apscheduler.triggers.cron import CronTrigger # type: ignore
from dotenv import load_dotenv

load_dotenv()

# --- Paths & config ---
ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT, "frontend")
DATA_DIR = os.path.join(ROOT, "data")
TMP_DIR = os.path.join(DATA_DIR, "tmp")
PAYS_DIR = os.path.join(DATA_DIR, "payslips")
JOBS_DIR = os.path.join(DATA_DIR, "jobs")
RECIPIENTS_FILE = os.path.join(ROOT, "recipients.csv")
SCHEDULE_FILE = os.path.join(ROOT, "schedule.json")

for p in (DATA_DIR, TMP_DIR, PAYS_DIR, JOBS_DIR):
    os.makedirs(p, exist_ok=True)

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
TZ = os.getenv("TIMEZONE", "Asia/Kolkata")
PORT = int(os.getenv("PORT", "5000"))

app = Flask(__name__, static_folder=None)  # we’ll serve frontend manually
scheduler = BackgroundScheduler(timezone=TZ)
scheduler.start()

# Keep reference to current cron job so we can reschedule
cron_job_id = "monthly_payslip_job"

# ---------- Helpers ----------
def write_job(job_id, obj):
    with open(os.path.join(JOBS_DIR, f"{job_id}.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def read_job(job_id):
    path = os.path.join(JOBS_DIR, f"{job_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_recipients():
    rows = []
    if not os.path.exists(RECIPIENTS_FILE):
        return rows
    with open(RECIPIENTS_FILE, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows

def render_template_html(tpl_html, row):
    now = datetime.now()
    month_name = now.strftime("%B")
    year = now.strftime("%Y")
    return (tpl_html
            .replace("{{name}}", (row.get("name") or ""))
            .replace("{{month}}", month_name)
            .replace("{{year}}", year))

def send_email(to_addr, subject, html_body, attachment_path=None):
    # Basic Gmail SMTP (App Password required)
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = to_addr
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition",
                        f'attachment; filename="{os.path.basename(attachment_path)}"')
        msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, [to_addr], msg.as_string())

def run_send_job(job_id, subject, template_html, recipients):
    job = {
        "jobId": job_id,
        "subject": subject,
        "total": len(recipients),
        "sent": 0,
        "errors": [],
        "status": "running",
        "startedAt": datetime.now().isoformat()
    }
    write_job(job_id, job)

    for i, r in enumerate(recipients):
        email = (r.get("email") or "").strip()
        if not email:
            job["errors"].append({"index": i, "reason": "email missing", "row": r})
            write_job(job_id, job)
            continue

        html = render_template_html(template_html, r)

        # attachment (optional)
        attach = None
        if r.get("file"):
            candidate = os.path.join(PAYS_DIR, r["file"])
            if os.path.exists(candidate):
                attach = candidate
            else:
                job["errors"].append({"index": i, "reason": "attachment not found", "file": r["file"], "email": email})

        try:
            send_email(email, subject, html, attach)
            job["sent"] += 1
        except Exception as e:
            job["errors"].append({"index": i, "reason": str(e), "email": email})

        write_job(job_id, job)

    job["status"] = "done"
    job["finishedAt"] = datetime.now().isoformat()
    write_job(job_id, job)

# ---------- API routes ----------
@app.post("/api/uploadRecipients")
def api_upload_recipients():
    if "file" not in request.files:
        return jsonify({"message": "No file uploaded"}), 400
    f = request.files["file"]
    if not f.filename.lower().endswith(".csv"):
        return jsonify({"message": "Only CSV allowed"}), 400

    tmp_path = os.path.join(TMP_DIR, secure_filename(f.filename))
    f.save(tmp_path)
    # move/overwrite recipients.csv
    shutil.move(tmp_path, RECIPIENTS_FILE)

    # preview first 20
    preview = []
    with open(RECIPIENTS_FILE, newline="", encoding="utf-8") as csvfile:
        r = csv.DictReader(csvfile)
        for i, row in enumerate(r):
            preview.append(row)
            if i >= 19:
                break

    return jsonify({"message": "Recipients uploaded", "preview": preview})

@app.post("/api/uploadFiles")
def api_upload_files():
    if "files" not in request.files:
        return jsonify({"message": "No files field"}), 400
    files = request.files.getlist("files")
    saved = []
    for f in files:
        safe_name = secure_filename(f.filename)
        out_path = os.path.join(PAYS_DIR, safe_name)
        f.save(out_path)
        saved.append(safe_name)
    return jsonify({"message": "Files uploaded", "files": saved})

@app.post("/api/sendNow")
def api_send_now():
    data = request.get_json(silent=True) or {}
    subject = (data.get("subject") or "").strip()
    template = data.get("template") or ""
    if not subject or not template:
        return jsonify({"message": "subject and template required"}), 400
    recipients = load_recipients()
    job_id = str(uuid.uuid4())

    # fire-and-forget
    from threading import Thread
    Thread(target=run_send_job, args=(job_id, subject, template, recipients), daemon=True).start()

    return jsonify({"message": "Job started", "jobId": job_id})

@app.get("/api/status/<job_id>")
def api_status(job_id):
    job = read_job(job_id)
    if not job:
        return jsonify({"message": "job not found"}), 404
    return jsonify(job)

def schedule_from_config(config):
    # remove existing
    try:
        scheduler.remove_job(cron_job_id)
    except Exception:
        pass

    trig = CronTrigger(
        day=config["day"],
        hour=config["hour"],
        minute=config["minute"],
        timezone=TZ
    )

    def scheduled_task():
        recipients = load_recipients()
        job_id = str(uuid.uuid4())
        run_send_job(job_id, config["subject"], config["template"], recipients)

    scheduler.add_job(scheduled_task, trig, id=cron_job_id, replace_existing=True)

@app.post("/api/schedule")
def api_schedule():
    data = request.get_json(silent=True) or {}
    day = int(data.get("day", 0))
    time_str = data.get("time", "")
    subject = data.get("subject") or "Monthly Payslip"
    template = data.get("template") or ""
    try:
        hour, minute = map(int, time_str.split(":"))
    except Exception:
        return jsonify({"message": "invalid time"}), 400
    if not (1 <= day <= 28):
        return jsonify({"message": "day must be 1..28"}), 400

    config = {"day": day, "hour": hour, "minute": minute, "subject": subject, "template": template}
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    schedule_from_config(config)
    return jsonify({"message": "schedule saved"})

# Load schedule on boot (if present)
if os.path.exists(SCHEDULE_FILE):
    try:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        schedule_from_config(cfg)
    except Exception as e:
        print("Failed to load schedule:", e)

# ---------- Frontend serving ----------
@app.get("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.get("/<path:path>")
def serve_static(path):
    # allow direct loading of assets if you add CSS/JS later
    return send_from_directory(FRONTEND_DIR, path)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT, debug=True)
