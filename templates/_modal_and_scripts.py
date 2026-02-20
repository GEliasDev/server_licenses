"""
templates/_modal_and_scripts.py - Modal de detalles y toda la lógica JavaScript
"""

MODAL_AND_SCRIPTS = """
<!-- Modal for Details -->
<div id="detailsModal" class="modal">
  <div class="modal-content">
    <span class="close" onclick="closeDetails()">&times;</span>
    <div id="detailsContent">Cargando...</div>
  </div>
</div>

<!-- Toast notification -->
<div id="toast" class="toast"></div>

<script>
  const SECRET = '{{ secret }}';

  // ── Utilidades ──────────────────────────────────────────────

  function showToast(msg, type = 'success') {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = `toast ${type}`;
    t.style.display = 'block';
    setTimeout(() => t.style.display = 'none', 3000);
  }

  // ── Tabs ────────────────────────────────────────────────────

  function showTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById('tab-' + tab).classList.add('active');
    if (tab === 'suspicious') loadSuspicious();
  }

  function loadSuspicious() {
    fetch(`/api/admin/suspicious_activity?secret=${SECRET}`)
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

  // ── Modal de detalles ───────────────────────────────────────

  function showDetails(key, secret, isRevoked, currentUser, currentPlan, hasDevice) {
    document.getElementById('detailsModal').style.display = 'block';
    document.getElementById('detailsContent').innerHTML = 'Cargando detalles...';

    fetch(`/api/admin/license_details/${key}?secret=${secret}`)
      .then(r => r.json())
      .then(data => {
        const lic = data.license;
        document.getElementById('detailsContent').innerHTML =
          buildActionBar(key, secret, isRevoked, hasDevice) +
          buildEditForm(key, lic) +
          buildInfo(lic) +
          buildStats(data.statistics) +
          buildDevices(data.devices) +
          buildActivity(data.recent_activity);
      })
      .catch(() => {
        document.getElementById('detailsContent').innerHTML =
          '<p style="color:#e05252">Error al cargar detalles</p>';
      });
  }

  function buildActionBar(key, secret, isRevoked, hasDevice) {
    const resetBtn = hasDevice
      ? `<a href="/api/admin/reset_ui/${key}?secret=${secret}"
           onclick="return confirm('¿Desvincular dispositivo? El cliente deberá ingresar su clave de nuevo en ~60s.')">
          <button class="btn btn-reset">🖥️ Reset PC</button>
         </a>`
      : '';

    if (isRevoked) {
      return `
        <div class="action-bar">
          <div class="action-bar-label">⚙️ Acciones</div>
          <a href="/api/admin/reactivate_ui/${key}?secret=${secret}"
             onclick="return confirm('¿Reactivar esta licencia?')">
            <button class="btn btn-reactivate">✅ Reactivar</button>
          </a>
          <div class="action-divider"></div>
          <button class="btn btn-delete" onclick="deleteLicense('${key}')">🗑️ Eliminar</button>
        </div>`;
    }

    return `
      <div class="action-bar">
        <div class="action-bar-label">⚙️ Acciones</div>
        <a href="/api/admin/revoke_ui/${key}?secret=${secret}"
           onclick="return confirm('¿Revocar? El cliente perderá acceso en ~60 segundos.')">
          <button class="btn btn-revoke">🚫 Revocar</button>
        </a>
        ${resetBtn}
        <div class="action-divider"></div>
        <button class="btn btn-delete" onclick="deleteLicense('${key}')">🗑️ Eliminar</button>
      </div>`;
  }

  function buildEditForm(key, lic) {
    return `
      <div class="edit-form">
        <b style="color:#00e5a0">✏️ Editar licencia</b><br><br>
        <div class="field">
          <label>Usuario / Email</label>
          <input id="edit-user" type="text" value="${lic.user || ''}" placeholder="nombre o email">
        </div>
        <div class="field">
          <label>Plan</label>
          <select id="edit-plan">
            <option value="monthly"  ${lic.plan === 'monthly'  ? 'selected' : ''}>Mensual (30 días)</option>
            <option value="yearly"   ${lic.plan === 'yearly'   ? 'selected' : ''}>Anual (365 días)</option>
            <option value="lifetime" ${lic.plan === 'lifetime' ? 'selected' : ''}>De por vida</option>
          </select>
        </div>
        <button class="btn btn-save" onclick="saveEdit('${key}')">💾 Guardar cambios</button>
      </div>`;
  }

  function buildInfo(lic) {
    return `
      <h2 style="color:#00e5a0">Detalles: ${lic.key}</h2>
      <div style="background:#0e0f11;padding:16px;margin:16px 0">
        <b>Usuario:</b> ${lic.user || '—'}<br>
        <b>Plan:</b> ${lic.plan}<br>
        <b>Creada:</b> ${lic.created_at.substring(0,16)}<br>
        <b>Primera activación:</b> ${lic.first_activation ? lic.first_activation.substring(0,16) : 'Nunca'}<br>
        <b>Vence:</b> ${lic.expires_at !== 'lifetime' ? lic.expires_at.substring(0,16) : '♾ lifetime'}<br>
        <b>Estado:</b> ${lic.revoked ? '<span class="revoked">REVOCADA</span>' : '<span class="active">ACTIVA</span>'}<br>
        <b>Dispositivo actual:</b> ${lic.current_hw_id || 'Sin activar'}<br>
        <b>Info dispositivo:</b> ${lic.device_info || '—'}<br>
        <b>IP actual:</b> ${lic.ip_address || '—'}
      </div>`;
  }

  function buildStats(statistics) {
    return `
      <h3>📊 Estadísticas</h3>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:12px 0">
        <div class="stat-card">
          <div class="label">Total intentos</div>
          <div class="value" style="font-size:20px">${statistics.total_attempts}</div>
        </div>
        <div class="stat-card">
          <div class="label">Exitosos</div>
          <div class="value" style="font-size:20px;color:#00e5a0">${statistics.successful}</div>
        </div>
        <div class="stat-card">
          <div class="label">Fallidos</div>
          <div class="value" style="font-size:20px;color:#e05252">${statistics.failed}</div>
        </div>
        <div class="stat-card">
          <div class="label">IPs únicas</div>
          <div class="value" style="font-size:20px">${statistics.unique_ips}</div>
        </div>
      </div>`;
  }

  function buildDevices(devices) {
    const rows = devices.map(d => `
      <tr style="${d.is_current ? 'background:#1a2d1a' : ''}">
        <td class="hw">${d.hw_id.substring(0,20)}...</td>
        <td>${d.device_info}</td>
        <td>${d.first_seen.substring(0,16)}</td>
        <td>${d.last_seen.substring(0,16)}</td>
        <td>${d.total_uses}</td>
        <td class="hw">${d.ip_addresses.length} IP${d.ip_addresses.length !== 1 ? 's' : ''}</td>
      </tr>`).join('');

    return `
      <h3>💻 Dispositivos (${devices.length})</h3>
      <table style="font-size:11px">
        <tr><th>HW ID</th><th>Dispositivo</th><th>Primera vez</th><th>Última vez</th><th>Usos</th><th>IPs</th></tr>
        ${rows}
      </table>`;
  }

  function buildActivity(activity) {
    const rows = activity.slice(0, 50).map(a => `
      <tr>
        <td>${a.timestamp.substring(0,16)}</td>
        <td class="${a.status === 'SUCCESS' ? 'success' : 'failed'}">${a.status}</td>
        <td class="hw">${a.hw_id}</td>
        <td class="hw">${a.ip}</td>
        <td>${a.error_detail || a.device_info}</td>
      </tr>`).join('');

    return `
      <h3>📝 Actividad Reciente (últimos 50)</h3>
      <div class="activity-log" style="max-height:300px;overflow-y:auto">
        <table style="font-size:10px">
          <tr><th>Fecha</th><th>Estado</th><th>Dispositivo</th><th>IP</th><th>Info</th></tr>
          ${rows}
        </table>
      </div>`;
  }

  // ── Acciones CRUD ───────────────────────────────────────────

  function saveEdit(key) {
    const user = document.getElementById('edit-user').value.trim();
    const plan = document.getElementById('edit-plan').value;

    fetch('/api/admin/edit_license', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Secret': SECRET },
      body: JSON.stringify({ key, user, plan })
    })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        showToast('Error: ' + data.error, 'error');
      } else {
        showToast(`✓ Licencia ${key} actualizada`, 'success');
        setTimeout(() => location.reload(), 1200);
      }
    })
    .catch(() => showToast('Error de conexión', 'error'));
  }

  function deleteLicense(key) {
    if (!confirm(`¿Eliminar permanentemente la licencia ${key}? Esta acción no se puede deshacer.`)) return;

    fetch('/api/admin/delete_license', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Secret': SECRET },
      body: JSON.stringify({ key })
    })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        showToast('Error: ' + data.error, 'error');
      } else {
        showToast(`🗑️ Licencia ${key} eliminada`, 'success');
        closeDetails();
        setTimeout(() => location.reload(), 1200);
      }
    })
    .catch(() => showToast('Error de conexión', 'error'));
  }

  // ── Modal ───────────────────────────────────────────────────

  function closeDetails() {
    document.getElementById('detailsModal').style.display = 'none';
  }

  window.onclick = function(event) {
    const modal = document.getElementById('detailsModal');
    if (event.target == modal) modal.style.display = 'none';
  }
</script>
"""