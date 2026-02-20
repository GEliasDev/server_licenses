"""
routes/admin_panel.py - Panel web de administración
"""

from datetime import datetime
from flask import Blueprint, request, render_template_string
from models import db, License
from utils import require_admin, redirect_panel
from templates.panel import PANEL_HTML

bp = Blueprint('admin_panel', __name__)


@bp.route("/api/admin/panel")
def panel():
    """Panel de administración HTML"""
    if not require_admin(request):
        return "Unauthorized", 401
    
    lics = License.query.order_by(License.created_at.desc()).all()
    secret = request.args.get("secret", "")
    now = datetime.utcnow()
    
    # Calcular estadísticas
    active_24h = sum(1 for l in lics if l.last_seen and (now - l.last_seen).total_seconds() < 86400)
    inactive = sum(1 for l in lics if not l.last_seen or (now - l.last_seen).total_seconds() > 604800)
    revoked = sum(1 for l in lics if l.revoked)
    
    # Preparar datos para el template
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
    
    return render_template_string(
        PANEL_HTML, 
        licenses=data, 
        secret=secret,
        now=now,
        stats={
            'total': len(lics),
            'active_24h': active_24h,
            'inactive': inactive,
            'revoked': revoked
        }
    )


@bp.route("/api/admin/revoke_ui/<key>")
def revoke_ui(key):
    """Revocar licencia desde UI"""
    if not require_admin(request):
        return "Unauthorized", 401
    
    lic = License.query.filter_by(key=key.upper()).first()
    if lic:
        lic.revoked = True
        db.session.commit()
    
    return redirect_panel(request.args.get("secret", ""))


@bp.route("/api/admin/reactivate_ui/<key>")
def reactivate_ui(key):
    """Reactivar licencia desde UI"""
    if not require_admin(request):
        return "Unauthorized", 401
    
    lic = License.query.filter_by(key=key.upper()).first()
    if lic:
        lic.revoked = False
        db.session.commit()
    
    return redirect_panel(request.args.get("secret", ""))


@bp.route("/api/admin/reset_ui/<key>")
def reset_ui(key):
    """Reset de dispositivo desde UI"""
    if not require_admin(request):
        return "Unauthorized", 401
    
    lic = License.query.filter_by(key=key.upper()).first()
    if lic:
        lic.revoked = True
        lic.hw_id = ""
        db.session.commit()
        
        import threading
        import time
        
        def _reactivate(k=key.upper()):
            time.sleep(65)
            from app import app
            with app.app_context():
                l = License.query.filter_by(key=k).first()
                if l and l.revoked and not l.hw_id:
                    l.revoked = False
                    db.session.commit()
        
        threading.Thread(target=_reactivate, daemon=True).start()
    
    return redirect_panel(request.args.get("secret", ""))