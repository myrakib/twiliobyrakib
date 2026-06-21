from flask import Flask, render_template_string, request, session, jsonify
from twilio.rest import Client
from datetime import timezone, timedelta
import re

app = Flask(__name__)
app.secret_key = "change_this_secret"

BD_TZ = timezone(timedelta(hours=6))


def to_bd_time(dt):
    if not dt:
        return "Unknown"
    return dt.replace(tzinfo=timezone.utc).astimezone(BD_TZ).strftime("%I:%M %p %d-%m-%Y")


def extract_otp(text):
    match = re.search(r"\b\d{4,8}\b", text or "")
    return match.group(0) if match else ""


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


HTML = """
<style>
body{
    margin:0;
    font-family:Arial;
    overflow-x:hidden;
    background: linear-gradient(to bottom, #b3e5fc, #e1f5fe);
}

/* 🌧️ RAIN */
canvas{
    position:fixed;
    top:0;
    left:0;
    width:100%;
    height:100%;
    z-index:-999;
    pointer-events:none;
}

/* 🔝 TOP BAR (FIX LOGOUT ISSUE) */
.topbar{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:12px 15px;
    background: rgba(255,255,255,0.7);
    backdrop-filter: blur(10px);
    border-bottom:1px solid rgba(0,0,0,0.1);
}

.logout-btn{
    background:#ef5350;
    color:white;
    padding:6px 10px;
    border:none;
    border-radius:8px;
    cursor:pointer;
    font-weight:bold;
}

/* 🪟 CARDS */
.card{
    padding:15px;
    margin:15px;
    border-radius:16px;
    backdrop-filter: blur(10px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.08);
}

.blue{background: rgba(33,150,243,0.25);}
.green{background: rgba(76,175,80,0.25);}
.pink{background: rgba(233,30,99,0.25);}
.yellow{background: rgba(255,193,7,0.25);}
.purple{background: rgba(156,39,176,0.25);}

.number{
    padding:8px;
    margin:5px 0;
    border-radius:10px;
    background: rgba(255,255,255,0.7);
    display:flex;
    justify-content:space-between;
    align-items:center;
}

.copy-num{
    background:#0288d1;
    color:white;
    border:none;
    padding:4px 8px;
    border-radius:6px;
    cursor:pointer;
    font-size:12px;
}

.sms{
    padding:10px;
    margin:8px 0;
    border-radius:12px;
    background:white;
    border-left:4px solid #4fc3f7;
}

.from{font-weight:bold}
.time{font-size:12px;opacity:0.6}

.otp{
    font-size:20px;
    font-weight:bold;
    background:#e3f2fd;
    padding:6px;
    border-radius:8px;
    margin-top:5px;
}

button{
    padding:8px 12px;
    border:none;
    border-radius:8px;
    cursor:pointer;
    font-weight:bold;
}

.search{background:#42a5f5;color:white}
.buy{background:#66bb6a;color:white}

.copy-btn{
    margin-left:8px;
    background:#1e88e5;
    color:white;
    font-size:12px;
}
</style>

<canvas id="rain"></canvas>

{% if session.get('logged_in') %}

<!-- 🔝 FIXED LOGOUT ALWAYS VISIBLE -->
<div class="topbar">
    <div>Get Your Number Your Otp Rcv </div>
    <form method="POST">
        <button class="logout-btn" name="action" value="logout">🚪 Logout</button>
    </form>
</div>

<div class="card purple">
<h2>📱 YOUR NUMBERS</h2>

{% for n in numbers %}
<div class="number">
<span>📞 {{ n }}</span>

<!-- 📋 COPY NUMBER FIX -->
<button class="copy-num" onclick="navigator.clipboard.writeText('{{ n }}')">COPY</button>
</div>
{% endfor %}

</div>

<div class="card green">
<h2>🔎 SEARCH</h2>
<form method="POST">
<select name="country">
<option value="CA">🇨🇦 CA</option>
<option value="US">🇺🇸 US</option>
</select>
<input name="area" placeholder="Area code" style="padding:8px;border-radius:8px">
<button class="search" name="action" value="search">SEARCH</button>
</form>
</div>

<div class="card yellow">
<h2>🛒 BUY (TOP 5)</h2>
{% for n in search_results[:5] %}
<div class="number">
<span>{{ n }}</span>
<form method="POST">
<input type="hidden" name="number" value="{{ n }}">
<button class="buy" name="action" value="buy">BUY</button>
</form>
</div>
{% endfor %}
</div>

<div class="card pink">
<h2>💬 LIVE SMS</h2>
<div id="sms"></div>
</div>

{% else %}

<div class="card blue">
<h2>🔐 Login</h2>          <h1>✨ Welcome to My Website ✨  👋 I am Rakibul Islam, the  owner of this platform. <h1>🔐If you need a id:token contrac who share is app/website you </h2>  <form method="POST">
<input name="credentials" placeholder="SID:TOKEN" style="width:100%;padding:10px;border-radius:8px">
<br><br>
<button class="search" name="action" value="login">LOGIN</button>
</form>
</div>

{% endif %}

<script>
/* 🌧️ RAIN */
const canvas = document.getElementById("rain");
const ctx = canvas.getContext("2d");

canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

const drops = [];

for(let i=0;i<160;i++){
    drops.push({
        x: Math.random()*canvas.width,
        y: Math.random()*canvas.height,
        len: Math.random()*18+8,
        speed: Math.random()*2+1.5
    });
}

function rain(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.strokeStyle = "rgba(80,160,255,0.85)";
    ctx.lineWidth = 2;

    for(let d of drops){
        ctx.beginPath();
        ctx.moveTo(d.x,d.y);
        ctx.lineTo(d.x,d.y+d.len);
        ctx.stroke();

        d.y += d.speed;

        if(d.y > canvas.height){
            d.y = -20;
            d.x = Math.random()*canvas.width;
        }
    }
}
setInterval(rain,30);

/* 💬 SMS */
async function loadSMS(){
    const res = await fetch("/?action=sms");
    const data = await res.json();

    let html = "";

    data.messages.forEach(m=>{
        html += `
        <div class="sms">
            <div class="from">${m.from}</div>

            ${m.otp ? `
            <div class="otp">
                🔑 ${m.otp}
                <button onclick="navigator.clipboard.writeText('${m.otp}')">COPY</button>
            </div>` : ""}

            <div>${m.body}</div>
            <div class="time">${m.time}</div>
        </div>`;
    });

    document.getElementById("sms").innerHTML = html;
}

setInterval(loadSMS,4000);
loadSMS();
</script>
"""


@app.route("/", methods=["GET","POST"])
def index():

    action = request.args.get("action") or request.form.get("action")

    if action == "login":
        sid, token = request.form["credentials"].split(":",1)

        client = Client(sid, token)
        client.api.accounts(sid).fetch()

        session["sid"] = sid
        session["token"] = token
        session["logged_in"] = True

        refresh_numbers()

    elif action == "logout":
        session.clear()

    elif action == "search":
        client = get_client()
        if client:
            country = request.form.get("country")
            area = request.form.get("area","").strip()

            q = client.available_phone_numbers(country).local
            result = q.list(area_code=area if area else None, limit=10)

            session["search_results"] = [n.phone_number for n in result]

    elif action == "buy":
        client = get_client()
        if client:
            number = request.form["number"]
            client.incoming_phone_numbers.create(phone_number=number)
            refresh_numbers()

    elif action == "sms":
        client = get_client()
        data = []

        if client:
            msgs = client.messages.list(limit=25)

            for m in msgs:
                if m.direction != "inbound":
                    continue

                body = m.body or ""

                data.append({
                    "from": m.from_,
                    "body": body,
                    "time": to_bd_time(m.date_sent),
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
