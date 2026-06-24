from flask import Flask, request, session, jsonify, render_template_string
from twilio.rest import Client
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

# =========================
# 🌈 FULL UI + REMEMBER LOGIN
# =========================

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Smart Panel BY Rakibul Islam 💖</title>

<style>
body{
    margin:0;
    font-family:Arial;
    background:linear-gradient(-45deg,#0f172a,#1e293b,#111827,#0b1220);
    background-size:400% 400%;
    animation:bg 10s ease infinite;
    color:white;
}

@keyframes bg{
    0%{background-position:0% 50%;}
    50%{background-position:100% 50%;}
    100%{background-position:0% 50%;}
}

.container{
    max-width:900px;
    margin:auto;
    padding:20px;
}

/* LOGIN */
.login-box{
    background:linear-gradient(135deg,#ff6fa1,#ff9ac1);
    padding:15px;
    border-radius:18px;
    text-align:center;
}

/* SECTIONS */
.box{
    padding:15px;
    border-radius:18px;
    margin-top:15px;
}

/* COLORS */
.numbers{background:linear-gradient(135deg,#4da9ff,#6fc2ff);}
.buy{background:linear-gradient(135deg,#a855f7,#c084fc);}
.sms{background:linear-gradient(135deg,#22c55e,#86efac);}

/* INPUT */
input,select{
    padding:10px;
    border-radius:12px;
    border:none;
    margin:5px;
    width:220px;
}

/* BUTTONS */
button{
    padding:10px 15px;
    border:none;
    border-radius:12px;
    cursor:pointer;
    font-weight:bold;
}

.pink{background:#ff4d88;color:white;}
.blue{background:#2563eb;color:white;}
.green{background:#16a34a;color:white;}
.red{background:#ef4444;color:white;}

/* ROW */
.row{
    display:flex;
    justify-content:space-between;
    align-items:center;
    background:rgba(255,255,255,0.2);
    padding:10px;
    margin:8px 0;
    border-radius:12px;
    color:black;
}
</style>
</head>

<body>

<div class="container">

<h2 style="text-align:center;">💖 Smart Control Panel BY Rakibul Islam</h2>

<!-- LOGIN -->
<div class="login-box">
    <h3>Login ID:TOKEN</h3>
    <input id="auth" placeholder="ID:TOKEN">
    <button class="pink" onclick="login()">LOGIN</button>
</div>

<!-- APP -->
<div id="app" style="display:none;">

<!-- NUMBERS -->
<div class="box numbers">
    <h3>📱 My Numbers</h3>
    <div id="numbers"></div>
</div>

<!-- BUY -->
<div class="box buy">
    <h3>🛒 Buy Number</h3>

    <select id="country">
      <option value="CA">CA</option>
      <option value="US">US</option>
        <option value="PR">PR</option>
    </select>

    <input id="area" placeholder="Area Code">
    <button class="blue" onclick="search()">Search</button>

    <div id="search"></div>
</div>

<!-- SMS -->
<div class="box sms">
    <h3>💬 Live SMS (BD Time 🇧🇩)</h3>
    <div id="sms"></div>
</div>

<button class="red" onclick="logout()">Logout</button>

</div>

</div>

<script>

/* AUTO LOGIN */
window.onload = async function(){
    let saved = localStorage.getItem("auth");

    if(saved){
        let res = await fetch("/login",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({auth:saved})
        });

        let data = await res.json();

        if(data.success){
            document.getElementById("app").style.display="block";
            loadNumbers();
            loadSMS();
            setInterval(loadSMS,5000);
        }else{
            localStorage.removeItem("auth");
        }
    }
}

/* LOGIN */
async function login(){
    let auth=document.getElementById("auth").value;

    let res=await fetch("/login",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({auth})
    });

    let data=await res.json();

    if(data.success){

        localStorage.setItem("auth",auth);

        document.getElementById("app").style.display="block";

        loadNumbers();
        loadSMS();
        setInterval(loadSMS,5000);

    }else{
        alert(data.error);
    }
}

/* LOGOUT */
function logout(){
    localStorage.removeItem("auth");
    location.reload();
}

/* LOAD NUMBERS */
async function loadNumbers(){
    let res=await fetch("/numbers");
    let data=await res.json();

    document.getElementById("numbers").innerHTML=
    data.map(n=>
        `<div class="row">
            📞 ${n.phone}
            <button class="red" onclick="del('${n.sid}')">Delete</button>
        </div>`
    ).join("");
}

/* DELETE */
async function del(sid){
    await fetch("/delete",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({sid})
    });

    loadNumbers();
}

/* SEARCH */
async function search(){
    let country=document.getElementById("country").value;
    let area=document.getElementById("area").value;

    let res=await fetch(`/available?country=${country}&area=${area}`);
    let data=await res.json();

    document.getElementById("search").innerHTML=
    data.map(n=>
        `<div class="row">
            📞 ${n}
            <button class="green" onclick="buy('${n}')">Buy</button>
        </div>`
    ).join("");
}

/* BUY */
async function buy(num){
    await fetch("/buy",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({number:num})
    });

    loadNumbers();
}

/* SMS */
async function loadSMS(){
    let res=await fetch("/sms");
    let data=await res.json();

    document.getElementById("sms").innerHTML=
    data.map(m=>
        `<div class="row">
            💌 <b>${m.from}</b><br>
            ${m.time}<br>
            ${m.body}
        </div>`
    ).join("");
}

</script>

</body>
</html>
"""

# =========================
# BACKEND
# =========================

def get_client():
    if "sid" not in session or "token" not in session:
        return None
    return Client(session["sid"], session["token"])

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/login", methods=["POST"])
def login():
    data=request.json
    auth=data.get("auth","")

    try:
        sid,token=auth.split(":",1)
        Client(sid,token).api.accounts(sid).fetch()

        session["sid"]=sid
        session["token"]=token

        return jsonify(success=True)

    except Exception as e:
        return jsonify(success=False,error=str(e))

@app.route("/numbers")
def numbers():
    c=get_client()
    if not c:
        return jsonify(error="not logged in"),401

    return jsonify([
        {"sid":n.sid,"phone":n.phone_number}
        for n in c.incoming_phone_numbers.list()
    ])

@app.route("/delete",methods=["POST"])
def delete():
    c=get_client()
    if not c:
        return jsonify(error="not logged in"),401

    sid=request.json["sid"]

    try:
        c.incoming_phone_numbers(sid).delete()
        return jsonify(ok=True)
    except:
        return jsonify(ok=False)

@app.route("/available")
def available():
    c=get_client()
    if not c:
        return jsonify(error="not logged in"),401

    country=request.args.get("country","US")
    area=request.args.get("area","")

    q=c.available_phone_numbers(country).local

    nums=q.list(area_code=area,limit=5) if area else q.list(limit=5)

    return jsonify([n.phone_number for n in nums])

@app.route("/buy",methods=["POST"])
def buy():
    c=get_client()
    if not c:
        return jsonify(error="not logged in"),401

    num=request.json["number"]
    c.incoming_phone_numbers.create(phone_number=num)

    return jsonify(ok=True)

@app.route("/sms")
def sms():
    c=get_client()
    if not c:
        return jsonify(error="not logged in"),401

    msgs=c.messages.list(limit=20)

    bd=ZoneInfo("Asia/Dhaka")

    out=[]
    for m in msgs:
        if m.direction=="inbound":
            dt=m.date_created
            if dt:
                dt=dt.astimezone(bd)

            out.append({
                "from":m.from_,
                "body":m.body,
                "time":dt.strftime("%H:%M:%S") if dt else ""
            })

    return jsonify(out)

if __name__=="__main__":
    app.run(debug=True)
