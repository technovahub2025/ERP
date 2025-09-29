import os
import time
import csv
import requests
from flask import Flask, request, render_template, send_file
from dotenv import load_dotenv

load_dotenv()
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

app = Flask(__name__)

WHATSAPP_API_URL = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

def send_template_message(phone, template_name, language, variables):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    components = []
    if variables:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": str(v)} for v in variables]
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": components
        }
    }
    r = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
    return r.json()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        template_name = request.form["template_name"]
        language = request.form["language"]
        csv_file = request.files["csv_file"]

        reader = csv.DictReader(csv_file.stream.read().decode("utf-8").splitlines())
        results = []
        for row in reader:
            phone = row["phone"]
            variables = [row[col] for col in row if col.startswith("var")]
            res = send_template_message(phone, template_name, language, variables)
            results.append({"phone": phone, "response": res})
            time.sleep(1)  # avoid rate limits

        with open("results.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["phone", "response"])
            writer.writeheader()
            for r in results:
                writer.writerow(r)

        return send_file("results.csv", as_attachment=True)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True,port=5001)
