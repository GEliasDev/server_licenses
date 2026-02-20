"""
routes/validation.py - Endpoints de validación de licencias (API pública)
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from models import db, License, DeviceHistory
from utils import log_activity, get_device_info

bp = Blueprint('validation', __name__)


@bp.route("/api/validate", methods=["POST"])
def validate():
    """Valida una licencia y vincula el dispositivo"""
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
                    "Intento desde dispositivo no autorizado", app_version)
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