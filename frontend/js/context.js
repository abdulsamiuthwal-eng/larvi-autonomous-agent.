/**
 * Larvi — Client-Side Context State Manager
 * Manages session ID, working memory display, and auth state.
 */

class LarviContext {
  constructor() {
    this.sessionId = null;
    this.workingMemory = {};
    this.authState = { authenticated: false };
    this.messageCount = 0;
  }

  /**
   * Set or restore session ID.
   */
  initSession() {
    this.sessionId = sessionStorage.getItem('larvi_session_id') || null;
    return this.sessionId;
  }

  /**
   * Store new session ID from API response.
   */
  setSessionId(id) {
    this.sessionId = id;
    sessionStorage.setItem('larvi_session_id', id);
  }

  /**
   * Clear session (new conversation).
   */
  clearSession() {
    this.sessionId = null;
    this.workingMemory = {};
    this.messageCount = 0;
    sessionStorage.removeItem('larvi_session_id');
    this.updateWorkingMemoryUI({});
  }

  /**
   * Update working memory and refresh the UI panel.
   */
  updateWorkingMemory(memory) {
    this.workingMemory = memory || {};
    this.updateWorkingMemoryUI(this.workingMemory);
  }

  /**
   * Render working memory into the right sidebar panel.
   */
  updateWorkingMemoryUI(memory) {
    const panel = document.getElementById('working-memory-content');
    if (!panel) return;

    const keys = Object.entries(memory).filter(([k, v]) =>
      v !== null && v !== undefined && k !== 'pending_action'
    );

    if (keys.length === 0) {
      panel.innerHTML = `<p class="memory-empty">No active context yet.</p>`;
      return;
    }

    const LABELS = {
      active_person: 'Person',
      last_email_id: 'Email ID',
      last_email_subject: 'Email Subject',
      last_email_from: 'Email From',
      last_event_id: 'Event ID',
      last_event_title: 'Event',
      last_event_date: 'Date',
      last_event_start: 'Start',
      last_event_end: 'End',
    };

    panel.innerHTML = keys.map(([k, v]) => `
      <div class="memory-row">
        <span class="memory-key">${LABELS[k] || k.replace(/_/g, ' ')}</span>
        <span class="memory-value">${String(v)}</span>
      </div>
    `).join('');
  }

  /**
   * Update auth state and refresh UI indicators.
   */
  setAuthState(authData) {
    this.authState = authData;
    this.updateAuthUI(authData);
  }

