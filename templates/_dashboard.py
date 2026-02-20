"""
templates/_dashboard.py - Stats cards y formulario de creación
"""

DASHBOARD = """
<!-- Stats Dashboard -->
<div class="stats-grid">
  <div class="stat-card">
    <div class="label">Total Licencias</div>
    <div class="value">{{ stats.total }}</div>
  </div>
  <div class="stat-card">
    <div class="label">Activas (24h)</div>
    <div class="value" style="color:#00e5a0">{{ stats.active_24h }}</div>
  </div>
  <div class="stat-card">
    <div class="label">Inactivas (7d+)</div>
    <div class="value" style="color:#f0a500">{{ stats.inactive }}</div>
  </div>
  <div class="stat-card">
    <div class="label">Revocadas</div>
    <div class="value" style="color:#e05252">{{ stats.revoked }}</div>
  </div>
</div>

<!-- Create Form -->
<div class="form-create">
  <b>Crear nueva licencia</b><br><br>
  <form method="POST" action="/api/admin/create?secret={{ secret }}">
    Usuario/Email: <input name="user" placeholder="nombre o email" size="22">
    &nbsp; Plan:
    <select name="plan">
      <option value="monthly">Mensual (30 días)</option>
      <option value="yearly">Anual (365 días)</option>
      <option value="lifetime">De por vida</option>
    </select>
    &nbsp;
    <button type="submit" class="btn btn-create">CREAR</button>
  </form>
</div>
"""