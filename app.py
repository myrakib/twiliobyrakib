from flask import Flask, render_template_string, request, session, jsonify
from twilio.rest import Client
from datetime import timezone, timedelta
import re

app = Flask(__name__)
app.secret_key = "change_this_secret"

BD_TZ = timezone(timedelta(hours=6))


# ---------------- TIME ----------------
def to_bd_time(dt):
    if not dt:
        return "Unknown"
    return dt.replace(tzinfo=timezone.utc).astimezone(BD_TZ).strftime("%I:%M %p %d-%m-%Y")


# ---------------- OTP ----------------
def extract_otp(text):
    match = re.search(r"\b\d{4,8}\b", text or "")
    return match.group(0) if match else ""


# ---------------- FACEBOOK / INSTAGRAM DETECTOR ----------------
def get_special_service(body):
    text = (body or "").lower()

    if "facebook" in text or "fb" in text:
        return {
            "name": "Facebook Login",
            "logo": "https://cdn.simpleicons.org/facebook",
            "color": "#1877F2"
        }

    if "instagram" in text or "insta" in text:
        return {
            "name": "Instagram Login",
            "logo": "https://cdn.simpleicons.org/instagram",
            "color": "#E4405F"
        }

    return None


# ---------------- TWILIO ----------------
def get_client():
    sid = session.get("sid")
    token = session.get("token")

    if not sid or not token:
        return None

    return Client(sid, token)


def refresh_numbers():
    client = get_client()
    if client:
        session["numbers_cache"] = [
            n.phone_number for n in client.incoming_phone_numbers.list()
        ]


# ---------------- UI ----------------
HTML = """
<style>
body {
    font-family: Arial;
    background: #f2f6ff;
    padding: 20px;
}

.card {
    background: white;
    padding: 15px;
    border-radius: 12px;
    margin-bottom: 15px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

h2 { color: #2b6cff; }

button {
    padding: 10px 15px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: bold;
}

.buy { background: #2ecc71; color: white; }
.delete { background: #e74c3c; color: white; }
.search { background: #3498db; color: white; }
.logout { background: #555; color: white; }

.number {
    font-size: 18px;
    padding: 8px;
    background: #eef3ff;
    margin: 5px 0;
    border-radius: 8px;
}

/* SMS */
.sms {
    padding:10px;
    margin:8px 0;
    border-radius:10px;
    background:#dff7ff;
    border-left:5px solid #00aaff;
}

.from { font-weight:bold; }
.time { font-size:12px; color:gray; }

.otp {
    font-size:24px;
    font-weight:bold;
    color:#2b6cff;
    background:#eef3ff;
    padding:8px;
    border-radius:8px;
    text-align:center;
    margin:8px 0;
}

.service {
    display:flex;
    align-items:center;
    gap:8px;
    margin-bottom:6px;
    font-weight:bold;
}
</style>

{% if not session.get('logged_in') %}

<div class="card">
<h2>🔐 Login</h2>          <h1>✨ Welcome to My Website ✨

👋 I am Rakibul Islam, the proud owner of this platform. <h1>🔐If you need a id:token contrac who share is app/website you </h2> 
<form method="POST">
    <input name="credentials" placeholder="SID:TOKEN" style="width:100%;padding:10px;">
    <br><br>
    <button class="search" name="action" value="login">Login</button>
</form>
</div>

{% else %}

<div class="card">
<h2>📱 Your Numbers</h2>

{% if numbers %}
    {% for n in numbers %}
        <div class="number">📞 {{ n }}</div>
    {% endfor %}
{% else %}
    <p>No numbers yet.</p>
{% endif %}
</div>

<div class="card">
<h2>🔎 Search Numbers</h2>
<form method="POST">
    <select name="country">
        
        <option value="CA">canada CA😊😊</option>
    </select>

    <input name="area" placeholder="Area code (optional)">
    <button class="search" name="action" value="search">Search</button>
</form>
</div>

<div class="card">
<h2>🛒 Buy Numbers (Top 5)</h2>

{% for n in search_results[:5] %}
    <div class="number">
        {{ n }}
        <form method="POST" style="display:inline;">
            <input type="hidden" name="number" value="{{ n }}">
            <button class="buy" name="action" value="buy">Buy</button>
        </form>
    </div>
{% endfor %}
</div>

<div class="card">
<h2>🗑 Manage Numbers</h2>

{% for n in numbers %}
<form method="POST">
    <input type="hidden" name="number" value="{{ n }}">
    <button class="delete" name="action" value="delete">Delete {{ n }}</button>
</form>
{% endfor %}
</div>

<div class="card">
<form method="POST">
    <button class="logout" name="action" value="logout">Logout</button>
</form>
</div>

<!-- SMS -->
<div class="card">
<h2>💬 Live SMS</h2>
<div id="sms-box"></div>
</div>

<!-- SOUND -->
<audio id="notifySound" preload="auto">
    <source src="https://www.soundjay.com/buttons/sounds/button-3.mp3" type="audio/mpeg">
</audio>

<script>
let lastCount = 0;
let soundEnabled = false;
let notifEnabled = false;

/* notification permission */
window.addEventListener("load", async () => {
    if ("Notification" in window) {
        const perm = await Notification.requestPermission();
        notifEnabled = perm === "granted";
    }
});

/* unlock sound */
document.addEventListener("click", () => {
    const audio = document.getElementById("notifySound");

    audio.play().then(() => {
        audio.pause();
        audio.currentTime = 0;
        soundEnabled = true;
    }).catch(() => {});
});


async function loadSMS() {
    try {
        const res = await fetch("/?action=sms");
        const data = await res.json();

        const messages = data.messages;

        if (messages.length > lastCount) {

            if (soundEnabled) {
                const sound = document.getElementById("notifySound");
                sound.currentTime = 0;
                sound.play().catch(() => {});
            }

            if (notifEnabled && messages.length > 0) {
                const m = messages[0];
                new Notification("📩 New SMS", {
                    body: m.from + ": " + m.body
                });
            }
        }

        lastCount = messages.length;

        let html = "";

        messages.forEach(m => {
            html += `
            <div class="sms">

                ${m.service ? `
                <div class="service" style="color:${m.service.color}">
                    <img src="${m.service.logo}" width="20">
                    ${m.service.name}
                </div>
                ` : ""}

                <div class="from">${m.from}</div>

                ${m.otp ? `<div class="otp">🔑 ${m.otp}</div>` : ""}

                <div>${m.body}</div>
                <div class="time">${m.time}</div>
            </div>
            `;
        });

        document.getElementById("sms-box").innerHTML = html;

    } catch (e) {}
}

setInterval(loadSMS, 4000);
loadSMS();
</script>

{% endif %}
"""


