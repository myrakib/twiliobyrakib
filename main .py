from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
from twilio.rest import Client
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
app.secret_key = "change_this_secret"

client = None
last_seen_time = None
numbers_cache = []
my_numbers_cache = []

# =========================
# 🇧🇩 BANGLADESH TIME
# =========================

BD_TZ = timezone(timedelta(hours=6))

def to_bd_time(dt):
    if not dt:
        return "Unknown"
    return dt.replace(tzinfo=timezone.utc).astimezone(BD_TZ).strftime("%I:%M %p  %d-%m-%Y")

# =========================
# UI
# =========================

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Twilio Dashboard</title>
    <style>
        body {margin:0;font-family:Arial;background:linear-gradient(135deg,#eef2ff,#ffe4f1);}
        .container{max-width:900px;margin:auto;padding:20px;}
        .card{background:white;padding:18px;border-radius:14px;margin-bottom:15px;box-shadow:0 10px 25px rgba(0,0,0,0.08);}
        h2{color:#d63384;}
        input{width:100%;padding:10px;margin:6px 0;border-radius:10px;border:1px solid #ddd;}
        button{padding:10px;width:100%;border:none;border-radius:10px;background:linear-gradient(135deg,#ff4d8d,#ff2e63);color:white;font-weight:bold;cursor:pointer;margin-top:5px;}
        button:hover{opacity:0.9;}

        .sms{padding:10px;border-bottom:1px solid #eee;}
        .from{font-weight:bold;}
        .body{color:#555;}
        .time{font-size:12px;color:#888;}
        .inbox{max-height:300px;overflow-y:auto;}

        .tag{display:flex;justify-content:space-between;align-items:center;
              padding:8px;background:#f1f1f1;border-radius:8px;margin:5px;}

        .btn-red{background:linear-gradient(135deg,#ff3b3b,#b30000)!important;width:auto;padding:5px 8px;}

        .btn-dark{background:#333!important;}

        #lastTime{color:#666;margin-bottom:10px;}

        .footer{
            text-align:center;
            margin-top:20px;
            color:#888;
            font-size:13px;
        }
    </style>
</head>
<body>

<div class="container">

<h2>📞 Twilio Dashboard</h2>

{% for m in get_flashed_messages() %}
<div class="sms">{{ m }}</div>
{% endfor %}

{% if not session.get('logged_in') %}

<div class="card">
    <h3>Login</h3>
    <form method="POST" action="/login">
        <input name="sid" placeholder="Twilio SID" required>
        <input name="token" placeholder="Twilio Auth Token" required>
        <button>Login</button>
    </form>
</div>

{% else %}

<!-- MY NUMBERS -->
<div class="card">
    <h3>📱 My Twilio Numbers</h3>

    {% if my_numbers %}
        {% for n in my_numbers %}
        <div class="tag">
            <span>{{ n }}</span>

            <!-- DELETE BUTTON -->
            <form method="POST" action="/delete-number">
                <input type="hidden" name="number" value="{{ n }}">
                <button class="btn-red">🗑️ Delete</button>
            </form>
        </div>
        {% endfor %}
    {% else %}
        <i>No numbers found</i>
    {% endif %}

    <hr>

    <!-- DELETE ALL -->
    <form method="POST" action="/delete-all-numbers">
        <button class="btn-dark">🗑️ Delete ALL Numbers</button>
    </form>

    <br>

    <!-- CUSTOM DELETE -->
    <form method="POST" action="/delete-custom-number">
        <input name="number" placeholder="Enter number to delete">
        <button class="btn-red">✍️ Delete Custom Number</button>
    </form>
</div>

<!-- LIVE SMS -->
<div class="card">
    <h3>📩 Live SMS</h3>

    <div id="lastTime">🕒 Loading...</div>
    <div class="inbox" id="inbox">Loading...</div>

    <form method="GET" action="/old-sms">
        <button class="btn-dark">📜 Old SMS</button>
    </form>
</div>

<!-- OLD SMS -->
{% if old_messages %}
<div class="card">
    <h3>📜 Old SMS</h3>

    {% for m in old_messages %}
    <div class="sms">
        <div class="from">{{ m.from }}</div>
        <div class="body">{{ m.body }}</div>
        <div class="time">🕒 {{ m.time }}</div>
    </div>
    {% endfor %}
</div>
{% endif %}

<div class="card">
    <a href="/logout"><button class="btn-dark">Logout</button></a>
</div>

{% endif %}

<div class="footer">
    Created by <b>Rakibul Islam</b>
</div>

</div>

<script>
let lastData = "";
let notified = new Set();

if ("Notification" in window) {
    Notification.requestPermission();
}

function notify(msg) {
    if (Notification.permission === "granted") {
        new Notification("📩 New SMS", {
            body: `From: ${msg.from} → ${msg.body}`
        });
    }
}

async function loadInbox() {
    const res = await fetch("/api/messages");
    const data = await res.json();

    let str = JSON.stringify(data);
    if (str === lastData) return;
    lastData = str;

    data.messages.forEach(m => {
        let key = m.from + m.body;
        if (!notified.has(key)) {
            notified.add(key);
            notify(m);
        }
    });

    document.getElementById("inbox").innerHTML =
        data.messages.length === 0
        ? "<i>No new messages</i>"
        : data.messages.map(m => `
            <div class="sms">
                <div class="from">${m.from}</div>
                <div class="body">${m.body}</div>
                <div class="time">🕒 ${m.time}</div>
            </div>
        `).join("");

    if (data.last_time) {
        document.getElementById("lastTime").innerHTML =
            "🕒 Last SMS: " + data.last_time;
    }
}

setInterval(loadInbox, 3000);
loadInbox();
</script>

</body>
</html>
"""

# =========================
# ROUTES
# =========================

@app.route("/")
def index():
    return render_template_string(
        TEMPLATE,
        numbers=numbers_cache,
        my_numbers=my_numbers_cache,
        old_messages=None
    )

@app.route("/login", methods=["POST"])
def login():
    global client, my_numbers_cache

    sid = request.form["sid"]
    token = request.form["token"]

    client = Client(sid, token)
    session["logged_in"] = True

    nums = client.incoming_phone_numbers.list()
    my_numbers_cache = [n.phone_number for n in nums]

    flash("Login successful")
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    global client, my_numbers_cache, numbers_cache, last_seen_time

    client = None
    my_numbers_cache = []
    numbers_cache = []
    last_seen_time = None
    session.clear()

    flash("Logged out")
    return redirect(url_for("index"))

# =========================
# DELETE SINGLE NUMBER
# =========================

@app.route("/delete-number", methods=["POST"])
def delete_number():
    number = request.form.get("number")

    nums = client.incoming_phone_numbers.list()
    for n in nums:
        if n.phone_number == number:
            client.incoming_phone_numbers(n.sid).delete()

    refresh_numbers()
    flash("Number deleted")
    return redirect(url_for("index"))

# =========================
# DELETE ALL NUMBERS
# =========================

@app.route("/delete-all-numbers", methods=["POST"])
def delete_all_numbers():
    nums = client.incoming_phone_numbers.list()

    for n in nums:
        client.incoming_phone_numbers(n.sid).delete()

    refresh_numbers()
    flash("All numbers deleted")
    return redirect(url_for("index"))

# =========================
# CUSTOM DELETE
# =========================

@app.route("/delete-custom-number", methods=["POST"])
def delete_custom_number():
    number = request.form.get("number")

    nums = client.incoming_phone_numbers.list()

    for n in nums:
        if n.phone_number == number:
            client.incoming_phone_numbers(n.sid).delete()

    refresh_numbers()
    flash("Custom number deleted")
    return redirect(url_for("index"))

# =========================
# HELPERS
# =========================

def refresh_numbers():
    global my_numbers_cache
    my_numbers_cache = [n.phone_number for n in client.incoming_phone_numbers.list()]

# =========================
# SMS API
# =========================

@app.route("/api/messages")
def api_messages():
    msgs = client.messages.list(limit=50)

    incoming = []
    seen = set()

    for m in msgs:
        if m.direction != "inbound":
            continue
        if m.sid in seen:
            continue
        seen.add(m.sid)

        incoming.append({
            "from": m.from_,
            "body": m.body,
            "time": to_bd_time(m.date_sent)
        })

    return jsonify({
        "messages": incoming,
        "last_time": "Live"
    })

# =========================
# RUN
# =========================

if __name__ == "__main__":
    app.run(debug=True)