"""
utils.py - Funciones de utilidad
"""

import string
import random
import json
from datetime import datetime, timedelta
from flask import request
from user_agents import parse
from models import db, ActivityLog, DeviceHistory


def generate_key(prefix="VB") -> str:
    """Genera una clave de licencia única"""
    chars = string.ascii_uppercase + string.digits
    groups = [prefix] + ["".join(random.choices(chars, k=4)) for _ in range(4)]
    return "-".join(groups)


def make_expiry(plan: str):
    """Calcula fecha de expiración según el plan"""
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


def get_client_ip(request) -> str:
    """
    Extrae la IP real del cliente, manejando proxies y CDNs.
    
    Orden de prioridad:
    1. CF-Connecting-IP (Cloudflare)
    2. X-Real-IP (Nginx)
    3. X-Forwarded-For (primer IP en la cadena)
    4. request.remote_addr (fallback)
    """
    # Cloudflare pone la IP real del cliente aquí
    if request.headers.get('CF-Connecting-IP'):
        return request.headers.get('CF-Connecting-IP')
    
    # Nginx y otros proxies
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    
    # X-Forwarded-For puede tener múltiples IPs: "client, proxy1, proxy2"
    # Tomamos solo la primera (la del cliente real)
    if request.headers.get('X-Forwarded-For'):
        ips = request.headers.get('X-Forwarded-For').split(',')
        return ips[0].strip()
    
    # Fallback
    return request.remote_addr or "Unknown"


def log_activity(license_obj, hw_id, ip, status, error_detail="", app_version=""):
    """Registra cada intento de validación"""
    user_agent = request.headers.get('User-Agent', '')
    device_info = get_device_info(user_agent)
    
    # Asegurar que tengamos solo la IP real del cliente
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    
    # Crear log de actividad
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
            ips = json.loads(device.ip_addresses) if device.ip_addresses else []
            if ip and ip not in ips:
                ips.append(ip)
                device.ip_addresses = json.dumps(ips)
        else:
            device = DeviceHistory(
                license_id=license_obj.id,
                hw_id=hw_id,
                device_info=device_info,
                ip_addresses=json.dumps([ip] if ip else []),
                is_current=(status == "SUCCESS")
            )
            db.session.add(device)


def require_admin(req):
    """Verifica si la petición tiene credenciales de admin"""
    from config import Config
    secret = req.headers.get("X-Admin-Secret") or req.args.get("secret", "")
    return secret == Config.ADMIN_SECRET


def redirect_panel(secret):
    """Genera HTML de redirección al panel"""
    return f'<meta http-equiv="refresh" content="0;url=/api/admin/panel?secret={secret}"/>'