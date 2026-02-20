"""
routes/analytics.py - Endpoints de análisis y estadísticas
"""

import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from models import db, License, ActivityLog, DeviceHistory
from utils import require_admin

bp = Blueprint('analytics', __name__)


@bp.route("/api/admin/license_details/<key>")
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


@bp.route("/api/admin/suspicious_activity")
def suspicious_activity():
    """Detecta actividad sospechosa"""
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    
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
        
        # IPs muy diferentes
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


@bp.route("/api/admin/activity_summary")
def activity_summary():
    """Resumen de actividad general"""
    if not require_admin(request):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    
    now = datetime.utcnow()
    last_24h = now - timedelta(days=1)
    last_7d = now - timedelta(days=7)
    
    # Licencias activas
    active_24h = License.query.filter(License.last_seen >= last_24h).count()
    active_7d = License.query.filter(License.last_seen >= last_7d).count()
    
    # Intentos de validación
    attempts_24h = ActivityLog.query.filter(ActivityLog.timestamp >= last_24h).count()
    success_24h = ActivityLog.query.filter(
        ActivityLog.timestamp >= last_24h,
        ActivityLog.status == "SUCCESS"
    ).count()
    
    # Licencias inactivas
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