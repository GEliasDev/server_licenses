"""
server_api.py  –  Servidor de licencias (Flask)
================================================
Instalar: pip install flask flask-sqlalchemy gunicorn
"""

import os
import string
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ── BASE DE DATOS ─────────────────────────────────────────────────────────────
# Usa SQLite — simple, sin dependencias externas, perfecto para comenzar.
# El archivo licenses.db se crea automáticamente en el servidor.
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///licenses.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ── CLAVE ADMIN ───────────────────────────────────────────────────────────────
# Local  → usa el valor por defecto abajo
# Railway → configura variable ADMIN_SECRET en el panel de Variables
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "TU_CLAVE_ADMIN_MUY_SEGURA")


# ── MODELO ────────────────────────────────────────────────────────────────────

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


# ── ENDPOINT: VALIDAR (clientes) ──────────────────────────────────────────────

@app.route("/api/validate", methods=["POST"])
def validate():
    data  = request.get_json(force=True)
    key   = (data.get("key") or "").strip().upper()
    hw_id = (data.get("hw_id") or "").strip()

    if not key or not hw_id:
        return jsonify({"error": "INVALID"}), 403

    lic = License.query.filter_by(key=key).first()

    if not lic:
        return jsonify({"error": "INVALID"}), 403
    if lic.revoked:
        return jsonify({"error": "REVOKED"}), 403
    if lic.expires_at and datetime.utcnow() > lic.expires_at:
        return jsonify({"error": "EXPIRED"}), 403

    # Vincular dispositivo en el primer uso
    if not lic.hw_id:
        lic.hw_id = hw_id
    elif lic.hw_id != hw_id:
        return jsonify({"error": "WRONG_DEVICE"}), 403

    lic.last_seen   = datetime.utcnow()
    lic.activations += 1
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
    """Reactiva una licencia revocada."""
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
    """
    Desvincula el dispositivo y fuerza cierre del bot en ~60s.
    Revoca brevemente → cliente detecta REVOKED → borra caché → se cierra.
    A los 65s reactiva sin hw_id → cliente activa con su clave de nuevo.
    """
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
        "key":         l.key,
        "plan":        l.plan,
        "user":        l.user,
        "hw_id":       l.hw_id or "sin activar",
        "expires_at":  l.expires_at.isoformat() if l.expires_at else "lifetime",
        "revoked":     l.revoked,
        "last_seen":   l.last_seen.isoformat() if l.last_seen else "nunca",
        "activations": l.activations,
    } for l in lics])


# ── PANEL HTML ────────────────────────────────────────────────────────────────

PANEL_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Visual Bot — Licencias</title>
  <meta charset="utf-8">
  <style>
    body{font-family:monospace;background:#0e0f11;color:#d4d8e2;margin:32px}
    h1,h2{color:#00e5a0}
    table{border-collapse:collapse;width:100%;margin-top:8px}
    th,td{border:1px solid #2a2d35;padding:8px 12px;text-align:left;vertical-align:middle}
    th{background:#16181c;color:#00e5a0}
    tr:nth-child(even){background:#16181c}
    .revoked{color:#e05252;font-weight:bold}
    .active{color:#00e5a0;font-weight:bold}
    .form-create{margin-bottom:24px;background:#16181c;padding:16px;border:1px solid #2a2d35}
    input,select{background:#0e0f11;color:#d4d8e2;border:1px solid #2a2d35;padding:6px;font-family:monospace}
    .btn{border:none;padding:5px 10px;font-weight:bold;cursor:pointer;font-family:monospace;font-size:12px}
    .btn-create{background:#00e5a0;color:#0e0f11;padding:8px 18px}
    .btn-revoke{background:#e05252;color:#fff}
    .btn-reactivate{background:#00a870;color:#fff}
    .btn-reset{background:#f0a500;color:#0e0f11}
    .key{font-size:13px;letter-spacing:1px;color:#00e5a0}
    .hw{font-size:10px;color:#60657a}
  </style>
</head>
<body>
  <h1>Visual Bot — Panel de Licencias</h1>

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

  <h2>Licencias ({{ licenses|length }} total)</h2>
  <table>
    <tr>
      <th>Clave</th>
      <th>Plan</th>
      <th>Usuario</th>
      <th>Vence</th>
      <th>Dispositivo</th>
      <th>Último uso</th>
      <th>Estado</th>
      <th>Acciones</th>
    </tr>
    {% for l in licenses %}
    <tr>
      <td class="key">{{ l.key }}</td>
      <td>{{ l.plan }}</td>
      <td>{{ l.user or "—" }}</td>
      <td>{{ l.expires_at[:10] if l.expires_at and l.expires_at != "lifetime" else "♾ lifetime" }}</td>
      <td class="hw">{{ (l.hw_id or "sin activar")[:20] }}{% if l.hw_id %}...{% endif %}</td>
      <td style="font-size:11px">{{ l.last_seen[:16] if l.last_seen and l.last_seen != "nunca" else "nunca" }}</td>
      <td class="{{ 'revoked' if l.revoked else 'active' }}">
        {{ "REVOCADA" if l.revoked else "ACTIVA" }}
      </td>
      <td>
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
          &nbsp;
          <a href="/api/admin/reset_ui/{{ l.key }}?secret={{ secret }}"
             onclick="return confirm('¿Desvincular dispositivo? El cliente deberá ingresar su clave de nuevo en ~60s.')">
            <button class="btn btn-reset">Reset PC</button>
          </a>
        {% endif %}
      </td>
    </tr>
    {% endfor %}
  </table>

  <p style="color:#3a3f50;margin-top:24px;font-size:11px">
    ⚡ Los clientes re-validan cada 60 segundos. Una revocación tarda máximo 60s en aplicarse.
  </p>
</body>
</html>
"""

@app.route("/api/admin/panel")
def admin_panel():
    if not require_admin(request):
        return "Unauthorized", 401
    lics   = License.query.order_by(License.created_at.desc()).all()
    secret = request.args.get("secret", "")
    data   = []
    for l in lics:
        data.append({
            "key":         l.key,
            "plan":        l.plan,
            "user":        l.user,
            "hw_id":       l.hw_id or "",
            "expires_at":  l.expires_at.isoformat() if l.expires_at else "lifetime",
            "revoked":     l.revoked,
            "last_seen":   l.last_seen.isoformat() if l.last_seen else "nunca",
            "activations": l.activations,
        })
    return render_template_string(PANEL_HTML, licenses=data, secret=secret)


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
    db.create_all()

if __name__ == "__main__":
    print(f"✓ Panel: http://localhost:5000/api/admin/panel?secret={ADMIN_SECRET}")
    app.run(host="0.0.0.0", port=5000, debug=False)

