"""
models.py - Modelos de base de datos SQLAlchemy
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class License(db.Model):
    """Modelo principal de licencias"""
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
    
    # Campos de tracking
    first_activation = db.Column(db.DateTime, nullable=True)
    device_info      = db.Column(db.String(200), default="")
    ip_address       = db.Column(db.String(45), default="")
    
    # Relaciones
    activity_logs = db.relationship('ActivityLog', backref='license', lazy='dynamic', 
                                    cascade='all, delete-orphan')
    devices = db.relationship('DeviceHistory', backref='license', lazy='dynamic',
                             cascade='all, delete-orphan')

    def __repr__(self):
        return f"<License {self.key} - {self.plan}>"


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
    status       = db.Column(db.String(20), default="SUCCESS")
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
    ip_addresses = db.Column(db.Text, default="")
    total_uses   = db.Column(db.Integer, default=1)
    is_current   = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f"<DeviceHistory {self.hw_id[:16]}... - {self.total_uses} uses>"