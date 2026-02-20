"""
app.py - Aplicación principal Flask
"""

import os
from flask import Flask
from config import config, Config
from models import db


def create_app(config_name='default'):
    """Factory para crear la aplicación Flask"""
    app = Flask(__name__)
    
    # Cargar configuración
    app.config.from_object(config[config_name])
    Config.init_app(app)
    
    # Inicializar base de datos
    db.init_app(app)
    
    # Registrar blueprints
    from routes.validation import bp as validation_bp
    from routes.admin_api import bp as admin_api_bp
    from routes.analytics import bp as analytics_bp
    from routes.admin_panel import bp as admin_panel_bp
    
    app.register_blueprint(validation_bp)
    app.register_blueprint(admin_api_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(admin_panel_bp)
    
    # Crear tablas si no existen
    with app.app_context():
        db.create_all()
    
    return app


# Crear instancia de la app
app = create_app(os.getenv('FLASK_ENV', 'production'))


if __name__ == "__main__":
    from config import Config
    print(f"✓ Panel Avanzado: http://localhost:5000/api/admin/panel?secret={Config.ADMIN_SECRET}")
    app.run(host="0.0.0.0", port=5000, debug=False)