# ---------------- ROUTES ----------------
@app.route("/", methods=["GET", "POST"])
def index():

    action = request.args.get("action") or request.form.get("action")

    # LOGIN
    if action == "login":
        try:
            credentials = request.form["credentials"].strip()
            sid, token = credentials.split(":", 1)

            client = Client(sid, token)
            client.api.accounts(sid).fetch()

            session["sid"] = sid
            session["token"] = token
            session["logged_in"] = True

            refresh_numbers()

        except:
            return "Invalid SID:TOKEN"

    # LOGOUT
    elif action == "logout":
        session.clear()

    # SEARCH
    elif action == "search":
        client = get_client()
        if client:
            country = request.form["country"]
            query = client.available_phone_numbers(country).local
            result = query.list(limit=10)

            session["search_results"] = [n.phone_number for n in result]

    # BUY
    elif action == "buy":
        client = get_client()
        if client:
            number = request.form["number"]
            client.incoming_phone_numbers.create(phone_number=number)
            refresh_numbers()

    # DELETE
    elif action == "delete":
        client = get_client()
        if client:
            number = request.form["number"]
            for n in client.incoming_phone_numbers.list():
                if n.phone_number == number:
                    client.incoming_phone_numbers(n.sid).delete()
                    break
            refresh_numbers()

    # SMS API
    elif action == "sms":
        client = get_client()

        data = []

        if client:
            msgs = client.messages.list(limit=30)

            for m in msgs:
                if m.direction != "inbound":
                    continue

                body = m.body or ""

                service = get_special_service(body)

                data.append({
                    "from": m.from_,
                    "body": body,
                    "time": to_bd_time(m.date_sent),
                    "service": service,
                    "otp": extract_otp(body)
                })

        return jsonify({"messages": data})

    return render_template_string(
        HTML,
        numbers=session.get("numbers_cache", []),
        search_results=session.get("search_results", [])
    )


if __name__ == "__main__":
    app.run(debug=True)
