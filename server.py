"""
ESP32 Cloud OTA - Complete Server
Day 5 final version
API Key  : ESP32-OTA-1ar0922ec
Dashboard: #ironman@099
"""

import os
import json
import hashlib
import functools
from datetime import datetime
from flask import (Flask, request, jsonify, send_file,
                   render_template_string, session, redirect, url_for)

app = Flask(__name__)
app.secret_key = "OTA-SESSION-KEY-anurag-2024"

API_KEY            = "ESP32-OTA-1ar0922ec"
DASHBOARD_PASSWORD = "#ironman@099"

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
FIRMWARE_DIR  = os.path.join(BASE_DIR, "firmware")
BIN_PATH      = os.path.join(FIRMWARE_DIR, "firmware.bin")
META_PATH     = os.path.join(FIRMWARE_DIR, "meta.json")
DEVICES_PATH  = os.path.join(FIRMWARE_DIR, "devices.json")
REGISTRY_PATH = os.path.join(FIRMWARE_DIR, "registry.json")
LOGS_PATH     = os.path.join(FIRMWARE_DIR, "logs.json")
STATS_PATH    = os.path.join(FIRMWARE_DIR, "stats.json")

os.makedirs(FIRMWARE_DIR, exist_ok=True)

def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_meta():     return load_json(META_PATH,     {"version": "none", "history": []})
def load_devices():  return load_json(DEVICES_PATH,  {})
def load_registry(): return load_json(REGISTRY_PATH, {})
def load_logs():     return load_json(LOGS_PATH,      [])
def load_stats():    return load_json(STATS_PATH,     {})
def save_meta(d):     save_json(META_PATH,     d)
def save_devices(d):  save_json(DEVICES_PATH,  d)
def save_registry(d): save_json(REGISTRY_PATH, d)
def save_logs(d):     save_json(LOGS_PATH,      d)
def save_stats(d):    save_json(STATS_PATH,     d)

def now_utc():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def md5_of_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def get_device_name(mac):
    return load_registry().get(mac, mac)

def add_log(mac, event, detail="", status="info"):
    logs = load_logs()
    logs.insert(0, {
        "mac": mac, "name": get_device_name(mac),
        "event": event, "detail": detail,
        "status": status, "time": now_utc()
    })
    save_logs(logs[:500])

def update_stats(mac, event):
    stats = load_stats()
    if mac not in stats:
        stats[mac] = {
            "total_checkins": 0, "successful_updates": 0,
            "failed_updates": 0, "last_update": None, "last_failure": None
        }
    if event == "checkin":
        stats[mac]["total_checkins"] += 1
    elif event == "update_success":
        stats[mac]["successful_updates"] += 1
        stats[mac]["last_update"] = now_utc()
    elif event == "update_failed":
        stats[mac]["failed_updates"] += 1
        stats[mac]["last_failure"] = now_utc()
    save_stats(stats)

def register_device(req):
    mac     = req.headers.get("X-Device-MAC", "unknown")
    version = req.headers.get("X-FW-Version",  "unknown")
    if mac == "unknown":
        return mac, version
    devices  = load_devices()
    registry = load_registry()
    devices[mac] = {
        "mac": mac, "name": registry.get(mac, None),
        "version": version, "last_seen": now_utc(),
        "ip": req.remote_addr or "unknown"
    }
    save_devices(devices)
    return mac, version

