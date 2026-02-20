"""
templates/panel.py - Template principal del panel de administración.

Ensambla las secciones desde los módulos separados:
  _styles.py            → CSS
  _dashboard.py         → Stats cards + formulario crear
  _tabs.py              → Tabs + tablas de licencias
  _modal_and_scripts.py → Modal de detalles + JavaScript
"""

from templates._styles import STYLES
from templates._dashboard import DASHBOARD
from templates._tabs import TABS
from templates._modal_and_scripts import MODAL_AND_SCRIPTS

PANEL_HTML = f"""
<!DOCTYPE html>
<html>
<head>
  <title>Visual Bot — Licencias Advanced</title>
  <meta charset="utf-8">
  {STYLES}
</head>
<body>
  <div class="container">
    <h1>🚀 Visual Bot — Panel Avanzado</h1>
    {DASHBOARD}
    {TABS}
  </div>

  {MODAL_AND_SCRIPTS}
</body>
</html>
"""