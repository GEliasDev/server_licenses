"""
server_api.py  –  Servidor de licencias con tracking avanzado (Flask)
========================================================================
Instalar: pip install flask flask-sqlalchemy gunicorn user-agents
"""

import os
import string
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.pool import NullPool
from user_agents import parse

app = Flask(__name__)

# ── BASE DE DATOS ─────────────────────────────────────────────────────────────
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'poolclass': NullPool}

db = SQLAlchemy(app)

# ── CLAVE ADMIN ───────────────────────────────────────────────────────────────
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "TU_CLAVE_ADMIN_MUY_SEGURA")


# ── MODELOS ───────────────────────────────────────────────────────────────────

class License(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    key         = db.Column(db.String(32), unique=True, nullable=False, index=True)
    plan        = db.Column(db.String(20), nullable=False)
    user        = db.Column(db.String(100), default="")
    hw_id       = db.Column(db.String(64), default="")
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at  = db.Column(db.DateTime, nullable=True)
    revoked     = db.Column(db.Boolean, default=False)
    last_seen   = db.Column(db.DateTime, nullable=True)
    activations = db.Column(db.Integer, default=0)
    
    # Nuevos campos para tracking
    first_activation = db.Column(db.DateTime, nullable=True)
    device_info      = db.Column(db.String(200), default="")  # OS, versión, etc.
    ip_address       = db.Column(db.String(45), default="")   # IPv4/IPv6
    
    # Relación con logs de actividad
    activity_logs = db.relationship('ActivityLog', backref='license', lazy='dynamic', 
                                    cascade='all, delete-orphan')


class ActivityLog(db.Model):
    """Registro detallado de cada validación/intento de acceso"""
    id           = db.Column(db.Integer, primary_key=True)
    license_id   = db.Column(db.Integer, db.ForeignKey('license.id'), nullable=False, index=True)
    timestamp    = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Información del dispositivo
    hw_id        = db.Column(db.String(64), default="")
    ip_address   = db.Column(db.String(45), default="")
    device_info  = db.Column(db.String(200), default="")
    user_agent   = db.Column(db.String(300), default="")
    
    # Resultado de la validación
    status       = db.Column(db.String(20), default="SUCCESS")  # SUCCESS, INVALID, REVOKED, EXPIRED, WRONG_DEVICE
    error_detail = db.Column(db.String(100), default="")
    
    # Metadata adicional
    app_version  = db.Column(db.String(20), default="")
    
    def __repr__(self):
        return f"<ActivityLog {self.timestamp} - {self.status}>"


class DeviceHistory(db.Model):
    """Historial de dispositivos únicos que han usado una licencia"""
    id           = db.Column(db.Integer, primary_key=True)
    license_id   = db.Column(db.Integer, db.ForeignKey('license.id'), nullable=False, index=True)
    hw_id        = db.Column(db.String(64), nullable=False)
    device_info  = db.Column(db.String(200), default="")
    first_seen   = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen    = db.Column(db.DateTime, default=datetime.utcnow)
    ip_addresses = db.Column(db.Text, default="")  # JSON array de IPs
    total_uses   = db.Column(db.Integer, default=1)
    is_current   = db.Column(db.Boolean, default=False)
    
    license = db.relationship('License', backref=db.backref('devices', lazy='dynamic'))


# ── GENERADOR DE CLAVES ───────────────────────────────────────────────────────

def generate_key(prefix="VB") -> str:
    chars = string.ascii_uppercase + string.digits
    groups = [prefix] + ["".join(random.choices(chars, k=4)) for _ in range(4)]
    return "-".join(groups)


def make_expiry(plan: str):
    if plan == "monthly":
        return datetime.utcnow() + timedelta(days=30)
    elif plan == "yearly":
        return datetime.utcnow() + timedelta(days=365)
    elif plan == "lifetime":
        return None
    else:
        raise ValueError(f"Plan desconocido: {plan}")


def get_device_info(user_agent_string: str) -> str:
    """Extrae información legible del user agent"""
    try:
        ua = parse(user_agent_string)
        return f"{ua.os.family} {ua.os.version_string} - {ua.browser.family}"
    except:
        return user_agent_string[:100] if user_agent_string else "Desconocido"


def log_activity(license_obj, hw_id, ip, status, error_detail="", app_version=""):
    """Registra cada intento de validación"""
    user_agent = request.headers.get('User-Agent', '')
    device_info = get_device_info(user_agent)
    
    log = ActivityLog(
        license_id=license_obj.id,
        hw_id=hw_id,
        ip_address=ip,
        device_info=device_info,
        user_agent=user_agent,
        status=status,
        error_detail=error_detail,
        app_version=app_version
    )
    db.session.add(log)
    
    # Actualizar o crear registro en DeviceHistory
    if hw_id:
        device = DeviceHistory.query.filter_by(
            license_id=license_obj.id, 
            hw_id=hw_id
        ).first()
        
        if device:
            device.last_seen = datetime.utcnow()
            device.total_uses += 1
            # Agregar IP si no existe
            import json
            ips = json.loads(device.ip_addresses) if device.ip_addresses else []
            if ip and ip not in ips:
                ips.append(ip)
                device.ip_addresses = json.dumps(ips)
        else:
            import json
            device = DeviceHistory(
                license_id=license_obj.id,
                hw_id=hw_id,
                device_info=device_info,
                ip_addresses=json.dumps([ip] if ip else []),
                is_current=(status == "SUCCESS")
            )
            db.session.add(device)


# ── ENDPOINT: VALIDAR (clientes) ──────────────────────────────────────────────

@app.route("/api/validate", methods=["POST"])
def validate():
    data        = request.get_json(force=True)
    key         = (data.get("key") or "").strip().upper()
    hw_id       = (data.get("hw_id") or "").strip()
    app_version = data.get("app_version", "")
    ip          = request.headers.get('X-Forwarded-For', request.remote_addr)

    if not key or not hw_id:
        return jsonify({"error": "INVALID"}), 403

    lic = License.query.filter_by(key=key).first()

    if not lic:
        # Log de intento fallido con clave inválida
        fake_lic = License(id=0, key=key)
        log_activity(fake_lic, hw_id, ip, "INVALID", "Clave no existe", app_version)
        db.session.commit()
        return jsonify({"error": "INVALID"}), 403
    
    # Verificar revocación
    if lic.revoked:
        log_activity(lic, hw_id, ip, "REVOKED", "Licencia revocada", app_version)
        db.session.commit()
        return jsonify({"error": "REVOKED"}), 403
    
    # Verificar expiración
    if lic.expires_at and datetime.utcnow() > lic.expires_at:
        log_activity(lic, hw_id, ip, "EXPIRED", "Licencia expirada", app_version)
        db.session.commit()
        return jsonify({"error": "EXPIRED"}), 403

    # Vincular dispositivo en el primer uso
    if not lic.hw_id:
        lic.hw_id = hw_id
        lic.first_activation = datetime.utcnow()
        lic.device_info = get_device_info(request.headers.get('User-Agent', ''))
        lic.ip_address = ip
    elif lic.hw_id != hw_id:
        log_activity(lic, hw_id, ip, "WRONG_DEVICE", 
                    f"Intento desde dispositivo no autorizado", app_version)
        db.session.commit()
        return jsonify({"error": "WRONG_DEVICE"}), 403

    # Actualizar última actividad
    lic.last_seen   = datetime.utcnow()
    lic.activations += 1
    lic.ip_address  = ip
    
    # Log exitoso
    log_activity(lic, hw_id, ip, "SUCCESS", "", app_version)
    
    # Marcar dispositivo actual
    DeviceHistory.query.filter_by(license_id=lic.id).update({"is_current": False})
    current_device = DeviceHistory.query.filter_by(license_id=lic.id, hw_id=hw_id).first()
    if current_device:
        current_device.is_current = True
    
    db.session.commit()

    return jsonify({
        "valid":      True,
        "plan":       lic.plan,
        "user":       lic.user,
        "expires_at": lic.expires_at.isoformat() if lic.expires_at else "lifetime",
    }), 200


# ── HELPERS ADMIN ─────────────────────────────────────────────────────────────

def require_admin(req):
    secret = req.headers.get("X-Admin-Secret") or req.args.get("secret", "")
    return secret == ADMIN_SECRET


def _redirect_panel(secret):
    return f'<meta http-equiv="refresh" content="0;url=/api/admin/panel?secret={secret}"/>'


# ── ENDPOINTS ADMIN ───────────────────────────────────────────────────────────

@app.route("/api/admin/create", methods=["POST"])
def admin_create():
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401

    data = request.get_json(force=True) if request.is_json else request.form
    plan = data.get("plan", "monthly")
    user = data.get("user", "")

    if plan not in ("monthly", "yearly", "lifetime"):
        return jsonify({"error": "Plan inválido"}), 400

    key = generate_key()
    while License.query.filter_by(key=key).first():
        key = generate_key()

    lic = License(key=key, plan=plan, user=user, expires_at=make_expiry(plan))
    db.session.add(lic)
    db.session.commit()

    if not request.is_json:
        secret      = request.args.get("secret", "")
        expires_str = lic.expires_at.isoformat() if lic.expires_at else "lifetime"
        return (
            f"<html><body style='background:#0e0f11;color:#d4d8e2;font-family:monospace;padding:32px'>"
            f"<h2 style='color:#00e5a0'>✓ Licencia creada</h2>"
            f"<p>Clave: <b style='color:#00e5a0;font-size:1.4em'>{key}</b></p>"
            f"<p>Plan: {plan} &nbsp;|&nbsp; Usuario: {user} &nbsp;|&nbsp; Vence: {expires_str}</p>"
            f"<br><a href='/api/admin/panel?secret={secret}' style='color:#00e5a0'>← Volver al panel</a>"
            f"</body></html>"
        )
    return jsonify({
        "key":        key,
        "plan":       plan,
        "user":       user,
        "expires_at": lic.expires_at.isoformat() if lic.expires_at else "lifetime",
    }), 201


@app.route("/api/admin/revoke", methods=["POST"])
def admin_revoke():
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    key = (request.get_json(force=True).get("key") or "").upper()
    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"error": "No encontrada"}), 404
    lic.revoked = True
    db.session.commit()
    return jsonify({"revoked": key}), 200


