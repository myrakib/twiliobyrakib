from flask import Flask, render_template_string, request, session, jsonify
from twilio.rest import Client
from datetime import timezone, timedelta

app = Flask(__name__)
app.secret_key = "change_this_secret"

BD_TZ = timezone(timedelta(hours=6))


def to_bd_time(dt):
    if not dt:
        return "Unknown"
    return dt.replace(tzinfo=timezone.utc).astimezone(BD_TZ).strftime("%I:%M %p %d-%m-%Y")


# ---------------- CLIENT ----------------
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
    max-width: 90%;
    background:#dff7ff;
    border-left:5px solid #00aaff;
}

.from { font-weight:bold; }
.time { font-size:12px; color:gray; }

</style>

{% if not session.get('logged_in') %}

<div class="card">
<h2>🔐 Login</h2>          <h1>✨ Welcome to My Website ✨

👋 I am Rakibul Islam, the proud owner of this platform. <h1>🔐If you need a id:token contrac who share is app/website you </h2> 
<form method="POST">
    <input name="credentials" placeholder="ID:TOKEN" style="width:100%;padding:10px;">
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
     
        <option value="CA">🇨🇦 CA</option>
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

<!-- 🔊 SOUND -->
<audio id="notifySound" preload="auto">
    <source src="https://www.soundjay.com/buttons/sounds/button-3.mp3" type="audio/mpeg">
</audio>

<!-- 🔔 PERMISSION + SOUND UNLOCK -->
<script>
let soundEnabled = false;
let notifEnabled = false;

/* Ask notification permission on open */
window.addEventListener("load", async () => {
    if ("Notification" in window) {
        const perm = await Notification.requestPermission();
        notifEnabled = perm === "granted";
    }
});

/* unlock sound on first user click */
document.addEventListener("click", () => {
    const audio = document.getElementById("notifySound");

    audio.play().then(() => {
        audio.pause();
        audio.currentTime = 0;
        soundEnabled = true;
    }).catch(() => {});
});
</script>

<!-- 💬 SMS LOGIC -->
<script>
let lastCount = 0;

async function loadSMS() {
    try {
        const res = await fetch("/?action=sms");
        const data = await res.json();

        const messages = data.messages;

        // 🔔 NEW SMS DETECTED
        if (messages.length > lastCount) {

            // 🔊 SOUND
            if (soundEnabled) {
                const sound = document.getElementById("notifySound");
                sound.currentTime = 0;
                sound.play().catch(() => {});
            }

            // 🔔 BROWSER NOTIFICATION
            if (notifEnabled && messages.length > 0) {
                const latest = messages[0];

                new Notification("📩 New SMS", {
                    body: latest.from + ": " + latest.body
                });
            }
        }

        lastCount = messages.length;

        let html = "";

        messages.forEach(m => {
            html += `
            <div class="sms">
                <div class="from">📩 ${m.from}</div>
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


# ---------------- APP ----------------
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
            area = request.form.get("area")

            query = client.available_phone_numbers(country).local

            kwargs = {"limit": 10}
            if area:
                kwargs["area_code"] = int(area)

            result = query.list(**kwargs)

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

                data.append({
                    "from": m.from_,
                    "body": m.body,
                    "time": to_bd_time(m.date_sent)
                })

        return jsonify({"messages": data})

    return render_template_string(
        HTML,
        numbers=session.get("numbers_cache", []),
        search_results=session.get("search_results", [])
    )


if __name__ == "__main__":
    app.run(debug=True)
