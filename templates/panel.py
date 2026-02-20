"""
templates/panel.py - Template HTML del panel de administración
"""

PANEL_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Visual Bot — Licencias Advanced</title>
  <meta charset="utf-8">
  <style>
    body{font-family:monospace;background:#0e0f11;color:#d4d8e2;margin:0;padding:0}
    .container{max-width:1400px;margin:0 auto;padding:32px}
    h1,h2{color:#00e5a0}
    .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:24px 0}
    .stat-card{background:#16181c;padding:16px;border:1px solid #2a2d35;border-radius:4px}
    .stat-card .label{color:#60657a;font-size:11px;text-transform:uppercase}
    .stat-card .value{color:#00e5a0;font-size:28px;font-weight:bold;margin-top:8px}
    table{border-collapse:collapse;width:100%;margin-top:8px}
    th,td{border:1px solid #2a2d35;padding:8px 12px;text-align:left;vertical-align:middle}
    th{background:#16181c;color:#00e5a0;position:sticky;top:0}
    tr:nth-child(even){background:#16181c}
    tr:hover{background:#1a1d24}
    .revoked{color:#e05252;font-weight:bold}
    .active{color:#00e5a0;font-weight:bold}
    .warning{color:#f0a500;font-weight:bold}
    .form-create{margin-bottom:24px;background:#16181c;padding:16px;border:1px solid #2a2d35}
    input,select{background:#0e0f11;color:#d4d8e2;border:1px solid #2a2d35;padding:6px;font-family:monospace}
    .btn{border:none;padding:5px 10px;font-weight:bold;cursor:pointer;font-family:monospace;font-size:12px;border-radius:3px;text-decoration:none;display:inline-block}
    .btn-create{background:#00e5a0;color:#0e0f11;padding:8px 18px}
    .btn-revoke{background:#e05252;color:#fff}
    .btn-reactivate{background:#00a870;color:#fff}
    .btn-reset{background:#f0a500;color:#0e0f11}
    .btn-details{background:#3a7bd5;color:#fff;font-size:11px}
    .key{font-size:13px;letter-spacing:1px;color:#00e5a0;font-weight:bold}
    .hw{font-size:10px;color:#60657a}
    .status-indicator{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
    .status-online{background:#00e5a0}
    .status-offline{background:#60657a}
    .status-warning{background:#f0a500}
    .tabs{display:flex;gap:8px;margin:24px 0;border-bottom:2px solid #2a2d35}
    .tab{padding:12px 24px;background:transparent;color:#60657a;cursor:pointer;border:none;font-family:monospace;font-weight:bold}
    .tab.active{color:#00e5a0;border-bottom:2px solid #00e5a0;margin-bottom:-2px}
    .tab-content{display:none}
    .tab-content.active{display:block}
    .device-badge{display:inline-block;background:#2a2d35;padding:4px 8px;border-radius:3px;font-size:10px;margin:2px}
    .modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:1000}
    .modal-content{background:#16181c;margin:50px auto;padding:24px;max-width:900px;max-height:80vh;overflow-y:auto;border:1px solid #2a2d35}
    .close{float:right;font-size:28px;font-weight:bold;color:#60657a;cursor:pointer}
    .close:hover{color:#00e5a0}
    .activity-log{font-size:11px}
    .activity-log .success{color:#00e5a0}
    .activity-log .failed{color:#e05252}
  </style>
</head>
<body>
  <div class="container">
    <h1>🚀 Visual Bot — Panel Avanzado</h1>
    
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

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab active" onclick="showTab('all')">Todas las licencias</button>
      <button class="tab" onclick="showTab('active')">Activas</button>
      <button class="tab" onclick="showTab('suspicious')">Actividad Sospechosa</button>
    </div>

    <!-- Tab: All Licenses -->
    <div class="tab-content active" id="tab-all">
      <h2>Licencias ({{ licenses|length }})</h2>
      <table>
        <tr>
          <th>Estado</th>
          <th>Clave</th>
          <th>Plan</th>
          <th>Usuario</th>
          <th>Vence</th>
          <th>Dispositivo Actual</th>
          <th>Primera/Última Actividad</th>
          <th>Usos</th>
          <th>Acciones</th>
        </tr>
        {% for l in licenses %}
        <tr>
          <td>
            {% if l.last_seen and l.last_seen != "nunca" %}
              {% set hours_ago = ((now - l.last_seen_dt).total_seconds() / 3600) | int %}
              {% if hours_ago < 1 %}
                <span class="status-indicator status-online"></span>
              {% elif hours_ago < 24 %}
                <span class="status-indicator status-warning"></span>
              {% else %}
                <span class="status-indicator status-offline"></span>
              {% endif %}
            {% else %}
              <span class="status-indicator status-offline"></span>
            {% endif %}
          </td>
          <td class="key">{{ l.key }}</td>
          <td>{{ l.plan }}</td>
          <td>{{ l.user or "—" }}</td>
          <td>{{ l.expires_at[:10] if l.expires_at and l.expires_at != "lifetime" else "♾ lifetime" }}</td>
          <td class="hw">
            {{ (l.hw_id or "sin activar")[:16] }}{% if l.hw_id and l.hw_id|length > 16 %}...{% endif %}
            {% if l.device_info %}<br><small style="color:#3a3f50">{{ l.device_info[:30] }}</small>{% endif %}
          </td>
          <td style="font-size:11px">
            {% if l.first_activation and l.first_activation != "nunca" %}
              <b>1ª:</b> {{ l.first_activation[:10] }}<br>
            {% endif %}
            <b>Ult:</b> {{ l.last_seen[:16] if l.last_seen and l.last_seen != "nunca" else "nunca" }}
          </td>
          <td style="text-align:center">{{ l.activations }}</td>
          <td>
            <a href="#" onclick="showDetails('{{ l.key }}', '{{ secret }}'); return false" class="btn btn-details">📊 Detalles</a>
            <br><br>
            {% if l.revoked %}
              <a href="/api/admin/reactivate_ui/{{ l.key }}?secret={{ secret }}"
                 onclick="return confirm('¿Reactivar esta licencia?')">
                <button class="btn btn-reactivate">Reactivar</button>
              </a>
            {% else %}
              <a href="/api/admin/revoke_ui/{{ l.key }}?secret={{ secret }}"
                 onclick="return confirm('¿Revocar? El cliente perderá acceso en ~60 segundos.')">
                <button class="btn btn-revoke">Revocar</button>
              </a>
              <br><br>
              <a href="/api/admin/reset_ui/{{ l.key }}?secret={{ secret }}"
                 onclick="return confirm('¿Desvincular dispositivo? El cliente deberá ingresar su clave de nuevo en ~60s.')">
                <button class="btn btn-reset">Reset PC</button>
              </a>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </table>
    </div>

    <!-- Tab: Active -->
    <div class="tab-content" id="tab-active">
      <h2>Licencias Activas (últimas 24h)</h2>
      <table>
        <tr>
          <th>Clave</th>
          <th>Usuario</th>
          <th>Plan</th>
          <th>Última Actividad</th>
          <th>IP</th>
        </tr>
        {% for l in licenses if l.last_seen_dt and (now - l.last_seen_dt).total_seconds() < 86400 %}
        <tr>
          <td class="key">{{ l.key }}</td>
          <td>{{ l.user or "—" }}</td>
          <td>{{ l.plan }}</td>
          <td>{{ l.last_seen[:16] }}</td>
          <td class="hw">{{ l.ip_address or "—" }}</td>
        </tr>
        {% endfor %}
      </table>
    </div>

    <!-- Tab: Suspicious -->
    <div class="tab-content" id="tab-suspicious">
      <h2>Actividad Sospechosa</h2>
      <p style="color:#60657a">Licencias con múltiples dispositivos o intentos fallidos recientes</p>
      <div id="suspicious-content">Cargando...</div>
    </div>

    <p style="color:#3a3f50;margin-top:24px;font-size:11px">
      🟢 Online (< 1h) &nbsp; 🟡 Reciente (< 24h) &nbsp; ⚫ Offline (> 24h)
      <br>
      Los clientes re-validan cada 60 segundos. Una revocación tarda máximo 60s en aplicarse.
    </p>
  </div>

  <!-- Modal for Details -->
  <div id="detailsModal" class="modal">
    <div class="modal-content">
      <span class="close" onclick="closeDetails()">&times;</span>
      <div id="detailsContent">Cargando...</div>
    </div>
  </div>

  <script>
    function showTab(tab) {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById('tab-' + tab).classList.add('active');
      
      if (tab === 'suspicious') {
        loadSuspicious();
      }
    }

    function loadSuspicious() {
      fetch('/api/admin/suspicious_activity?secret={{ secret }}')
        .then(r => r.json())
        .then(data => {
          const content = document.getElementById('suspicious-content');
          if (data.suspicious_licenses.length === 0) {
            content.innerHTML = '<p style="color:#00e5a0">✓ No se detectó actividad sospechosa</p>';
            return;
          }
          
          let html = '<table><tr><th>Clave</th><th>Usuario</th><th>Motivo</th><th>Severidad</th></tr>';
          data.suspicious_licenses.forEach(s => {
            const color = s.severity === 'HIGH' ? '#e05252' : s.severity === 'MEDIUM' ? '#f0a500' : '#60657a';
            html += `<tr>
              <td class="key">${s.key}</td>
              <td>${s.user || '—'}</td>
              <td>${s.reason}</td>
              <td style="color:${color};font-weight:bold">${s.severity}</td>
            </tr>`;
          });
          html += '</table>';
          content.innerHTML = html;
        });
    }

    function showDetails(key, secret) {
      document.getElementById('detailsModal').style.display = 'block';
      document.getElementById('detailsContent').innerHTML = 'Cargando detalles...';
      
      fetch(`/api/admin/license_details/${key}?secret=${secret}`)
        .then(r => r.json())
        .then(data => {
          let html = `
            <h2 style="color:#00e5a0">Detalles: ${data.license.key}</h2>
            <div style="background:#0e0f11;padding:16px;margin:16px 0">
              <b>Usuario:</b> ${data.license.user || '—'}<br>
              <b>Plan:</b> ${data.license.plan}<br>
              <b>Creada:</b> ${data.license.created_at.substring(0,16)}<br>
              <b>Primera activación:</b> ${data.license.first_activation ? data.license.first_activation.substring(0,16) : 'Nunca'}<br>
              <b>Vence:</b> ${data.license.expires_at !== 'lifetime' ? data.license.expires_at.substring(0,16) : '♾ lifetime'}<br>
              <b>Estado:</b> ${data.license.revoked ? '<span class="revoked">REVOCADA</span>' : '<span class="active">ACTIVA</span>'}<br>
              <b>Dispositivo actual:</b> ${data.license.current_hw_id || 'Sin activar'}<br>
              <b>Info dispositivo:</b> ${data.license.device_info || '—'}<br>
              <b>IP actual:</b> ${data.license.ip_address || '—'}
            </div>
            
            <h3>📊 Estadísticas</h3>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:12px 0">
              <div class="stat-card">
                <div class="label">Total intentos</div>
                <div class="value" style="font-size:20px">${data.statistics.total_attempts}</div>
              </div>
              <div class="stat-card">
                <div class="label">Exitosos</div>
                <div class="value" style="font-size:20px;color:#00e5a0">${data.statistics.successful}</div>
              </div>
              <div class="stat-card">
                <div class="label">Fallidos</div>
                <div class="value" style="font-size:20px;color:#e05252">${data.statistics.failed}</div>
              </div>
              <div class="stat-card">
                <div class="label">IPs únicas</div>
                <div class="value" style="font-size:20px">${data.statistics.unique_ips}</div>
              </div>
            </div>
            
            <h3>💻 Dispositivos (${data.devices.length})</h3>
            <table style="font-size:11px">
              <tr><th>HW ID</th><th>Dispositivo</th><th>Primera vez</th><th>Última vez</th><th>Usos</th><th>IPs</th></tr>
              ${data.devices.map(d => `
                <tr style="${d.is_current ? 'background:#1a2d1a' : ''}">
                  <td class="hw">${d.hw_id.substring(0,20)}...</td>
                  <td>${d.device_info}</td>
                  <td>${d.first_seen.substring(0,16)}</td>
                  <td>${d.last_seen.substring(0,16)}</td>
                  <td>${d.total_uses}</td>
                  <td class="hw">${d.ip_addresses.length} IP${d.ip_addresses.length !== 1 ? 's' : ''}</td>
                </tr>
              `).join('')}
            </table>
            
            <h3>📝 Actividad Reciente (últimos 50)</h3>
            <div class="activity-log" style="max-height:300px;overflow-y:auto">
              <table style="font-size:10px">
                <tr><th>Fecha</th><th>Estado</th><th>Dispositivo</th><th>IP</th><th>Info</th></tr>
                ${data.recent_activity.slice(0,50).map(a => `
                  <tr>
                    <td>${a.timestamp.substring(0,16)}</td>
                    <td class="${a.status === 'SUCCESS' ? 'success' : 'failed'}">${a.status}</td>
                    <td class="hw">${a.hw_id}</td>
                    <td class="hw">${a.ip}</td>
                    <td>${a.error_detail || a.device_info}</td>
                  </tr>
                `).join('')}
              </table>
            </div>
          `;
          document.getElementById('detailsContent').innerHTML = html;
        })
        .catch(err => {
          document.getElementById('detailsContent').innerHTML = 
            '<p style="color:#e05252">Error al cargar detalles</p>';
        });
    }

    function closeDetails() {
      document.getElementById('detailsModal').style.display = 'none';
    }

    window.onclick = function(event) {
      const modal = document.getElementById('detailsModal');
      if (event.target == modal) {
        modal.style.display = 'none';
      }
    }
  </script>
</body>
</html>
"""