  /**
   * Update all auth-related UI elements.
   */
  updateAuthUI(authData) {
    const authPrompt = document.getElementById('auth-prompt');
    const statusPill = document.getElementById('system-status-pill');

    // Auth prompt banner
    if (authPrompt) {
      if (!authData.authenticated) {
        authPrompt.classList.remove('hidden');
      } else {
        authPrompt.classList.add('hidden');
      }
    }

    // System status pill
    if (statusPill) {
      if (authData.authenticated) {
        statusPill.style.display = 'flex';
        statusPill.innerHTML = `
          <span class="status-dot active"></span>
          All Systems Active
        `;
      } else {
        statusPill.innerHTML = `
          <span class="status-dot error"></span>
          Not Connected
        `;
        statusPill.style.borderColor = 'var(--color-rose-border)';
        statusPill.style.background = 'var(--color-rose-pale)';
        statusPill.style.color = 'var(--color-rose)';
      }
    }

    // Agent status dots in left sidebar
    const emailDot = document.getElementById('email-agent-dot');
    const calDot = document.getElementById('cal-agent-dot');
    const emailSub = document.getElementById('email-agent-sub');
    const calSub = document.getElementById('cal-agent-sub');

    if (authData.authenticated) {
      if (emailDot) emailDot.className = 'status-dot active';
      if (calDot)   calDot.className   = 'status-dot active';
      if (emailSub) emailSub.textContent = 'Gmail OAuth • Connected';
      if (calSub)   calSub.textContent   = 'Google Calendar • Connected';
    } else {
      if (emailDot) emailDot.className = 'status-dot error';
      if (calDot)   calDot.className   = 'status-dot error';
      if (emailSub) emailSub.textContent = 'Not authenticated';
      if (calSub)   calSub.textContent   = 'Not authenticated';
    }

    // ── Sidebar User Profile Strip & View Updates ────────────────
    const userNameEl = document.getElementById('user-name-display');
    const userEmailEl = document.getElementById('user-email-display');
    const userAvatarEl = document.getElementById('user-avatar');
    const userPicEl = document.getElementById('user-profile-pic');
    const upStatusDot = document.getElementById('up-status-dot');

    // Profile View Elements
    const heroName = document.getElementById('profile-name-display');
    const heroEmail = document.getElementById('profile-email-hero');
    const heroAvatarStatus = document.getElementById('profile-avatar-status');
    const heroPicLarge = document.getElementById('profile-pic-large');
    const heroInitialLarge = document.getElementById('profile-initial-large');
    const pfName = document.getElementById('pf-name');
    const pfEmail = document.getElementById('pf-email');
    const pfGmailStatus = document.getElementById('pf-gmail-status');
    const pfCalStatus = document.getElementById('pf-cal-status');
    const pfTokenStatus = document.getElementById('pf-token-status');

    if (authData.authenticated) {
      const email = authData.email || 'user@gmail.com';
      const name = authData.name || email.split('@')[0];
      const initial = (name || email)[0].toUpperCase();

      // Sidebar Profile Strip
      if (userNameEl) userNameEl.textContent = name;
      if (userEmailEl) userEmailEl.textContent = email;
      if (upStatusDot) {
        upStatusDot.className = 'up-status-dot online';
      }

      if (authData.picture && userPicEl) {
        userPicEl.src = authData.picture;
        userPicEl.style.display = 'block';
        if (userAvatarEl) userAvatarEl.style.display = 'none';
      } else if (userAvatarEl) {
        userAvatarEl.textContent = initial;
        userAvatarEl.style.display = 'flex';
        if (userPicEl) userPicEl.style.display = 'none';
      }

      // Profile Page View
      if (heroName) heroName.textContent = name;
      if (heroEmail) heroEmail.textContent = email;
      if (heroAvatarStatus) {
        heroAvatarStatus.textContent = '● Online & Connected';
        heroAvatarStatus.className = 'profile-avatar-status online';
      }

      if (authData.picture && heroPicLarge) {
        heroPicLarge.src = authData.picture;
        heroPicLarge.style.display = 'block';
        if (heroInitialLarge) heroInitialLarge.style.display = 'none';
      } else if (heroInitialLarge) {
        heroInitialLarge.textContent = initial;
        heroInitialLarge.style.display = 'flex';
        if (heroPicLarge) heroPicLarge.style.display = 'none';
      }

      if (pfName) pfName.textContent = name;
      if (pfEmail) pfEmail.textContent = email;
      if (pfGmailStatus) pfGmailStatus.innerHTML = '<span class="status-chip connected">Active & Linked</span>';
      if (pfCalStatus) pfCalStatus.innerHTML = '<span class="status-chip connected">Active & Linked</span>';
      if (pfTokenStatus) pfTokenStatus.innerHTML = '<span class="status-chip connected">Valid & Refreshing</span>';

    } else {
      // Sidebar Profile Strip (Offline)
      if (userNameEl) userNameEl.textContent = 'Larvi User';
      if (userEmailEl) userEmailEl.textContent = 'Not connected';
      if (upStatusDot) upStatusDot.className = 'up-status-dot offline';
      if (userAvatarEl) {
        userAvatarEl.textContent = 'U';
        userAvatarEl.style.display = 'flex';
      }
      if (userPicEl) userPicEl.style.display = 'none';

      // Profile Page View (Offline)
      if (heroName) heroName.textContent = 'Larvi User';
      if (heroEmail) heroEmail.textContent = 'Not connected';
      if (heroAvatarStatus) {
        heroAvatarStatus.textContent = '● Offline (Not Connected)';
        heroAvatarStatus.className = 'profile-avatar-status';
      }
      if (heroInitialLarge) {
        heroInitialLarge.textContent = 'U';
        heroInitialLarge.style.display = 'flex';
      }
      if (heroPicLarge) heroPicLarge.style.display = 'none';

      if (pfName) pfName.textContent = '—';
      if (pfEmail) pfEmail.textContent = '—';
      if (pfGmailStatus) pfGmailStatus.innerHTML = '<span class="status-chip disconnected">Disconnected</span>';
      if (pfCalStatus) pfCalStatus.innerHTML = '<span class="status-chip disconnected">Disconnected</span>';
      if (pfTokenStatus) pfTokenStatus.innerHTML = '<span class="status-chip disconnected">Not issued</span>';
    }
  }
}

// Singleton
const larviContext = new LarviContext();
export default larviContext;
