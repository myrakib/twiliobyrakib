from flask import Flask, render_template_string, request, session, jsonify
from twilio.rest import Client
from datetime import timezone, timedelta

app = Flask(__name__)
app.secret_key = "change_this_secret"

client = None
numbers_cache = []
search_results = []

BD_TZ = timezone(timedelta(hours=6))


def to_bd_time(dt):
    if not dt:
        return "Unknown"
    return dt.replace(tzinfo=timezone.utc).astimezone(BD_TZ).strftime("%I:%M %p %d-%m-%Y")


HTML = """
<!doctype html>
<html>
<head>
<style>
body { font-family: Arial; margin:20px; }
.box { border:1px solid #ddd; padding:10px; margin-bottom:10px; border-radius:8px; }
.row { display:flex; justify-content:space-between; margin:5px 0; }
button { padding:6px 10px; border:none; border-radius:5px; cursor:pointer; }
.red { background:#e74c3c; color:white; }
.green { background:#2ecc71; color:white; }
.blue { background:#3498db; color:white; }

.sms { border-bottom:1px solid #eee; padding:5px; }
.from { font-weight:bold; }
.time { font-size:12px; color:gray; }

.footer { text-align:center; font-size:13px; color:gray; margin-top:10px; }
</style>
</head>
<body>

<h2>📱 id and token </h2>

<div class="footer">
Creator: <b>Rakibul Islam tg @mri013</b>
</div>

{% if not session.get('logged_in') %}

<div class="box">
<h3>Login</h3>
<form method="POST">
    <input name="sid" placeholder="ID" required><br><br>
    <input name="token" placeholder="TOKEN" required><br><br>
    <button class="blue" name="action" value="login">Login</button>
</form>
</div>

{% else %}

<!-- SEARCH -->
<div class="box">
<h3>🌍 find Numbers</h3>

<form method="POST">
    <select name="country">
        
        <option value="CA">🇨🇦 CA</option>
    </select>

    <input name="area" placeholder="Area code (optional)">
    <button class="green" name="action" value="search">Search</button>
</form>
</div>

<!-- RESULTS -->
{% if search_results %}
<div class="box">
<h3>📋 Available Numbers</h3>

{% for n in search_results %}
<div class="row">
    <span>{{ n }}</span>

    <form method="POST">
        <input type="hidden" name="number" value="{{ n }}">
        <button class="blue" name="action" value="buy">Buy</button>
    </form>
</div>
{% endfor %}
</div>
{% endif %}

<!-- OWNED -->
<div class="box">
<h3>📞 My Numbers</h3>

{% for n in numbers %}
<div class="row">
    <span>{{ n }}</span>

    <form method="POST">
        <input type="hidden" name="number" value="{{ n }}">
        <button class="red" name="action" value="delete">Delete</button>
    </form>
</div>
{% endfor %}
</div>

<!-- SMS -->
<div class="box">
<h3>📩 SMS Inbox</h3>
<button onclick="loadSMS()" class="green">GET CODE</button>
<div id="smsBox"></div>
</div>

<form method="POST">
    <button class="red" name="action" value="logout">Logout</button>
</form>

{% endif %}

<script>
function loadSMS(){
    fetch('/?action=sms')
    .then(r => r.json())
    .then(data => {
        let box = document.getElementById("smsBox");
        box.innerHTML = "";

        data.messages.forEach(m => {
            box.innerHTML += `
                <div class="sms">
                    <div class="from">${m.from}</div>
                    <div>${m.body}</div>
                    <div class="time">${m.time}</div>
                </div>
            `;
        });
    });
}
</script>

</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    global client, numbers_cache, search_results

    action = request.args.get("action") or request.form.get("action")

    if action == "login":
        sid = request.form["sid"]
        token = request.form["token"]

        client = Client(sid, token)
        session["logged_in"] = True
        refresh_numbers()

    elif action == "logout":
        client = None
        numbers_cache = []
        search_results = []
        session.clear()

    elif action == "search" and client:
        country = request.form["country"]
        area = request.form.get("area")

        query = client.available_phone_numbers(country).local

        result = query.list(area_code=area, limit=10)
        search_results = [n.phone_number for n in result]

    elif action == "buy" and client:
        number = request.form["number"]

        client.incoming_phone_numbers.create(phone_number=number)
        refresh_numbers()

    elif action == "delete" and client:
        number = request.form["number"]

        for n in client.incoming_phone_numbers.list():
            if n.phone_number == number:
                client.incoming_phone_numbers(n.sid).delete()

        refresh_numbers()

    elif action == "sms" and client:
        msgs = client.messages.list(limit=30)

        data = []
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
        numbers=numbers_cache,
        search_results=search_results
    )


def refresh_numbers():
    global numbers_cache
    if client:
        numbers_cache = [n.phone_number for n in client.incoming_phone_numbers.list()]


if __name__ == "__main__":
    app.run(debug=True)
