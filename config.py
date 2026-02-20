"""
config.py - Configuración centralizada del servidor
"""

import os

class Config:
    """Configuración base"""
    # Base de datos
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///licenses.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'poolclass': __import__('sqlalchemy.pool', fromlist=['NullPool']).NullPool}
    
    # Seguridad
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "TU_CLAVE_ADMIN_MUY_SEGURA")
    
    # Configuración de licencias
    LICENSE_PREFIX = "VB"
    
    @staticmethod
    def init_app(app):
        """Inicialización de la aplicación"""
        if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
            app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace(
                "postgres://", "postgresql://", 1
            )


class DevelopmentConfig(Config):
    """Configuración de desarrollo"""
    DEBUG = True


class ProductionConfig(Config):
    """Configuración de producción"""
    DEBUG = False


# Configuración por defecto
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}