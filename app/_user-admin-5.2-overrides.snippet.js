/* =====================================================================
 * 5.2 — Per-user permission overrides (drill-down tree)
 * ---------------------------------------------------------------------
 * READY TO INTEGRATE — not yet injected into ritual-studio-ops-v2.html.
 * The DB side is LIVE and tested: admin_set_user_permission(p_user_id,
 * p_permission_code, p_state) with p_state in ('inherit','granted','denied'),
 * the user_permission_overrides table, and v_user_permissions_resolved which
 * layers overrides on top of role grants. This snippet provides the UI that
 * drives that RPC.
 *
 * Depends on helpers already present in v2 after the 5.1 patch:
 *   dbGet(path), rpc(fn,args), hasPerm(code), esc(s), showToast(),
 *   showLoading()/hideLoading(), currentUserProfile.
 *
 * INTEGRATION
 *   1. Paste these functions into the main <script> of ritual-studio-ops-v2.html
 *      (near the other USER MANAGEMENT functions, after loadUserProfiles).
 *   2. In loadUserProfiles(), add an Edit button to each row's actions cell:
 *        <button class="btn btn-secondary" style="font-size:10px;padding:4px 10px;"
 *          onclick="openUserPermissions('${u.user_id}','${esc(u.email)}','${u.role}')">Edit</button>
 *   3. Add an empty modal container once in the page body:
 *        <div id="permModal" class="modal" style="display:none;"></div>
 *   4. Browser-test as developer AND as an administrator before deploy.
 * ===================================================================== */

// In-memory cache of the permission catalogue (code, parent_code, category, description)
let _permCatalogue = null;

async function _loadPermCatalogue() {
  if (_permCatalogue) return _permCatalogue;
  const rows = await dbGet('permissions?select=code,parent_code,category,description&order=category.asc,code.asc');
  _permCatalogue = rows || [];
  return _permCatalogue;
}

/* Open the per-user permission editor. */
async function openUserPermissions(userId, email, role) {
  if (!hasPerm('admin.users.manage')) { showToast('You do not have permission to manage users.', 'error'); return; }
  showLoading('Loading permissions…');
  try {
    const [catalogue, effRows, ovRows] = await Promise.all([
      _loadPermCatalogue(),
      dbGet(`v_user_permissions_resolved?user_id=eq.${userId}&select=permission_code`),
      dbGet(`user_permission_overrides?user_id=eq.${userId}&select=permission_code,granted`)
    ]);
    const effective = new Set((effRows || []).map(r => r.permission_code));
    const overrides = {};
    (ovRows || []).forEach(o => { overrides[o.permission_code] = o.granted ? 'granted' : 'denied'; });
    _renderPermModal(userId, email, role, catalogue, effective, overrides);
  } catch (e) {
    showToast('Error loading permissions: ' + e.message, 'error');
  } finally {
    hideLoading();
  }
}

