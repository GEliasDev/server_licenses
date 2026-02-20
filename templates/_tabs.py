"""
templates/_tabs.py - Tabs de navegación y tablas de licencias
"""

TABS = """
<!-- Tabs -->
<div class="tabs">
  <button class="tab active" onclick="showTab('all')">Todas las licencias</button>
  <button class="tab" onclick="showTab('active')">Activas</button>
  <button class="tab" onclick="showTab('suspicious')">Actividad Sospechosa</button>
</div>

<!-- Tab: All Licenses -->
<div class="tab-content active" id="tab-all">
  <h2>Licencias ({{ licenses|length }}) <small style="color:#60657a;font-size:12px;font-weight:normal">— Click en una fila para ver detalles</small></h2>
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
    </tr>
    {% for l in licenses %}
    <tr class="clickable-row"
        onclick="showDetails('{{ l.key }}', '{{ secret }}', {{ 'true' if l.revoked else 'false' }}, '{{ l.user or '' }}', '{{ l.plan }}', {{ 'true' if l.hw_id else 'false' }})"
        title="Click para ver detalles de {{ l.key }}">
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
"""