@app.route("/api/admin/reactivate", methods=["POST"])
def admin_reactivate():
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    key = (request.get_json(force=True).get("key") or "").upper()
    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"error": "No encontrada"}), 404
    lic.revoked = False
    db.session.commit()
    return jsonify({"reactivated": key}), 200


@app.route("/api/admin/reset_device", methods=["POST"])
def admin_reset_device():
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    key = (request.get_json(force=True).get("key") or "").upper()
    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"error": "No encontrada"}), 404

    lic.revoked = True
    lic.hw_id   = ""
    db.session.commit()

    import threading
    def _reactivate():
        import time
        time.sleep(65)
        with app.app_context():
            l = License.query.filter_by(key=key).first()
            if l and l.revoked and not l.hw_id:
                l.revoked = False
                db.session.commit()
    threading.Thread(target=_reactivate, daemon=True).start()

    return jsonify({"reset": key, "note": "Bot cerrará en ~60s, licencia libre en ~65s"}), 200


@app.route("/api/admin/extend", methods=["POST"])
def admin_extend():
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    data = request.get_json(force=True)
    key  = (data.get("key") or "").upper()
    days = int(data.get("days", 30))
    lic  = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"error": "No encontrada"}), 404
    base = max(lic.expires_at or datetime.utcnow(), datetime.utcnow())
    lic.expires_at = base + timedelta(days=days)
    db.session.commit()
    return jsonify({"extended_until": lic.expires_at.isoformat()}), 200


