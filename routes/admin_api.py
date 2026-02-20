"""
routes/admin_api.py - Endpoints de administración (API JSON)
"""

import threading
import time
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from models import db, License
from utils import require_admin, generate_key, make_expiry

bp = Blueprint('admin_api', __name__)


@bp.route("/api/admin/create", methods=["POST"])
def create():
    """Crea una nueva licencia"""
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

    # Si es petición de formulario HTML, redirigir al panel
    if not request.is_json:
        secret = request.args.get("secret", "")
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


@bp.route("/api/admin/revoke", methods=["POST"])
def revoke():
    """Revoca una licencia"""
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    
    key = (request.get_json(force=True).get("key") or "").upper()
    lic = License.query.filter_by(key=key).first()
    
    if not lic:
        return jsonify({"error": "No encontrada"}), 404
    
    lic.revoked = True
    db.session.commit()
    
    return jsonify({"revoked": key}), 200


@bp.route("/api/admin/reactivate", methods=["POST"])
def reactivate():
    """Reactiva una licencia revocada"""
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    
    key = (request.get_json(force=True).get("key") or "").upper()
    lic = License.query.filter_by(key=key).first()
    
    if not lic:
        return jsonify({"error": "No encontrada"}), 404
    
    lic.revoked = False
    db.session.commit()
    
    return jsonify({"reactivated": key}), 200


@bp.route("/api/admin/reset_device", methods=["POST"])
def reset_device():
    """Desvincula el dispositivo de una licencia"""
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    
    key = (request.get_json(force=True).get("key") or "").upper()
    lic = License.query.filter_by(key=key).first()
    
    if not lic:
        return jsonify({"error": "No encontrada"}), 404

    lic.revoked = True
    lic.hw_id = ""
    db.session.commit()

    def _reactivate():
        """Reactiva la licencia después de 65 segundos"""
        time.sleep(65)
        from app import app
        with app.app_context():
            l = License.query.filter_by(key=key).first()
            if l and l.revoked and not l.hw_id:
                l.revoked = False
                db.session.commit()
    
    threading.Thread(target=_reactivate, daemon=True).start()

    return jsonify({
        "reset": key, 
        "note": "Bot cerrará en ~60s, licencia libre en ~65s"
    }), 200


@bp.route("/api/admin/extend", methods=["POST"])
def extend():
    """Extiende la fecha de expiración de una licencia"""
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    
    data = request.get_json(force=True)
    key = (data.get("key") or "").upper()
    days = int(data.get("days", 30))
    
    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"error": "No encontrada"}), 404
    
    base = max(lic.expires_at or datetime.utcnow(), datetime.utcnow())
    lic.expires_at = base + timedelta(days=days)
    db.session.commit()
    
    return jsonify({"extended_until": lic.expires_at.isoformat()}), 200


@bp.route("/api/admin/list", methods=["GET"])
def list_licenses():
    """Lista todas las licencias"""
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


@bp.route("/api/admin/edit_license", methods=["POST"])
def edit_license():
    """Edita los datos de una licencia existente"""
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    
    data = request.get_json(force=True)
    key = (data.get("key") or "").upper()
    user = data.get("user", "")
    plan = data.get("plan", "")
    
    if plan not in ("monthly", "yearly", "lifetime"):
        return jsonify({"error": "Plan inválido"}), 400
    
    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"error": "No encontrada"}), 404
    
    # Actualizar datos
    lic.user = user
    
    # Si cambió el plan, recalcular expiración
    if lic.plan != plan:
        old_plan = lic.plan
        lic.plan = plan
        
        # Solo recalcular si no está expirada
        if not lic.expires_at or lic.expires_at > datetime.utcnow():
            lic.expires_at = make_expiry(plan)
    
    db.session.commit()
    
    return jsonify({
        "updated": key,
        "user": user,
        "plan": plan,
        "expires_at": lic.expires_at.isoformat() if lic.expires_at else "lifetime"
    }), 200


@bp.route("/api/admin/delete_license", methods=["POST"])
def delete_license():
    """Elimina permanentemente una licencia y todos sus datos relacionados"""
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    
    key = (request.get_json(force=True).get("key") or "").upper()
    
    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"error": "No encontrada"}), 404
    
    # SQLAlchemy eliminará automáticamente los registros relacionados
    # gracias al cascade='all, delete-orphan' en los modelos
    db.session.delete(lic)
    db.session.commit()
    
    return jsonify({"deleted": key}), 200