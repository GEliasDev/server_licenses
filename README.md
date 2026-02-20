# 🚀 Visual Bot - License Server

Sistema avanzado de gestión de licencias con tracking detallado y panel de administración.

## 📁 Estructura del Proyecto

```
license_server/
├── app.py                      # Aplicación principal Flask
├── config.py                   # Configuración centralizada
├── models.py                   # Modelos de base de datos
├── utils.py                    # Funciones de utilidad
├── requirements.txt            # Dependencias Python
├── README.md                   # Esta documentación
├── routes/
│   ├── validation.py          # API pública de validación
│   ├── admin_api.py           # API de administración (JSON)
│   ├── admin_panel.py         # Panel web de administración
│   └── analytics.py           # Endpoints de análisis y estadísticas
└── templates/
    └── panel.py               # Template HTML del panel
```

## 🔧 Instalación

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
# Obligatorio: URL de la base de datos
export DATABASE_URL="postgresql://user:password@localhost/licenses"

# Opcional: Clave de administrador (usa un valor seguro en producción)
export ADMIN_SECRET="tu_clave_super_segura_aqui"

# Opcional: Entorno de desarrollo
export FLASK_ENV="development"
```

### 3. Ejecutar el servidor

```bash
# Modo desarrollo
python app.py

# Modo producción con Gunicorn
gunicorn app:app --bind 0.0.0.0:5000 --workers 4
```

## 📊 Componentes Principales

### **config.py** - Configuración
- Gestión de variables de entorno
- Configuraciones para desarrollo/producción
- Ajuste automático para Heroku/Railway

### **models.py** - Base de Datos
- `License`: Licencias principales
- `ActivityLog`: Registro detallado de cada validación
- `DeviceHistory`: Historial de dispositivos por licencia

### **utils.py** - Utilidades
- Generación de claves de licencia
- Cálculo de fechas de expiración
- Extracción de información de dispositivos
- Logging de actividad
- Autenticación de admin

### **routes/validation.py** - API Pública
- `POST /api/validate`: Validar y vincular licencias

### **routes/admin_api.py** - API de Administración
- `POST /api/admin/create`: Crear licencia
- `POST /api/admin/revoke`: Revocar licencia
- `POST /api/admin/reactivate`: Reactivar licencia
- `POST /api/admin/reset_device`: Desvincular dispositivo
- `POST /api/admin/extend`: Extender expiración
- `GET /api/admin/list`: Listar todas las licencias

### **routes/analytics.py** - Analytics
- `GET /api/admin/license_details/<key>`: Detalles completos de una licencia
- `GET /api/admin/suspicious_activity`: Detectar actividad sospechosa
- `GET /api/admin/activity_summary`: Resumen de actividad general

### **routes/admin_panel.py** - Panel Web
- `GET /api/admin/panel`: Panel de administración HTML interactivo
- Acciones UI: revoke_ui, reactivate_ui, reset_ui

## 🔐 Seguridad

- Todas las rutas de administración requieren autenticación con `ADMIN_SECRET`
- Autenticación vía header `X-Admin-Secret` o query param `?secret=`
- Sin secret válido → 401 Unauthorized

## 📝 Uso de la API

### Validar Licencia (Cliente)

```python
import requests

response = requests.post('https://tu-servidor.com/api/validate', json={
    'key': 'VB-XXXX-XXXX-XXXX-XXXX',
    'hw_id': 'hardware_id_unico',
    'app_version': '1.0.0'
})

if response.status_code == 200:
    data = response.json()
    print(f"Válida! Plan: {data['plan']}, Expira: {data['expires_at']}")
else:
    error = response.json()['error']
    print(f"Error: {error}")  # INVALID, REVOKED, EXPIRED, WRONG_DEVICE
```

### Crear Licencia (Admin)

```python
import requests

response = requests.post(
    'https://tu-servidor.com/api/admin/create',
    headers={'X-Admin-Secret': 'tu_admin_secret'},
    json={
        'plan': 'yearly',
        'user': 'cliente@email.com'
    }
)

data = response.json()
print(f"Nueva licencia: {data['key']}")
```

### Obtener Detalles de Licencia

```python
import requests

response = requests.get(
    'https://tu-servidor.com/api/admin/license_details/VB-XXXX-XXXX-XXXX-XXXX',
    params={'secret': 'tu_admin_secret'}
)

data = response.json()
print(f"Activaciones: {data['statistics']['successful']}")
print(f"Dispositivos: {len(data['devices'])}")
```

## 🌐 Panel de Administración

Accede al panel web:
```
https://tu-servidor.com/api/admin/panel?secret=TU_ADMIN_SECRET
```

Características:
- 📊 Dashboard con estadísticas en tiempo real
- 📝 Crear licencias nuevas
- 🔍 Ver detalles completos de cada licencia
- 🚨 Detectar actividad sospechosa
- ⚙️ Gestionar licencias (revocar, reactivar, reset)
- 📈 Analytics de uso y dispositivos

## 🚀 Deployment

### Heroku

```bash
# Crear app
heroku create tu-app-licencias

# Añadir PostgreSQL
heroku addons:create heroku-postgresql:mini

# Configurar admin secret
heroku config:set ADMIN_SECRET="tu_clave_super_segura"

# Deploy
git push heroku main
```

### Railway

1. Conecta tu repositorio GitHub
2. Añade PostgreSQL desde Variables → New Variable
3. Configura `ADMIN_SECRET` en Variables
4. Railway detectará y desplegará automáticamente

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "4"]
```

## 🔄 Migraciones

Si necesitas modificar la estructura de la base de datos:

```python
# En el contexto de la app
from app import app, db

with app.app_context():
    db.create_all()  # Crear tablas nuevas
    # o usar Flask-Migrate para migraciones más complejas
```

## 📦 Ventajas de Esta Estructura

✅ **Modular**: Cada componente en su archivo separado
✅ **Escalable**: Fácil añadir nuevas rutas/funcionalidades
✅ **Mantenible**: Código organizado y fácil de entender
✅ **Testeable**: Cada módulo se puede testear independientemente
✅ **Profesional**: Sigue best practices de Flask
✅ **Optimizado**: Mejor rendimiento con blueprints separados

## 🆘 Troubleshooting

**Error: "No module named 'routes'"**
- Asegúrate de crear un archivo `routes/__init__.py` vacío

**Error de conexión a PostgreSQL**
- Verifica que `DATABASE_URL` esté correctamente configurada
- Formato: `postgresql://user:pass@host:port/dbname`

**401 Unauthorized en admin**
- Verifica que `ADMIN_SECRET` esté configurado
- Usa el header `X-Admin-Secret` o param `?secret=`

## 📄 Licencia

Uso interno / comercial según necesidades del proyecto.