@app.route("/api/admin/list", methods=["GET"])
def admin_list():
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    lics = License.query.order_by(License.created_at.desc()).all()
    return jsonify([{
        "key":              l.key,
        "plan":             l.plan,
        "user":             l.user,
        "hw_id":            l.hw_id or "sin activar",
        "expires_at":       l.expires_at.isoformat() if l.expires_at else "lifetime",
        "revoked":          l.revoked,
        "last_seen":        l.last_seen.isoformat() if l.last_seen else "nunca",
        "first_activation": l.first_activation.isoformat() if l.first_activation else None,
        "activations":      l.activations,
        "device_info":      l.device_info,
        "ip_address":       l.ip_address,
    } for l in lics])


# ── NUEVOS ENDPOINTS DE ANALYTICS ────────────────────────────────────────────

@app.route("/api/admin/license_details/<key>")
def license_details(key):
    """Información detallada de una licencia específica"""
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    
    lic = License.query.filter_by(key=key.upper()).first()
    if not lic:
        return jsonify({"error": "No encontrada"}), 404
    
    # Logs de actividad (últimos 100)
    logs = ActivityLog.query.filter_by(license_id=lic.id)\
                            .order_by(ActivityLog.timestamp.desc())\
                            .limit(100).all()
    
    # Dispositivos históricos
    devices = DeviceHistory.query.filter_by(license_id=lic.id)\
                                 .order_by(DeviceHistory.last_seen.desc()).all()
    
    # Estadísticas
    import json
    total_attempts = len(logs)
    success_count = sum(1 for log in logs if log.status == "SUCCESS")
    failed_count = total_attempts - success_count
    unique_ips = len(set(log.ip_address for log in logs if log.ip_address))
    
    return jsonify({
        "license": {
            "key":              lic.key,
            "plan":             lic.plan,
            "user":             lic.user,
            "created_at":       lic.created_at.isoformat(),
            "first_activation": lic.first_activation.isoformat() if lic.first_activation else None,
            "expires_at":       lic.expires_at.isoformat() if lic.expires_at else "lifetime",
            "last_seen":        lic.last_seen.isoformat() if lic.last_seen else None,
            "revoked":          lic.revoked,
            "activations":      lic.activations,
            "current_hw_id":    lic.hw_id,
            "device_info":      lic.device_info,
            "ip_address":       lic.ip_address,
        },
        "statistics": {
            "total_attempts": total_attempts,
            "successful":     success_count,
            "failed":         failed_count,
            "unique_ips":     unique_ips,
            "unique_devices": len(devices),
        },
        "recent_activity": [{
            "timestamp":    log.timestamp.isoformat(),
            "status":       log.status,
            "hw_id":        log.hw_id[:20] + "..." if len(log.hw_id) > 20 else log.hw_id,
            "ip":           log.ip_address,
            "device_info":  log.device_info,
            "error_detail": log.error_detail,
            "app_version":  log.app_version,
        } for log in logs],
        "devices": [{
            "hw_id":        dev.hw_id,
            "device_info":  dev.device_info,
            "first_seen":   dev.first_seen.isoformat(),
            "last_seen":    dev.last_seen.isoformat(),
            "total_uses":   dev.total_uses,
            "is_current":   dev.is_current,
            "ip_addresses": json.loads(dev.ip_addresses) if dev.ip_addresses else [],
        } for dev in devices]
    })


