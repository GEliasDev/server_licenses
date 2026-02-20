"""
templates/_styles.py - Estilos CSS del panel
"""

STYLES = """
<style>
  body{font-family:monospace;background:#0e0f11;color:#d4d8e2;margin:0;padding:0}
  .container{max-width:1400px;margin:0 auto;padding:32px}
  h1,h2{color:#00e5a0}

  /* ── Stats ── */
  .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:24px 0}
  .stat-card{background:#16181c;padding:16px;border:1px solid #2a2d35;border-radius:4px}
  .stat-card .label{color:#60657a;font-size:11px;text-transform:uppercase}
  .stat-card .value{color:#00e5a0;font-size:28px;font-weight:bold;margin-top:8px}

  /* ── Tabla ── */
  table{border-collapse:collapse;width:100%;margin-top:8px}
  th,td{border:1px solid #2a2d35;padding:8px 12px;text-align:left;vertical-align:middle}
  th{background:#16181c;color:#00e5a0;position:sticky;top:0}
  tr:nth-child(even){background:#16181c}
  tr:hover{background:#1a1d24}
  .clickable-row{cursor:pointer}
  .clickable-row:hover{background:#1e2330 !important;outline:1px solid #00e5a0}

  /* ── Estados ── */
  .revoked{color:#e05252;font-weight:bold}
  .active{color:#00e5a0;font-weight:bold}
  .warning{color:#f0a500;font-weight:bold}

  /* ── Formulario crear ── */
  .form-create{margin-bottom:24px;background:#16181c;padding:16px;border:1px solid #2a2d35}
  input,select{background:#0e0f11;color:#d4d8e2;border:1px solid #2a2d35;padding:6px;font-family:monospace}

  /* ── Botones ── */
  .btn{border:none;padding:5px 10px;font-weight:bold;cursor:pointer;font-family:monospace;font-size:12px;border-radius:3px;text-decoration:none;display:inline-block}
  .btn-create{background:#00e5a0;color:#0e0f11;padding:8px 18px}
  .btn-revoke{background:#e05252;color:#fff;padding:8px 16px;font-size:13px}
  .btn-reactivate{background:#00a870;color:#fff;padding:8px 16px;font-size:13px}
  .btn-reset{background:#f0a500;color:#0e0f11;padding:8px 16px;font-size:13px}
  .btn-delete{background:#6b1c1c;color:#ffaaaa;padding:8px 16px;font-size:13px;border:1px solid #e05252}
  .btn-save{background:#00e5a0;color:#0e0f11;padding:8px 16px;font-size:13px}

  /* ── Tipografía auxiliar ── */
  .key{font-size:13px;letter-spacing:1px;color:#00e5a0;font-weight:bold}
  .hw{font-size:10px;color:#60657a}

  /* ── Indicadores de estado ── */
  .status-indicator{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
  .status-online{background:#00e5a0}
  .status-offline{background:#60657a}
  .status-warning{background:#f0a500}

  /* ── Tabs ── */
  .tabs{display:flex;gap:8px;margin:24px 0;border-bottom:2px solid #2a2d35}
  .tab{padding:12px 24px;background:transparent;color:#60657a;cursor:pointer;border:none;font-family:monospace;font-weight:bold}
  .tab.active{color:#00e5a0;border-bottom:2px solid #00e5a0;margin-bottom:-2px}
  .tab-content{display:none}
  .tab-content.active{display:block}

  /* ── Modal ── */
  .modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:1000}
  .modal-content{background:#16181c;margin:50px auto;padding:24px;max-width:900px;max-height:80vh;overflow-y:auto;border:1px solid #2a2d35}
  .close{float:right;font-size:28px;font-weight:bold;color:#60657a;cursor:pointer}
  .close:hover{color:#00e5a0}

  /* ── Activity log ── */
  .activity-log{font-size:11px}
  .activity-log .success{color:#00e5a0}
  .activity-log .failed{color:#e05252}

  /* ── Action bar ── */
  .action-bar{display:flex;gap:10px;margin:16px 0;padding:16px;background:#0e0f11;border:1px solid #2a2d35;border-radius:4px;align-items:center;flex-wrap:wrap}
  .action-bar-label{color:#60657a;font-size:11px;width:100%;margin-bottom:4px}
  .action-divider{width:1px;background:#2a2d35;height:32px;margin:0 4px}

  /* ── Edit form ── */
  .edit-form{background:#0e0f11;border:1px solid #2a2d35;border-radius:4px;padding:16px;margin:16px 0}
  .edit-form label{color:#60657a;font-size:11px;text-transform:uppercase;display:block;margin-bottom:4px}
  .edit-form .field{margin-bottom:12px}
  .edit-form input,.edit-form select{width:100%;box-sizing:border-box;padding:8px}

  /* ── Toast ── */
  .toast{position:fixed;bottom:24px;right:24px;background:#16181c;border:1px solid #2a2d35;padding:12px 20px;border-radius:4px;font-size:13px;z-index:2000;display:none}
  .toast.success{border-color:#00e5a0;color:#00e5a0}
  .toast.error{border-color:#e05252;color:#e05252}
</style>
"""