def require_api_key(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key")
        if not key:
            return jsonify({"error": "API key missing"}), 401
        if key != API_KEY:
            return jsonify({"error": "Invalid API key"}), 403
        return f(*args, **kwargs)
    return decorated

def require_login(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ESP32 Cloud OTA - Login</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#0d0f0e;--surface:#141714;--border:#232623;--accent:#39ff8a;--text:#e8ede9;--muted:#5a6b5c;--danger:#ff4f4f;--mono:"JetBrains Mono",monospace;--display:"Syne",sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:var(--mono);min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:40px;width:100%;max-width:380px}
.logo{font-family:var(--display);font-size:22px;font-weight:800;margin-bottom:8px}
.logo span{color:var(--accent)}
.sub{color:var(--muted);font-size:12px;margin-bottom:32px}
label{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:var(--muted);display:block;margin-bottom:8px}
input{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-family:var(--mono);font-size:14px;padding:12px 14px;outline:none;transition:border-color .2s;margin-bottom:20px}
input:focus{border-color:var(--accent)}
button{width:100%;background:var(--accent);color:#000;border:none;border-radius:6px;font-family:var(--display);font-size:15px;font-weight:700;padding:12px;cursor:pointer;transition:opacity .2s}
button:hover{opacity:.85}
.error{background:#1a0a0a;border:1px solid var(--danger);border-radius:6px;padding:10px 14px;color:var(--danger);font-size:12px;margin-bottom:20px}
</style>
</head>
<body>
<div class="card">
  <div class="logo">ESP32 <span>Cloud</span> OTA</div>
  <div class="sub">Enter password to access dashboard</div>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  <form method="POST">
    <label>Password</label>
    <input type="password" name="password" placeholder="Enter dashboard password" autofocus>
    <button type="submit">Login</button>
  </form>
</div>
</body>
</html>"""

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        error = "Wrong password. Try again."
    return render_template_string(LOGIN_HTML, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/checkin", methods=["POST"])
@require_api_key
def checkin():
    mac, version = register_device(request)
    add_log(mac, "check-in", "v" + version, "info")
    update_stats(mac, "checkin")
    return jsonify({"ok": True})

@app.route("/version")
@require_api_key
def get_version():
    mac, version = register_device(request)
    meta       = load_meta()
    server_ver = meta["version"]
    if server_ver != "none" and server_ver != version:
        add_log(mac, "update available",
                "device v" + version + " to server v" + server_ver, "warning")
    return jsonify({"version": server_ver})

@app.route("/firmware")
def get_firmware():
    key = request.headers.get("X-API-Key") or request.args.get("key")
    mac = request.headers.get("X-Device-MAC", "unknown")
    if not key:
        return jsonify({"error": "API key missing"}), 401
    if key != API_KEY:
        return jsonify({"error": "Invalid API key"}), 403
    if not os.path.exists(BIN_PATH):
        return jsonify({"error": "No firmware uploaded yet"}), 404
    add_log(mac, "firmware download", "downloading binary", "info")
    return send_file(BIN_PATH, mimetype="application/octet-stream",
                     as_attachment=True, download_name="firmware.bin")

@app.route("/update/success", methods=["POST"])
@require_api_key
def update_success():
    mac     = request.headers.get("X-Device-MAC", "unknown")
    version = request.headers.get("X-FW-Version",  "unknown")
    add_log(mac, "update success", "now running v" + version, "success")
    update_stats(mac, "update_success")
    return jsonify({"ok": True})

@app.route("/update/failed", methods=["POST"])
@require_api_key
def update_failed():
    mac    = request.headers.get("X-Device-MAC", "unknown")
    reason = request.headers.get("X-Error", "unknown error")
    add_log(mac, "update failed", reason, "error")
    update_stats(mac, "update_failed")
    return jsonify({"ok": True})

@app.route("/upload", methods=["POST"])
def upload_firmware():
    upload_key = request.headers.get("X-Upload-Key")
    if not session.get("logged_in") and upload_key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    if "file" not in request.files:
        return jsonify({"error": "No file in request"}), 400
    file    = request.files["file"]
    version = request.form.get("version", "").strip()
    if not file.filename.endswith(".bin"):
        return jsonify({"error": "Only .bin files are accepted"}), 400
    if not version:
        return jsonify({"error": "Version string is required"}), 400
    file.save(BIN_PATH)
    size_kb = round(os.path.getsize(BIN_PATH) / 1024, 1)
    md5     = md5_of_file(BIN_PATH)
    meta    = load_meta()
    meta["version"] = version
    meta["history"].insert(0, {
        "version": version, "filename": file.filename,
        "size_kb": size_kb, "md5": md5, "uploaded": now_utc()
    })
    meta["history"] = meta["history"][:20]
    save_meta(meta)
    add_log("dashboard", "firmware uploaded", "v" + version + " - " + str(size_kb) + " KB", "success")
    print("[OTA] New firmware uploaded - v" + version + " (" + str(size_kb) + " KB)")
    return jsonify({"ok": True, "version": version, "size_kb": size_kb, "md5": md5})

@app.route("/history")
@require_login
def get_history():
    return jsonify(load_meta().get("history", []))

@app.route("/devices/named")
@require_login
def get_named_devices():
    devices  = load_devices()
    registry = load_registry()
    stats    = load_stats()
    return jsonify([
        {**d, "name": registry[mac], "stats": stats.get(mac, {})}
        for mac, d in devices.items() if mac in registry
    ])

@app.route("/devices/unnamed")
@require_login
def get_unnamed_devices():
    devices  = load_devices()
    registry = load_registry()
    return jsonify([d for mac, d in devices.items() if mac not in registry])

@app.route("/devices/register", methods=["POST"])
@require_login
def register_device_name():
    data = request.get_json()
    mac  = data.get("mac", "").strip()
    name = data.get("name", "").strip()
    if not mac or not name:
        return jsonify({"error": "MAC and name required"}), 400
    registry      = load_registry()
    registry[mac] = name
    save_registry(registry)
    devices = load_devices()
    if mac in devices:
        devices[mac]["name"] = name
        save_devices(devices)
    add_log(mac, "device registered", "named: " + name, "success")
    return jsonify({"ok": True, "mac": mac, "name": name})

@app.route("/devices/rename", methods=["POST"])
@require_login
def rename_device():
    data     = request.get_json()
    mac      = data.get("mac", "").strip()
    name     = data.get("name", "").strip()
    if not mac or not name:
        return jsonify({"error": "MAC and name required"}), 400
    registry = load_registry()
    old_name = registry.get(mac, mac)
    registry[mac] = name
    save_registry(registry)
    devices = load_devices()
    if mac in devices:
        devices[mac]["name"] = name
        save_devices(devices)
    add_log(mac, "device renamed", old_name + " to " + name, "info")
    return jsonify({"ok": True})

@app.route("/logs")
@require_login
def get_logs():
    logs   = load_logs()
    status = request.args.get("status")
    limit  = int(request.args.get("limit", 100))
    if status:
        logs = [l for l in logs if l["status"] == status]
    return jsonify(logs[:limit])

@app.route("/stats")
@require_login
def get_stats():
    stats    = load_stats()
    registry = load_registry()
    return jsonify([
        {"mac": mac, "name": registry.get(mac, mac), **s}
        for mac, s in stats.items()
    ])

REGISTER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Device Registration</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#0d0f0e;--surface:#141714;--border:#232623;--accent:#39ff8a;--accent2:#00c8ff;--text:#e8ede9;--muted:#5a6b5c;--danger:#ff4f4f;--radius:10px;--mono:"JetBrains Mono",monospace;--display:"Syne",sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:var(--mono);font-size:13px;min-height:100vh;padding:40px 24px}
header{display:flex;align-items:center;justify-content:space-between;margin-bottom:40px;padding-bottom:20px;border-bottom:1px solid var(--border)}
.logo{font-family:var(--display);font-size:26px;font-weight:800}
.logo span{color:var(--accent)}
.back{background:transparent;border:1px solid var(--border);border-radius:6px;color:var(--muted);font-family:var(--mono);font-size:12px;padding:6px 14px;cursor:pointer;text-decoration:none}
.back:hover{border-color:var(--accent);color:var(--accent)}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:24px;margin-bottom:16px}
.lbl{font-size:10px;text-transform:uppercase;letter-spacing:2px;color:var(--muted);margin-bottom:16px}
.row{display:flex;align-items:center;gap:12px;padding:16px 0;border-bottom:1px solid var(--border)}
.row:last-child{border-bottom:none}
.mac{font-size:14px;color:var(--accent2);min-width:180px}
.ver{color:var(--muted);font-size:11px;min-width:60px}
.last{color:var(--muted);font-size:11px;flex:1}
.ni{background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-family:var(--mono);font-size:13px;padding:8px 12px;outline:none;width:200px}
.ni:focus{border-color:var(--accent)}
.ni::placeholder{color:var(--muted)}
.sb{background:var(--accent);color:#000;border:none;border-radius:6px;font-family:var(--display);font-size:13px;font-weight:700;padding:8px 16px;cursor:pointer}
.sb:hover{opacity:.85}
.empty{color:var(--muted);text-align:center;padding:32px}
.toast{display:none;position:fixed;bottom:24px;right:24px;padding:12px 20px;border-radius:8px;font-size:13px;font-weight:600;z-index:999}
.toast.success{background:var(--accent);color:#000;display:block}
.toast.error{background:var(--danger);color:#fff;display:block}
.cnt{font-family:var(--display);font-size:32px;font-weight:800;color:var(--accent2);line-height:1;margin-bottom:4px}
.csub{color:var(--muted);font-size:11px;margin-bottom:20px}
</style>
</head>
<body>
<header>
  <div class="logo">ESP32 <span>Cloud</span> OTA</div>
  <a href="/" class="back">Back to dashboard</a>
</header>
<div class="card">
  <div class="lbl">Unregistered devices</div>
  <div class="cnt" id="count">-</div>
  <div class="csub">devices waiting to be named</div>
  <div id="list"><div class="empty">Loading...</div></div>
</div>
<div class="toast" id="toast"></div>
<script>
function load(){
  fetch("/devices/unnamed").then(r=>r.json()).then(function(devices){
    var list=document.getElementById("list");
    document.getElementById("count").textContent=devices.length;
    if(!devices.length){list.innerHTML="<div class='empty'>No unregistered devices</div>";return}
    var html="";
    for(var i=0;i<devices.length;i++){
      var d=devices[i];
      var id=d.mac.replace(/:/g,"");
      html+="<div class='row' id='row-"+id+"'>";
      html+="<div class='mac'>"+d.mac+"</div>";
      html+="<div class='ver'>v"+d.version+"</div>";
      html+="<div class='last'>"+d.last_seen+"</div>";
      html+="<input class='ni' id='inp-"+id+"' placeholder='Enter device name...'>";
      html+="<button class='sb' data-mac='"+d.mac+"' onclick='save(this)'>Register</button>";
      html+="</div>";
    }
    list.innerHTML=html;
  });
}
function save(btn){
  var mac=btn.getAttribute("data-mac");
  var id=mac.replace(/:/g,"");
  var name=document.getElementById("inp-"+id).value.trim();
  if(!name){toast("Enter a device name","error");return}
  fetch("/devices/register",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mac:mac,name:name})})
    .then(function(r){return r.json()}).then(function(d){
      if(d.ok){
        toast(name+" registered","success");
        document.getElementById("row-"+id).remove();
        var c=document.getElementById("count");
        c.textContent=parseInt(c.textContent)-1;
      } else toast(d.error||"Failed","error");
    });
}
function toast(msg,type){
  var t=document.getElementById("toast");
  t.textContent=msg;t.className="toast "+type;
  clearTimeout(t._t);t._t=setTimeout(function(){t.className="toast"},3500);
}
load();
</script>
</body>
</html>"""

@app.route("/register")
@require_login
def register_page():
    return render_template_string(REGISTER_HTML)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ESP32 Cloud OTA</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#0d0f0e;--surface:#141714;--border:#232623;--accent:#39ff8a;--accent2:#00c8ff;--text:#e8ede9;--muted:#5a6b5c;--danger:#ff4f4f;--warning:#f5a623;--radius:10px;--mono:"JetBrains Mono",monospace;--display:"Syne",sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:var(--mono);font-size:13px;min-height:100vh;padding:40px 24px}
header{display:flex;align-items:center;justify-content:space-between;margin-bottom:40px;padding-bottom:20px;border-bottom:1px solid var(--border)}
.logo{font-family:var(--display);font-size:26px;font-weight:800;letter-spacing:-.5px}
.logo span{color:var(--accent)}
.hr{display:flex;align-items:center;gap:12px}
.badge{display:flex;align-items:center;gap:8px;background:var(--surface);border:1px solid var(--border);border-radius:999px;padding:6px 14px;font-size:12px;color:var(--muted)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--accent);animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.logout{background:transparent;border:1px solid var(--border);border-radius:6px;color:var(--muted);font-family:var(--mono);font-size:12px;padding:6px 14px;cursor:pointer;text-decoration:none}
.logout:hover{border-color:var(--danger);color:var(--danger)}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:16px}
@media(max-width:900px){.g3{grid-template-columns:1fr 1fr}}
@media(max-width:600px){.g3{grid-template-columns:1fr}}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:24px;margin-bottom:16px}
.lbl{font-size:10px;text-transform:uppercase;letter-spacing:2px;color:var(--muted);margin-bottom:10px}
.bignum{font-family:var(--display);font-size:40px;font-weight:800;line-height:1}
.bigsub{color:var(--muted);font-size:11px;margin-top:6px}
.ver{font-family:var(--display);font-size:48px;font-weight:800;color:var(--accent);line-height:1;letter-spacing:-1px}
.drop{border:2px dashed var(--border);border-radius:var(--radius);padding:36px;text-align:center;cursor:pointer;transition:border-color .2s,background .2s;margin-bottom:16px}
.drop.over{border-color:var(--accent);background:#0d1f13}
.drop input{display:none}
.dicon{font-size:32px;margin-bottom:10px;display:block;filter:grayscale(1);transition:filter .2s}
.drop.hasfile .dicon{filter:none}
.dtitle{font-family:var(--display);font-size:16px;font-weight:700;margin-bottom:4px}
.dsub{color:var(--muted);font-size:12px}
.finfo{display:none;margin-top:10px;padding:8px 14px;background:var(--bg);border-radius:6px;border:1px solid var(--accent);color:var(--accent);font-size:12px}
.drop.hasfile .finfo{display:block}
.urow{display:flex;gap:12px;align-items:center}
.vi{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-family:var(--mono);font-size:14px;padding:10px 14px;outline:none;transition:border-color .2s}
.vi:focus{border-color:var(--accent)}
.vi::placeholder{color:var(--muted)}
.ubtn{background:var(--accent);color:#000;border:none;border-radius:6px;font-family:var(--display);font-size:14px;font-weight:700;padding:10px 24px;cursor:pointer;transition:opacity .2s;white-space:nowrap}
.ubtn:hover{opacity:.85}
.ubtn:disabled{opacity:.4;cursor:not-allowed}
.toast{display:none;position:fixed;bottom:24px;right:24px;padding:12px 20px;border-radius:8px;font-size:13px;font-weight:600;z-index:999}
.toast.success{background:var(--accent);color:#000;display:block}
.toast.error{background:var(--danger);color:#fff;display:block}
.pw{display:none;height:4px;background:var(--border);border-radius:2px;margin-top:12px;overflow:hidden}
.pb{height:100%;background:var(--accent);width:0%;transition:width .3s}
.pw.on{display:block}
.dtable{width:100%;border-collapse:collapse}
.dtable th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:2px;color:var(--muted);padding:8px 12px;border-bottom:1px solid var(--border)}
.dtable td{padding:12px;border-bottom:1px solid var(--border);vertical-align:middle}
.dtable tr:last-child td{border-bottom:none}
.dname{font-family:var(--display);font-size:15px;font-weight:700}
.dmac{color:var(--muted);font-size:11px;margin-top:3px}
.son{display:inline-flex;align-items:center;gap:6px;color:var(--accent);font-size:12px}
.soff{display:inline-flex;align-items:center;gap:6px;color:var(--muted);font-size:12px}
.smiss{display:inline-flex;align-items:center;gap:6px;color:var(--danger);font-size:12px}
.sd{width:7px;height:7px;border-radius:50%}
.sd.on{background:var(--accent);animation:pulse 2s infinite}
.sd.off{background:var(--muted)}
.sd.miss{background:var(--danger)}
.vb{display:inline-block;padding:3px 10px;border-radius:4px;font-size:11px}
.utd{background:#0e3a2a;color:var(--accent)}
.old{background:#2a1a0e;color:var(--warning)}
.ls{color:var(--muted);font-size:11px}
.rbtn{background:transparent;border:1px solid var(--border);border-radius:4px;color:var(--muted);font-family:var(--mono);font-size:11px;padding:3px 8px;cursor:pointer}
.rbtn:hover{border-color:var(--accent2);color:var(--accent2)}
.empty{color:var(--muted);text-align:center;padding:24px}
.alert{display:none;background:#1a2e3a;border:1px solid var(--accent2);border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:12px;color:var(--accent2)}
.alert a{color:var(--accent2);font-weight:600}
.sh{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.rfbtn{background:transparent;border:1px solid var(--border);border-radius:6px;color:var(--muted);font-family:var(--mono);font-size:11px;padding:4px 12px;cursor:pointer}
.rfbtn:hover{border-color:var(--accent2);color:var(--accent2)}
.lf{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.fb{background:transparent;border:1px solid var(--border);border-radius:4px;color:var(--muted);font-family:var(--mono);font-size:11px;padding:4px 10px;cursor:pointer}
.fb.on{border-color:var(--accent);color:var(--accent)}
.le{display:flex;align-items:flex-start;gap:12px;padding:10px 0;border-bottom:1px solid var(--border)}
.le:last-child{border-bottom:none}
.ld{width:8px;height:8px;border-radius:50%;margin-top:4px;flex-shrink:0}
.ld.info{background:var(--accent2)}
.ld.success{background:var(--accent)}
.ld.warning{background:var(--warning)}
.ld.error{background:var(--danger)}
.ln{color:var(--text);font-weight:600;font-size:12px}
.lev{color:var(--muted);font-size:11px}
.ldt{color:var(--muted);font-size:11px;margin-top:2px}
.lt{color:var(--muted);font-size:10px;margin-left:auto;white-space:nowrap}
.lbox{max-height:400px;overflow-y:auto}
.sg{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}
.sc{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:16px}
.scn{font-family:var(--display);font-size:14px;font-weight:700;margin-bottom:12px}
.sr{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;font-size:12px}
.sl{color:var(--muted)}
.sv{font-weight:600}
.sv.g{color:var(--accent)}
.sv.r{color:var(--danger)}
.sv.y{color:var(--warning);font-size:10px}
.ht{width:100%;border-collapse:collapse}
.ht th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:2px;color:var(--muted);padding:8px 12px;border-bottom:1px solid var(--border)}
.ht td{padding:10px 12px;border-bottom:1px solid var(--border)}
.ht tr:last-child td{border-bottom:none}
.ht tr:first-child td{color:var(--accent)}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;background:#0e3a2a;color:var(--accent)}
</style>
</head>
<body>
<header>
  <div class="logo">ESP32 <span>Cloud</span> OTA</div>
  <div class="hr">
    <div class="badge"><div class="dot"></div>Secured - Online 24/7</div>
    <a href="/logout" class="logout">Logout</a>
  </div>
</header>
<div id="alert" class="alert">
  New devices detected - <span id="ucnt">0</span> unregistered
  <a href="/register"> Register now</a>
</div>
<div class="g3">
  <div class="card">
    <div class="lbl">Current firmware</div>
    <div class="ver" id="vd">-</div>
    <div style="color:var(--muted);margin-top:8px;font-size:11px" id="vs">Fetching...</div>
  </div>
  <div class="card">
    <div class="lbl">Devices</div>
    <div class="bignum" id="td" style="color:var(--accent2)">-</div>
    <div class="bigsub" id="oc">- online</div>
  </div>
  <div class="card">
    <div class="lbl">Total check-ins</div>
    <div class="bignum" id="tc" style="color:var(--accent)">-</div>
    <div class="bigsub">across all devices</div>
  </div>
</div>
<div class="card">
  <div class="sh">
    <div class="lbl" style="margin-bottom:0">Named devices</div>
    <div style="display:flex;gap:8px">
      <a href="/register" style="background:transparent;border:1px solid var(--accent2);border-radius:6px;color:var(--accent2);font-family:var(--mono);font-size:11px;padding:4px 12px;text-decoration:none">+ Register</a>
      <button class="rfbtn" onclick="loadDevices()">Refresh</button>
    </div>
  </div>
  <div id="dc"><div class="empty">Loading...</div></div>
</div>
<div class="card">
  <div class="lbl">Device statistics</div>
  <div class="sg" id="sc"><div class="empty">Loading...</div></div>
</div>
<div class="card">
  <div class="sh">
    <div class="lbl" style="margin-bottom:0">Activity log</div>
    <button class="rfbtn" onclick="loadLogs()">Refresh</button>
  </div>
  <div class="lf">
    <button class="fb on" onclick="filterLogs(this,'all')">All</button>
    <button class="fb" onclick="filterLogs(this,'success')">Success</button>
    <button class="fb" onclick="filterLogs(this,'warning')">Updates</button>
    <button class="fb" onclick="filterLogs(this,'error')">Errors</button>
    <button class="fb" onclick="filterLogs(this,'info')">Info</button>
  </div>
  <div class="lbox" id="lb"><div class="empty">Loading...</div></div>
</div>
<div class="card">
  <div class="lbl">Upload new firmware</div>
  <div class="drop" id="drop" onclick="document.getElementById('fi').click()">
    <input type="file" id="fi" accept=".bin">
    <span class="dicon">&#128230;</span>
    <div class="dtitle">Drop .bin file here or click to browse</div>
    <div class="dsub">Only compiled Arduino .bin files</div>
    <div class="finfo" id="finfo"></div>
  </div>
  <div class="urow">
    <input class="vi" id="vi" type="text" placeholder="Version - e.g. 1.0.1">
    <button class="ubtn" id="ub" onclick="doUpload()">Upload</button>
  </div>
  <div class="pw" id="pw"><div class="pb" id="pb"></div></div>
</div>
<div class="card">
  <div class="lbl">Upload history</div>
  <div id="hist"><div class="empty">No uploads yet</div></div>
</div>
<div class="toast" id="toast"></div>
<script>
var file=null,lf="all";
var drop=document.getElementById("drop");
var fi=document.getElementById("fi");
drop.addEventListener("dragover",function(e){e.preventDefault();drop.classList.add("over")});
drop.addEventListener("dragleave",function(){drop.classList.remove("over")});
drop.addEventListener("drop",function(e){e.preventDefault();drop.classList.remove("over");if(e.dataTransfer.files[0])setFile(e.dataTransfer.files[0])});
fi.addEventListener("change",function(){if(fi.files[0])setFile(fi.files[0])});
function setFile(f){
  if(!f.name.endsWith(".bin")){toast("Only .bin files accepted","error");return}
  file=f;drop.classList.add("hasfile");
  document.getElementById("finfo").textContent=f.name+" - "+(f.size/1024).toFixed(1)+" KB";
}
function doUpload(){
  var v=document.getElementById("vi").value.trim();
  if(!file){toast("Select a .bin file","error");return}
  if(!v){toast("Enter a version number","error");return}
  var btn=document.getElementById("ub");
  btn.disabled=true;btn.textContent="Uploading...";
  document.getElementById("pw").classList.add("on");
  var fd=new FormData();fd.append("file",file);fd.append("version",v);
  var xhr=new XMLHttpRequest();
  xhr.upload.onprogress=function(e){if(e.lengthComputable)document.getElementById("pb").style.width=Math.round(e.loaded/e.total*100)+"%"};
  xhr.onload=function(){
    btn.disabled=false;btn.textContent="Upload";
    document.getElementById("pw").classList.remove("on");
    document.getElementById("pb").style.width="0%";
    if(xhr.status===200){
      var r=JSON.parse(xhr.responseText);
      toast("v"+r.version+" uploaded - "+r.size_kb+" KB","success");
      file=null;drop.classList.remove("hasfile");
      document.getElementById("finfo").textContent="";
      document.getElementById("vi").value="";fi.value="";
      loadAll();
    } else {
      try{toast(JSON.parse(xhr.responseText).error||"Upload failed","error")}
      catch(e){toast("Upload failed","error")}
    }
  };
  xhr.onerror=function(){btn.disabled=false;btn.textContent="Upload";toast("Network error","error")};
  xhr.open("POST","/upload");xhr.send(fd);
}
function loadVer(){
  fetch("/version",{headers:{"X-API-Key":"ESP32-OTA-1ar0922ec"}}).then(function(r){return r.json()}).then(function(d){
    var el=document.getElementById("vd"),sub=document.getElementById("vs");
    if(d.version==="none"){el.textContent="-";sub.textContent="No firmware uploaded yet"}
    else{el.textContent="v"+d.version;sub.textContent="Ready to serve worldwide"}
  });
}
function loadDevices(){
  var sv=document.getElementById("vd").textContent.replace("v","");
  fetch("/devices/unnamed").then(function(r){return r.json()}).then(function(u){
    var a=document.getElementById("alert");
    document.getElementById("ucnt").textContent=u.length;
    a.style.display=u.length>0?"block":"none";
  });
  fetch("/devices/named").then(function(r){return r.json()}).then(function(devices){
    document.getElementById("td").textContent=devices.length;
    var on=0;
    for(var i=0;i<devices.length;i++){
      if(Math.floor((new Date()-new Date(devices[i].last_seen))/60000)<5)on++;
    }
    document.getElementById("oc").textContent=on+" online";
    var c=document.getElementById("dc");
    if(!devices.length){c.innerHTML="<div class='empty'>No named devices - <a href='/register' style='color:var(--accent2)'>register devices</a></div>";return}
    var rows="";
    for(var i=0;i<devices.length;i++){
      var d=devices[i];
      var diff=Math.floor((new Date()-new Date(d.last_seen))/60000);
      var isOn=diff<5,isMiss=diff>=15,isUtd=d.version===sv;
      var ci=d.stats?d.stats.total_checkins||0:0;
      var st=isOn?"<span class='son'><span class='sd on'></span>Online</span>":isMiss?"<span class='smiss'><span class='sd miss'></span>Missing</span>":"<span class='soff'><span class='sd off'></span>Offline</span>";
      rows+="<tr><td><div class='dname'>"+d.name+"</div><div class='dmac'>"+d.mac+"</div></td>";
      rows+="<td>"+st+"</td>";
      rows+="<td><span class='vb "+(isUtd?"utd":"old")+"'>v"+d.version+" "+(isUtd?"":"update available")+"</span></td>";
      rows+="<td style='color:var(--muted)'>"+ci+"</td>";
      rows+="<td class='ls'>"+d.last_seen+"</td>";
      rows+="<td><button class='rbtn' data-mac='"+d.mac+"' data-name='"+d.name+"' onclick='rename(this)'>Rename</button></td></tr>";
    }
    c.innerHTML="<table class='dtable'><thead><tr><th>Device</th><th>Status</th><th>Firmware</th><th>Check-ins</th><th>Last seen</th><th></th></tr></thead><tbody>"+rows+"</tbody></table>";
  });
}
function loadStats(){
  fetch("/stats").then(function(r){return r.json()}).then(function(stats){
    var total=0;
    for(var i=0;i<stats.length;i++)total+=stats[i].total_checkins||0;
    document.getElementById("tc").textContent=total;
    var c=document.getElementById("sc");
    if(!stats.length){c.innerHTML="<div class='empty'>No stats yet</div>";return}
    var html="";
    for(var i=0;i<stats.length;i++){
      var s=stats[i];
      html+="<div class='sc'><div class='scn'>"+s.name+"</div>";
      html+="<div class='sr'><span class='sl'>Total check-ins</span><span class='sv'>"+(s.total_checkins||0)+"</span></div>";
      html+="<div class='sr'><span class='sl'>Successful updates</span><span class='sv g'>"+(s.successful_updates||0)+"</span></div>";
      html+="<div class='sr'><span class='sl'>Failed updates</span><span class='sv r'>"+(s.failed_updates||0)+"</span></div>";
      html+="<div class='sr'><span class='sl'>Last update</span><span class='sv y'>"+(s.last_update?s.last_update.slice(0,16).replace("T"," "):"never")+"</span></div></div>";
    }
    c.innerHTML=html;
  });
}
function loadLogs(f){
  if(f)lf=f;
  var url=lf==="all"?"/logs":"/logs?status="+lf;
  fetch(url).then(function(r){return r.json()}).then(function(logs){
    var c=document.getElementById("lb");
    if(!logs.length){c.innerHTML="<div class='empty'>No logs yet</div>";return}
    var html="";
    for(var i=0;i<logs.length;i++){
      var l=logs[i];
      html+="<div class='le'><div class='ld "+l.status+"'></div>";
      html+="<div style='flex:1'><div style='display:flex;align-items:center;gap:8px'><span class='ln'>"+l.name+"</span><span class='lev'>"+l.event+"</span></div>";
      if(l.detail)html+="<div class='ldt'>"+l.detail+"</div>";
      html+="</div><div class='lt'>"+l.time.replace("T"," ").replace("Z","")+"</div></div>";
    }
    c.innerHTML=html;
  });
}
function filterLogs(btn,f){
  var btns=document.querySelectorAll(".fb");
  for(var i=0;i<btns.length;i++)btns[i].classList.remove("on");
  btn.classList.add("on");loadLogs(f);
}
function rename(btn){
  var mac=btn.getAttribute("data-mac");
  var cur=btn.getAttribute("data-name");
  var name=prompt("Rename (current: "+cur+"):",cur);
  if(!name||name===cur)return;
  fetch("/devices/rename",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mac:mac,name:name})})
    .then(function(r){return r.json()}).then(function(d){
      if(d.ok){toast("Renamed to "+name,"success");loadDevices()}
      else toast(d.error||"Failed","error");
    });
}
function loadHistory(){
  fetch("/history").then(function(r){return r.json()}).then(function(rows){
    var c=document.getElementById("hist");
    if(!rows.length){c.innerHTML="<div class='empty'>No uploads yet</div>";return}
    var html="<table class='ht'><thead><tr><th>Version</th><th>File</th><th>Size</th><th>MD5</th><th>Uploaded</th></tr></thead><tbody>";
    for(var i=0;i<rows.length;i++){
      var r=rows[i];
      html+="<tr><td><span class='badge'>"+r.version+"</span>"+(i===0?" current":"")+"</td>";
      html+="<td>"+r.filename+"</td><td>"+r.size_kb+" KB</td>";
      html+="<td style='font-size:11px;color:var(--muted)'>"+r.md5.slice(0,12)+"</td>";
      html+="<td style='color:var(--muted)'>"+r.uploaded+"</td></tr>";
    }
    html+="</tbody></table>";
    c.innerHTML=html;
  });
}
function toast(msg,type){
  var t=document.getElementById("toast");t.textContent=msg;t.className="toast "+type;
  clearTimeout(t._t);t._t=setTimeout(function(){t.className="toast"},3500);
}
function loadAll(){loadVer();loadDevices();loadStats();loadLogs();loadHistory()}
loadAll();
setInterval(loadAll,30000);
</script>
</body>
</html>"""

@app.route("/")
@require_login
def dashboard():
    return render_template_string(DASHBOARD_HTML)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