@app.route("/api/admin/suspicious_activity")
def suspicious_activity():
    """Detecta actividad sospechosa"""
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    
    # Buscar licencias con múltiples dispositivos intentando acceso
    suspicious = []
    
    for lic in License.query.all():
        devices = DeviceHistory.query.filter_by(license_id=lic.id).all()
        
        # Más de 2 dispositivos diferentes
        if len(devices) > 2:
            suspicious.append({
                "key": lic.key,
                "user": lic.user,
                "reason": f"{len(devices)} dispositivos diferentes detectados",
                "devices": len(devices),
                "severity": "HIGH"
            })
        
        # Intentos fallidos recientes
        recent_fails = ActivityLog.query.filter(
            ActivityLog.license_id == lic.id,
            ActivityLog.status != "SUCCESS",
            ActivityLog.timestamp > datetime.utcnow() - timedelta(days=1)
        ).count()
        
        if recent_fails > 5:
            suspicious.append({
                "key": lic.key,
                "user": lic.user,
                "reason": f"{recent_fails} intentos fallidos en 24h",
                "devices": len(devices),
                "severity": "MEDIUM"
            })
        
        # IPs muy diferentes geográficamente (simplificado)
        import json
        unique_ips = set()
        for dev in devices:
            if dev.ip_addresses:
                unique_ips.update(json.loads(dev.ip_addresses))
        
        if len(unique_ips) > 5:
            suspicious.append({
                "key": lic.key,
                "user": lic.user,
                "reason": f"{len(unique_ips)} IPs diferentes",
                "devices": len(devices),
                "severity": "LOW"
            })
    
    return jsonify({"suspicious_licenses": suspicious, "total": len(suspicious)})


@app.route("/api/admin/activity_summary")
def activity_summary():
    """Resumen de actividad general"""
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    
    now = datetime.utcnow()
    last_24h = now - timedelta(days=1)
    last_7d = now - timedelta(days=7)
    
    # Licencias activas (vistas en últimas 24h)
    active_24h = License.query.filter(License.last_seen >= last_24h).count()
    active_7d = License.query.filter(License.last_seen >= last_7d).count()
    
    # Intentos de validación
    attempts_24h = ActivityLog.query.filter(ActivityLog.timestamp >= last_24h).count()
    success_24h = ActivityLog.query.filter(
        ActivityLog.timestamp >= last_24h,
        ActivityLog.status == "SUCCESS"
    ).count()
    
    # Licencias inactivas (no vistas en 7 días)
    total_licenses = License.query.count()
    inactive = License.query.filter(
        (License.last_seen < last_7d) | (License.last_seen == None)
    ).count()
    
    return jsonify({
        "summary": {
            "total_licenses":        total_licenses,
            "active_last_24h":       active_24h,
            "active_last_7d":        active_7d,
            "inactive_7d":           inactive,
            "validation_attempts_24h": attempts_24h,
            "successful_24h":        success_24h,
            "failed_24h":            attempts_24h - success_24h,
        },
        "timestamp": now.isoformat()
    })


# ── PANEL HTML MEJORADO ───────────────────────────────────────────────────────