/* Render the three-state tree, grouped by parent_code. */
function _renderPermModal(userId, email, role, catalogue, effective, overrides) {
  const isSelf = currentUserProfile && currentUserProfile.user_id === userId;
  const parents = catalogue.filter(p => !p.parent_code);
  const childrenOf = code => catalogue.filter(c => c.parent_code === code);

  const stateFor = code => overrides[code] || 'inherit'; // inherit | granted | denied
  const radios = (code) => {
    // Self-protection: cannot deny your own admin/superuser permissions.
    const lockDeny = isSelf && (code === 'admin.users.manage' || code === 'system.admin');
    const cur = stateFor(code);
    const opt = (val, label) => `
      <label style="margin-right:10px;font-size:11px;${val==='denied'&&lockDeny?'opacity:0.4;':''}">
        <input type="radio" name="perm_${code}" value="${val}" ${cur===val?'checked':''}
          ${val==='denied'&&lockDeny?'disabled':''}> ${label}</label>`;
    return opt('inherit','Inherit') + opt('granted','Grant') + opt('denied','Deny');
  };

  const rows = parents.map(p => {
    const kids = childrenOf(p.code);
    const kidRows = kids.map(k => `
      <tr>
        <td style="padding-left:24px;font-size:12px;">${esc(k.code)}<div style="font-size:10px;color:var(--text-muted);">${esc(k.description||'')}</div></td>
        <td style="text-align:right;white-space:nowrap;">${radios(k.code)}</td>
        <td style="text-align:center;font-size:10px;color:${effective.has(k.code)?'#4A7A4A':'var(--text-muted)'};">${effective.has(k.code)?'effective':'—'}</td>
      </tr>`).join('');
    const parentRow = `
      <tr style="background:var(--cream);">
        <td style="font-weight:600;font-size:12px;">${esc(p.code)}<div style="font-size:10px;color:var(--text-muted);">${esc(p.description||'')}</div></td>
        <td style="text-align:right;white-space:nowrap;">${radios(p.code)}</td>
        <td style="text-align:center;font-size:10px;color:${effective.has(p.code)?'#4A7A4A':'var(--text-muted)'};">${effective.has(p.code)?'effective':'—'}</td>
      </tr>`;
    return parentRow + kidRows;
  }).join('');

  const modal = document.getElementById('permModal');
  modal.innerHTML = `
    <div class="modal-content" style="max-width:720px;max-height:80vh;overflow:auto;">
      <h2 style="font-family:'Cormorant Garamond',serif;font-weight:400;">Permissions — ${esc(email)} <span class="role-badge role-${role}">${esc(role)}</span></h2>
      <p style="font-size:11px;color:var(--text-muted);">Inherit = use the role default. Grant/Deny override the role for this user only. Developer holds <code>system.admin</code> (wildcard) and resolves to everything.</p>
      <table class="data-table" style="width:100%;">
        <thead><tr><th>Permission</th><th style="text-align:right;">Override</th><th style="text-align:center;">Now</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div style="margin-top:16px;text-align:right;">
        <button class="btn btn-secondary" onclick="document.getElementById('permModal').style.display='none';">Cancel</button>
        <button class="btn btn-secondary" onclick="resetUserPermissions('${userId}','${esc(email)}','${role}')">Reset to role defaults</button>
        <button class="btn btn-primary" onclick="saveUserPermissions('${userId}','${esc(email)}','${role}')">Save</button>
      </div>
    </div>`;
  modal.style.display = 'flex';
}

/* Save the diff: one admin_set_user_permission call per permission whose state changed. */
async function saveUserPermissions(userId, email, role) {
  showLoading('Saving…');
  try {
    const catalogue = await _loadPermCatalogue();
    for (const p of catalogue) {
      const sel = document.querySelector(`input[name="perm_${p.code}"]:checked`);
      if (!sel) continue;
      await rpc('admin_set_user_permission', { p_user_id: userId, p_permission_code: p.code, p_state: sel.value });
    }
    showToast('Permissions saved for ' + email + '.');
    document.getElementById('permModal').style.display = 'none';
  } catch (e) {
    showToast('Error saving permissions: ' + e.message, 'error');
  } finally {
    hideLoading();
  }
}

/* Reset: set every permission back to inherit (deletes all override rows). */
async function resetUserPermissions(userId, email, role) {
  if (!confirm(`Reset ${email} to pure role defaults? This removes all per-user overrides.`)) return;
  showLoading('Resetting…');
  try {
    const ovRows = await dbGet(`user_permission_overrides?user_id=eq.${userId}&select=permission_code`);
    for (const o of (ovRows || [])) {
      await rpc('admin_set_user_permission', { p_user_id: userId, p_permission_code: o.permission_code, p_state: 'inherit' });
    }
    showToast('Reset to role defaults for ' + email + '.');
    await openUserPermissions(userId, email, role); // reopen refreshed
  } catch (e) {
    showToast('Error resetting: ' + e.message, 'error');
  } finally {
    hideLoading();
  }
}
