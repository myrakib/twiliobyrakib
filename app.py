from flask import Flask, request, session, jsonify, render_template_string
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = "change-me"

HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Twilio Dashboard</title>

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">

<style>
body{
    background:#f4f8ff;
    padding:20px;
}
.card{
    border:none;
    border-radius:20px;
    box-shadow:0 4px 15px rgba(0,0,0,.08);
}
.big-btn{
    border-radius:15px;
}
.sms-box{
    max-height:350px;
    overflow:auto;
}
</style>
</head>
<body>

<div class="container">

<h2 class="text-center mb-4">
📱 Twilio Manager
</h2>

<div id="loginCard" class="card p-4 mb-4">
<h4>Login</h4>

<input id="sid" class="form-control mb-2" placeholder="Account SID">
<input id="token" class="form-control mb-3" placeholder="Auth Token">

<button class="btn btn-primary big-btn" onclick="login()">
Login
</button>

<div id="loginMsg" class="mt-3"></div>
</div>

<div id="dashboard" style="display:none">

<div class="card p-3 mb-3">
<div class="d-flex justify-content-between">
<div>✅ Logged In</div>
<div>
<button class="btn btn-danger btn-sm" onclick="logout()">
Logout
</button>
</div>
</div>
</div>

<div class="card p-3 mb-3">
<h5>Buy Number</h5>

<select id="country" class="form-select mb-2">
<option value="US">United States</option>
<option value="CA">Canada</option>
</select>

<button class="btn btn-success mb-3" onclick="loadNumbers()">
Load 5 Numbers
</button>

<div id="availableNumbers"></div>
</div>

<div class="card p-3 mb-3">
<h5>Current Numbers</h5>
<div id="ownedNumbers"></div>
</div>

<div class="card p-3">
<h5>Recent Incoming SMS</h5>
<div id="smsList" class="sms-box"></div>
</div>

</div>

</div>

<script>

async function login(){
    let r = await fetch("/login",{
        method:"POST",
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
            sid:document.getElementById("sid").value,
            token:document.getElementById("token").value
        })
    });

    let data = await r.json();

    if(data.success){
        document.getElementById("loginCard").style.display="none";
        document.getElementById("dashboard").style.display="block";

        refreshNumbers();
        refreshSMS();
    }else{
        document.getElementById("loginMsg").innerHTML =
        '<div class="alert alert-danger">'+data.error+'</div>';
    }
}

async function logout(){
    await fetch("/logout");
    location.reload();
}

async function loadNumbers(){

    let country =
    document.getElementById("country").value;

    let r = await fetch("/available?country="+country);

    let data = await r.json();

    let html="";

    data.forEach(n=>{
        html += `
        <div class="mb-2">
            ${n}
            <button class="btn btn-sm btn-success"
            onclick="buyNumber('${n}')">
            Buy
            </button>
        </div>
        `;
    });

    document.getElementById("availableNumbers").innerHTML = html;
}

async function buyNumber(num){

    await fetch("/buy",{
        method:"POST",
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({number:num})
    });

    refreshNumbers();
}

async function refreshNumbers(){

    let r = await fetch("/numbers");
    let data = await r.json();

    let html="";

    data.forEach(n=>{

        html += `
        <div class="mb-2">
            ${n.phone}
            <button
            class="btn btn-danger btn-sm"
            onclick="deleteNumber('${n.sid}')">
            Delete
            </button>
        </div>
        `;
    });

    document.getElementById("ownedNumbers").innerHTML = html;
}

async function deleteNumber(sid){

    await fetch("/delete",{
        method:"POST",
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({sid:sid})
    });

    refreshNumbers();
}

async function refreshSMS(){

    let r = await fetch("/sms");
    let data = await r.json();

    let html="";

    data.forEach(m=>{

        html += `
        <div class="border rounded p-2 mb-2">
        <b>${m.from}</b><br>
        ${m.body}
        </div>
        `;
    });

    document.getElementById("smsList").innerHTML = html;
}

setInterval(refreshSMS,5000);

</script>

</body>
</html>
"""

def client():
    if "sid" not in session:
        return None
    return Client(session["sid"], session["token"])

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/login", methods=["POST"])
def login():
    data = request.json

    sid = data["sid"]
    token = data["token"]

    try:
        c = Client(sid, token)
        c.api.accounts(sid).fetch()

        session["sid"] = sid
        session["token"] = token

        return jsonify(success=True)

    except Exception as e:
        return jsonify(
            success=False,
            error="Invalid SID or Token"
        )

@app.route("/logout")
def logout():
    session.clear()
    return jsonify(ok=True)

@app.route("/available")
def available():

    c = client()

    country = request.args.get("country","US")

    nums = c.available_phone_numbers(
        country
    ).local.list(limit=5)

    return jsonify([
        n.phone_number
        for n in nums
    ])

@app.route("/buy", methods=["POST"])
def buy():

    c = client()

    number = request.json["number"]

    c.incoming_phone_numbers.create(
        phone_number=number
    )

    return jsonify(ok=True)

@app.route("/numbers")
def numbers():

    c = client()

    result = []

    for n in c.incoming_phone_numbers.list():

        result.append({
            "sid":n.sid,
            "phone":n.phone_number
        })

    return jsonify(result)

@app.route("/delete", methods=["POST"])
def delete_number():

    c = client()

    sid = request.json["sid"]

    c.incoming_phone_numbers(
        sid
    ).delete()

    return jsonify(ok=True)

@app.route("/sms")
def sms():

    c = client()

    messages = c.messages.list(limit=50)

    result = []

    for m in messages:

        if m.direction == "inbound":

            result.append({
                "from":m.from_,
                "body":m.body
            })

    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