PANEL_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Visual Bot — Licencias Advanced</title>
  <meta charset="utf-8">
  <style>
    body{font-family:monospace;background:#0e0f11;color:#d4d8e2;margin:0;padding:0}
    .container{max-width:1400px;margin:0 auto;padding:32px}
    h1,h2{color:#00e5a0}
    .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:24px 0}
    .stat-card{background:#16181c;padding:16px;border:1px solid #2a2d35;border-radius:4px}
    .stat-card .label{color:#60657a;font-size:11px;text-transform:uppercase}
    .stat-card .value{color:#00e5a0;font-size:28px;font-weight:bold;margin-top:8px}
    table{border-collapse:collapse;width:100%;margin-top:8px}
    th,td{border:1px solid #2a2d35;padding:8px 12px;text-align:left;vertical-align:middle}
    th{background:#16181c;color:#00e5a0;position:sticky;top:0}
    tr:nth-child(even){background:#16181c}
    tr:hover{background:#1a1d24}
    .revoked{color:#e05252;font-weight:bold}
    .active{color:#00e5a0;font-weight:bold}
    .warning{color:#f0a500;font-weight:bold}
    .form-create{margin-bottom:24px;background:#16181c;padding:16px;border:1px solid #2a2d35}
    input,select{background:#0e0f11;color:#d4d8e2;border:1px solid #2a2d35;padding:6px;font-family:monospace}
    .btn{border:none;padding:5px 10px;font-weight:bold;cursor:pointer;font-family:monospace;font-size:12px;border-radius:3px;text-decoration:none;display:inline-block}
    .btn-create{background:#00e5a0;color:#0e0f11;padding:8px 18px}
    .btn-revoke{background:#e05252;color:#fff}
    .btn-reactivate{background:#00a870;color:#fff}
    .btn-reset{background:#f0a500;color:#0e0f11}
    .btn-details{background:#3a7bd5;color:#fff;font-size:11px}
    .key{font-size:13px;letter-spacing:1px;color:#00e5a0;font-weight:bold}
    .hw{font-size:10px;color:#60657a}
    .status-indicator{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
    .status-online{background:#00e5a0}
    .status-offline{background:#60657a}
    .status-warning{background:#f0a500}
    .tabs{display:flex;gap:8px;margin:24px 0;border-bottom:2px solid #2a2d35}
    .tab{padding:12px 24px;background:transparent;color:#60657a;cursor:pointer;border:none;font-family:monospace;font-weight:bold}
    .tab.active{color:#00e5a0;border-bottom:2px solid #00e5a0;margin-bottom:-2px}
    .tab-content{display:none}
    .tab-content.active{display:block}
    .device-badge{display:inline-block;background:#2a2d35;padding:4px 8px;border-radius:3px;font-size:10px;margin:2px}
    .modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:1000}
    .modal-content{background:#16181c;margin:50px auto;padding:24px;max-width:900px;max-height:80vh;overflow-y:auto;border:1px solid #2a2d35}
    .close{float:right;font-size:28px;font-weight:bold;color:#60657a;cursor:pointer}
    .close:hover{color:#00e5a0}
    .activity-log{font-size:11px}
    .activity-log .success{color:#00e5a0}
    .activity-log .failed{color:#e05252}
  </style>
</head>
<body>
  <div class="container">
    <h1>🚀 Visual Bot — Panel Avanzado</h1>
    
    <!-- Stats Dashboard -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="label">Total Licencias</div>
        <div class="value">{{ stats.total }}</div>
      </div>
      <div class="stat-card">
        <div class="label">Activas (24h)</div>
        <div class="value" style="color:#00e5a0">{{ stats.active_24h }}</div>
      </div>
      <div class="stat-card">
        <div class="label">Inactivas (7d+)</div>
        <div class="value" style="color:#f0a500">{{ stats.inactive }}</div>
      </div>
      <div class="stat-card">
        <div class="label">Revocadas</div>
        <div class="value" style="color:#e05252">{{ stats.revoked }}</div>
      </div>
    </div>

    <!-- Create Form -->
    <div class="form-create">
      <b>Crear nueva licencia</b><br><br>
      <form method="POST" action="/api/admin/create?secret={{ secret }}">
        Usuario/Email: <input name="user" placeholder="nombre o email" size="22">
        &nbsp; Plan:
        <select name="plan">
          <option value="monthly">Mensual (30 días)</option>
          <option value="yearly">Anual (365 días)</option>
          <option value="lifetime">De por vida</option>
        </select>
        &nbsp;
        <button type="submit" class="btn btn-create">CREAR</button>
      </form>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab active" onclick="showTab('all')">Todas las licencias</button>
      <button class="tab" onclick="showTab('active')">Activas</button>
      <button class="tab" onclick="showTab('suspicious')">Actividad Sospechosa</button>
    </div>

    <!-- Tab: All Licenses -->
    <div class="tab-content active" id="tab-all">
      <h2>Licencias ({{ licenses|length }})</h2>
      <table>
        <tr>
          <th>Estado</th>
          <th>Clave</th>
          <th>Plan</th>
          <th>Usuario</th>
          <th>Vence</th>
          <th>Dispositivo Actual</th>
          <th>Primera/Última Actividad</th>
          <th>Usos</th>
          <th>Acciones</th>
        </tr>
        {% for l in licenses %}
        <tr>
          <td>
            {% if l.last_seen and l.last_seen != "nunca" %}
              {% set hours_ago = ((now - l.last_seen_dt).total_seconds() / 3600) | int %}
              {% if hours_ago < 1 %}
                <span class="status-indicator status-online"></span>
              {% elif hours_ago < 24 %}
                <span class="status-indicator status-warning"></span>
              {% else %}
                <span class="status-indicator status-offline"></span>
              {% endif %}
            {% else %}
              <span class="status-indicator status-offline"></span>
            {% endif %}
          </td>
          <td class="key">{{ l.key }}</td>
          <td>{{ l.plan }}</td>
          <td>{{ l.user or "—" }}</td>
          <td>{{ l.expires_at[:10] if l.expires_at and l.expires_at != "lifetime" else "♾ lifetime" }}</td>
          <td class="hw">
            {{ (l.hw_id or "sin activar")[:16] }}{% if l.hw_id and l.hw_id|length > 16 %}...{% endif %}
            {% if l.device_info %}<br><small style="color:#3a3f50">{{ l.device_info[:30] }}</small>{% endif %}
          </td>
          <td style="font-size:11px">
            {% if l.first_activation and l.first_activation != "nunca" %}
              <b>1ª:</b> {{ l.first_activation[:10] }}<br>
            {% endif %}
            <b>Ult:</b> {{ l.last_seen[:16] if l.last_seen and l.last_seen != "nunca" else "nunca" }}
          </td>
          <td style="text-align:center">{{ l.activations }}</td>
          <td>
            <a href="#" onclick="showDetails('{{ l.key }}', '{{ secret }}'); return false" class="btn btn-details">📊 Detalles</a>
            <br><br>
            {% if l.revoked %}
              <a href="/api/admin/reactivate_ui/{{ l.key }}?secret={{ secret }}"
                 onclick="return confirm('¿Reactivar esta licencia?')">
                <button class="btn btn-reactivate">Reactivar</button>
              </a>
            {% else %}
              <a href="/api/admin/revoke_ui/{{ l.key }}?secret={{ secret }}"
                 onclick="return confirm('¿Revocar? El cliente perderá acceso en ~60 segundos.')">
                <button class="btn btn-revoke">Revocar</button>
              </a>
              <br><br>
              <a href="/api/admin/reset_ui/{{ l.key }}?secret={{ secret }}"
                 onclick="return confirm('¿Desvincular dispositivo? El cliente deberá ingresar su clave de nuevo en ~60s.')">
                <button class="btn btn-reset">Reset PC</button>
              </a>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </table>
    </div>

    <!-- Tab: Active -->
    <div class="tab-content" id="tab-active">
      <h2>Licencias Activas (últimas 24h)</h2>
      <table>
        <tr>
          <th>Clave</th>
          <th>Usuario</th>
          <th>Plan</th>
          <th>Última Actividad</th>
          <th>IP</th>
        </tr>
        {% for l in licenses if l.last_seen_dt and (now - l.last_seen_dt).total_seconds() < 86400 %}
        <tr>
          <td class="key">{{ l.key }}</td>
          <td>{{ l.user or "—" }}</td>
          <td>{{ l.plan }}</td>
          <td>{{ l.last_seen[:16] }}</td>
          <td class="hw">{{ l.ip_address or "—" }}</td>
        </tr>
        {% endfor %}
      </table>
    </div>

    <!-- Tab: Suspicious -->
    <div class="tab-content" id="tab-suspicious">
      <h2>Actividad Sospechosa</h2>
      <p style="color:#60657a">Licencias con múltiples dispositivos o intentos fallidos recientes</p>
      <div id="suspicious-content">Cargando...</div>
    </div>

    <p style="color:#3a3f50;margin-top:24px;font-size:11px">
      🟢 Online (< 1h) &nbsp; 🟡 Reciente (< 24h) &nbsp; ⚫ Offline (> 24h)
      <br>
      Los clientes re-validan cada 60 segundos. Una revocación tarda máximo 60s en aplicarse.
    </p>
  </div>

  <!-- Modal for Details -->
  <div id="detailsModal" class="modal">
    <div class="modal-content">
      <span class="close" onclick="closeDetails()">&times;</span>
      <div id="detailsContent">Cargando...</div>
    </div>
  </div>

  <script>
    function showTab(tab) {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById('tab-' + tab).classList.add('active');
      
      if (tab === 'suspicious') {
        loadSuspicious();
      }
    }

    function loadSuspicious() {
      fetch('/api/admin/suspicious_activity?secret={{ secret }}')
        .then(r => r.json())
        .then(data => {
          const content = document.getElementById('suspicious-content');
          if (data.suspicious_licenses.length === 0) {
            content.innerHTML = '<p style="color:#00e5a0">✓ No se detectó actividad sospechosa</p>';
            return;
          }
          
          let html = '<table><tr><th>Clave</th><th>Usuario</th><th>Motivo</th><th>Severidad</th></tr>';
          data.suspicious_licenses.forEach(s => {
            const color = s.severity === 'HIGH' ? '#e05252' : s.severity === 'MEDIUM' ? '#f0a500' : '#60657a';
            html += `<tr>
              <td class="key">${s.key}</td>
              <td>${s.user || '—'}</td>
              <td>${s.reason}</td>
              <td style="color:${color};font-weight:bold">${s.severity}</td>
            </tr>`;
          });
          html += '</table>';
          content.innerHTML = html;
        });
    }

    function showDetails(key, secret) {
      document.getElementById('detailsModal').style.display = 'block';
      document.getElementById('detailsContent').innerHTML = 'Cargando detalles...';
      
      fetch(`/api/admin/license_details/${key}?secret=${secret}`)
        .then(r => r.json())
        .then(data => {
          let html = `
            <h2 style="color:#00e5a0">Detalles: ${data.license.key}</h2>
            <div style="background:#0e0f11;padding:16px;margin:16px 0">
              <b>Usuario:</b> ${data.license.user || '—'}<br>
              <b>Plan:</b> ${data.license.plan}<br>
              <b>Creada:</b> ${data.license.created_at.substring(0,16)}<br>
              <b>Primera activación:</b> ${data.license.first_activation ? data.license.first_activation.substring(0,16) : 'Nunca'}<br>
              <b>Vence:</b> ${data.license.expires_at !== 'lifetime' ? data.license.expires_at.substring(0,16) : '♾ lifetime'}<br>
              <b>Estado:</b> ${data.license.revoked ? '<span class="revoked">REVOCADA</span>' : '<span class="active">ACTIVA</span>'}<br>
              <b>Dispositivo actual:</b> ${data.license.current_hw_id || 'Sin activar'}<br>
              <b>Info dispositivo:</b> ${data.license.device_info || '—'}<br>
              <b>IP actual:</b> ${data.license.ip_address || '—'}
            </div>
            
            <h3>📊 Estadísticas</h3>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:12px 0">
              <div class="stat-card">
                <div class="label">Total intentos</div>
                <div class="value" style="font-size:20px">${data.statistics.total_attempts}</div>
              </div>
              <div class="stat-card">
                <div class="label">Exitosos</div>
                <div class="value" style="font-size:20px;color:#00e5a0">${data.statistics.successful}</div>
              </div>
              <div class="stat-card">
                <div class="label">Fallidos</div>
                <div class="value" style="font-size:20px;color:#e05252">${data.statistics.failed}</div>
              </div>
              <div class="stat-card">
                <div class="label">IPs únicas</div>
                <div class="value" style="font-size:20px">${data.statistics.unique_ips}</div>
              </div>
            </div>
            
            <h3>💻 Dispositivos (${data.devices.length})</h3>
            <table style="font-size:11px">
              <tr><th>HW ID</th><th>Dispositivo</th><th>Primera vez</th><th>Última vez</th><th>Usos</th><th>IPs</th></tr>
              ${data.devices.map(d => `
                <tr style="${d.is_current ? 'background:#1a2d1a' : ''}">
                  <td class="hw">${d.hw_id.substring(0,20)}...</td>
                  <td>${d.device_info}</td>
                  <td>${d.first_seen.substring(0,16)}</td>
                  <td>${d.last_seen.substring(0,16)}</td>
                  <td>${d.total_uses}</td>
                  <td class="hw">${d.ip_addresses.length} IP${d.ip_addresses.length !== 1 ? 's' : ''}</td>
                </tr>
              `).join('')}
            </table>
            
            <h3>📝 Actividad Reciente (últimos 50)</h3>
            <div class="activity-log" style="max-height:300px;overflow-y:auto">
              <table style="font-size:10px">
                <tr><th>Fecha</th><th>Estado</th><th>Dispositivo</th><th>IP</th><th>Info</th></tr>
                ${data.recent_activity.slice(0,50).map(a => `
                  <tr>
                    <td>${a.timestamp.substring(0,16)}</td>
                    <td class="${a.status === 'SUCCESS' ? 'success' : 'failed'}">${a.status}</td>
                    <td class="hw">${a.hw_id}</td>
                    <td class="hw">${a.ip}</td>
                    <td>${a.error_detail || a.device_info}</td>
                  </tr>
                `).join('')}
              </table>
            </div>
          `;
          document.getElementById('detailsContent').innerHTML = html;
        })
        .catch(err => {
          document.getElementById('detailsContent').innerHTML = 
            '<p style="color:#e05252">Error al cargar detalles</p>';
        });
    }

    function closeDetails() {
      document.getElementById('detailsModal').style.display = 'none';
    }

    window.onclick = function(event) {
      const modal = document.getElementById('detailsModal');
      if (event.target == modal) {
        modal.style.display = 'none';
      }
    }
  </script>
</body>
</html>
"""

@app.route("/api/admin/panel")
def admin_panel():
    if not require_admin(request):
        return "Unauthorized", 401
    
    lics   = License.query.order_by(License.created_at.desc()).all()
    secret = request.args.get("secret", "")
    now    = datetime.utcnow()
    
    # Calcular estadísticas
    active_24h = sum(1 for l in lics if l.last_seen and (now - l.last_seen).total_seconds() < 86400)
    inactive = sum(1 for l in lics if not l.last_seen or (now - l.last_seen).total_seconds() > 604800)
    revoked = sum(1 for l in lics if l.revoked)
    
    data = []
    for l in lics:
        data.append({
            "key":              l.key,
            "plan":             l.plan,
            "user":             l.user,
            "hw_id":            l.hw_id or "",
            "expires_at":       l.expires_at.isoformat() if l.expires_at else "lifetime",
            "revoked":          l.revoked,
            "last_seen":        l.last_seen.isoformat() if l.last_seen else "nunca",
            "last_seen_dt":     l.last_seen,
            "first_activation": l.first_activation.isoformat() if l.first_activation else "nunca",
            "activations":      l.activations,
            "device_info":      l.device_info,
            "ip_address":       l.ip_address,
        })
    
    return render_template_string(PANEL_HTML, 
                                licenses=data, 
                                secret=secret,
                                now=now,
                                stats={
                                    'total': len(lics),
                                    'active_24h': active_24h,
                                    'inactive': inactive,
                                    'revoked': revoked
                                })


# ── ACCIONES UI ───────────────────────────────────────────────────────────────

@app.route("/api/admin/revoke_ui/<key>")
def revoke_ui(key):
    if not require_admin(request):
        return "Unauthorized", 401
    lic = License.query.filter_by(key=key.upper()).first()
    if lic:
        lic.revoked = True
        db.session.commit()
    return _redirect_panel(request.args.get("secret", ""))


@app.route("/api/admin/reactivate_ui/<key>")
def reactivate_ui(key):
    if not require_admin(request):
        return "Unauthorized", 401
    lic = License.query.filter_by(key=key.upper()).first()
    if lic:
        lic.revoked = False
        db.session.commit()
    return _redirect_panel(request.args.get("secret", ""))


@app.route("/api/admin/reset_ui/<key>")
def reset_ui(key):
    if not require_admin(request):
        return "Unauthorized", 401
    lic = License.query.filter_by(key=key.upper()).first()
    if lic:
        lic.revoked = True
        lic.hw_id   = ""
        db.session.commit()
        import threading
        def _reactivate(k=key.upper()):
            import time
            time.sleep(65)
            with app.app_context():
                l = License.query.filter_by(key=k).first()
                if l and l.revoked and not l.hw_id:
                    l.revoked = False
                    db.session.commit()
        threading.Thread(target=_reactivate, daemon=True).start()
    return _redirect_panel(request.args.get("secret", ""))


# ── INICIO ────────────────────────────────────────────────────────────────────
with app.app_context():
    if app.config["SQLALCHEMY_DATABASE_URI"] and app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://", 1)
    db.create_all()

if __name__ == "__main__":
    print(f"✓ Panel Avanzado: http://localhost:5000/api/admin/panel?secret={ADMIN_SECRET}")
    app.run(host="0.0.0.0", port=5000, debug=False)
