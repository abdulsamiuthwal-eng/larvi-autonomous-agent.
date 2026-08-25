/**
 * Larvi — Main Application Controller
 * Bootstraps the app, handles user input, coordinates all modules.
 */

import {
  sendChatMessage,
  getAuthStatus,
  getLoginUrl,
  checkHealth,
  fetchSessions,
  fetchSessionHistory,
  createNewSessionApi,
  deleteSessionApi,
  fetchRecentEmails,
  fetchCalendarEvents,
  fetchSettingsStats,
  clearAllDataApi,
  logoutGoogleApi,
} from './api.js';
import larviContext from './context.js';
import { workflowStepper, actionFeed } from './workflow.js';
import {
  renderUserMessage,
  renderLarviMessage,
  renderErrorMessage,
  showTyping,
  hideTyping,
  showToast,
  startStreamingLarviMessage,
  appendStreamingToken,
  appendStreamingToolCall,
  finalizeStreamingLarviMessage,
} from './chat.js';

// ── State ─────────────────────────────────────────────────────────────────────
let isSending = false;

// ── Quick Action Chips ────────────────────────────────────────────────────────
const QUICK_CHIPS = [
  {
    icon: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
    label: 'Check latest emails',
    text: 'Show me my latest emails',
  },
  {
    icon: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
    label: 'Today\'s schedule',
    text: 'What meetings do I have today?',
  },
  {
    icon: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>',
    label: 'Draft an email',
    text: 'Help me draft an email',
  },
  {
    icon: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    label: 'Am I free tomorrow?',
    text: 'Am I free tomorrow at 3 PM?',
  },
  {
    icon: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>',
    label: 'Unread summary',
    text: 'Summarize my unread emails',
  },
];

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  // Restore or init session
  larviContext.initSession();

  // Check URL for OAuth callback return (?auth=success&session_id=...)
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('auth') === 'success') {
    const sid = urlParams.get('session_id');
    if (sid) {
      larviContext.setSessionId(sid);
    }
    showToast('✅ Google account connected successfully!', 'success');
    // Clean URL without reload
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  // Render quick chips
  renderQuickChips();

  // Load Recent Chats List from SQLite
  await loadRecentChats();

  // If there's an active session with past messages, restore them
  if (larviContext.sessionId) {
    await restoreSessionMessages(larviContext.sessionId);
  }

  // Check backend health + auth status for this session
  await initHealthCheck();

  // Wire up event listeners
  setupEventListeners();

  // Current date in header
  updateDateDisplay();

  console.log('[Larvi] App initialized ✅ | Session ID:', larviContext.sessionId);
});

async function initHealthCheck() {
  try {
    const [health, auth] = await Promise.all([
      checkHealth(larviContext.sessionId),
      getAuthStatus(larviContext.sessionId),
    ]);

    larviContext.setAuthState(auth);

    // Update user email in sidebar
    const userEmailEl = document.getElementById('user-email-display');
    if (userEmailEl) {
      if (auth.email) {
        userEmailEl.textContent = auth.email;
      } else if (auth.authenticated) {
        userEmailEl.textContent = 'Connected';
      } else {
        userEmailEl.textContent = 'Not connected';
      }
    }

    if (health.status !== 'ok') {
      showToast('Backend server is not responding. Start the server first.', 'warning');
    }
  } catch {
    showToast('Cannot connect to Larvi backend. Make sure it is running on port 8000.', 'error');
  }
}

// ── Event Listeners ───────────────────────────────────────────────────────────

function setupEventListeners() {
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const newChatBtn = document.getElementById('new-chat-btn');
  const userProfile = document.getElementById('user-profile');

  // Send on button click
  if (sendBtn) {
    sendBtn.addEventListener('click', handleSend);
  }

  // Send on Enter (Shift+Enter = new line)
  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    });

    // Auto-resize textarea
    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 140) + 'px';
    });
  }

  // View Navigation Listeners
  const navChat = document.getElementById('nav-chat');
  const navInbox = document.getElementById('nav-inbox');
  const navCalendar = document.getElementById('nav-calendar');
  const navSettings = document.getElementById('nav-settings');

  if (navChat) navChat.addEventListener('click', () => switchView('chat'));
  if (navInbox) navInbox.addEventListener('click', () => switchView('inbox'));
  if (navCalendar) navCalendar.addEventListener('click', () => switchView('calendar'));
  if (navSettings) navSettings.addEventListener('click', () => switchView('settings'));

  // Inbox & Calendar View Action Listeners
  const inboxRefreshBtn = document.getElementById('inbox-refresh-btn');
  if (inboxRefreshBtn) inboxRefreshBtn.addEventListener('click', () => loadInboxView(true));
  const inboxComposeBtn = document.getElementById('inbox-compose-btn');
  if (inboxComposeBtn) inboxComposeBtn.addEventListener('click', () => {
    switchView('chat');
    window.sendQuickMessage('Help me draft a new email');
  });

  const calendarRefreshBtn = document.getElementById('calendar-refresh-btn');
  if (calendarRefreshBtn) calendarRefreshBtn.addEventListener('click', () => loadCalendarView(true));
  const calendarScheduleBtn = document.getElementById('calendar-schedule-btn');
  if (calendarScheduleBtn) calendarScheduleBtn.addEventListener('click', () => {
    switchView('chat');
    window.sendQuickMessage('Schedule a meeting tomorrow');
  });

  // Settings Action Listeners
  const settingsExportBtn = document.getElementById('settings-export-btn');
  if (settingsExportBtn) settingsExportBtn.addEventListener('click', exportChatData);
  const settingsClearChatsBtn = document.getElementById('settings-clear-chats-btn');
  if (settingsClearChatsBtn) settingsClearChatsBtn.addEventListener('click', promptClearAllChats);
  const settingsDeleteAccountBtn = document.getElementById('settings-delete-account-btn');
  if (settingsDeleteAccountBtn) settingsDeleteAccountBtn.addEventListener('click', promptDeleteAccount);

  // New conversation
  if (newChatBtn) {
    newChatBtn.addEventListener('click', () => {
      switchView('chat');
      handleNewChat();
    });
  }
  const sidebarNewChatBtn = document.getElementById('sidebar-new-chat-btn');
  if (sidebarNewChatBtn) {
    sidebarNewChatBtn.addEventListener('click', () => {
      switchView('chat');
      handleNewChat();
    });
  }

  // Mobile sidebar menu toggle
  const mobileMenuBtn = document.getElementById('mobile-menu-btn');
  const sidebarLeft = document.getElementById('sidebar-left');
  const sidebarOverlay = document.getElementById('sidebar-overlay');

  const toggleMobileSidebar = (open) => {
    if (!sidebarLeft || !sidebarOverlay) return;
    const shouldOpen = open !== undefined ? open : !sidebarLeft.classList.contains('mobile-open');
    if (shouldOpen) {
      sidebarLeft.classList.add('mobile-open');
      sidebarOverlay.classList.add('active');
    } else {
      sidebarLeft.classList.remove('mobile-open');
      sidebarOverlay.classList.remove('active');
    }
  };

  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', () => toggleMobileSidebar());
  }
  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', () => toggleMobileSidebar(false));
  }

  // Modal Cancel & Confirm Listeners
  const cancelBtn = document.getElementById('modal-cancel-btn');
  const confirmBtn = document.getElementById('modal-confirm-btn');
  const modalBackdrop = document.getElementById('modal-backdrop');

  if (cancelBtn) {
    cancelBtn.addEventListener('click', hideModal);
  }
  if (modalBackdrop) {
    modalBackdrop.addEventListener('click', (e) => {
      if (e.target === modalBackdrop) hideModal();
    });
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') hideModal();
  });
  if (confirmBtn) {
    confirmBtn.addEventListener('click', async () => {
      if (currentModalCallback) {
        const cb = currentModalCallback;
        hideModal();
        await cb();
      }
    });
  }

  // Auth connect button in banner
  const connectBtn = document.getElementById('connect-google-btn');
  if (connectBtn) {
    connectBtn.addEventListener('click', () => {
      const loginUrl = getLoginUrl(larviContext.sessionId);
      window.location.href = loginUrl;
    });
  }

  // Profile View Action Listeners
  const profileExportBtn = document.getElementById('profile-export-btn');
  if (profileExportBtn) profileExportBtn.addEventListener('click', exportChatData);
  const profileDeleteBtn = document.getElementById('profile-delete-btn');
  if (profileDeleteBtn) profileDeleteBtn.addEventListener('click', promptDeleteAccount);

  // User profile in sidebar -> Opens Profile View
  if (userProfile) {
    userProfile.addEventListener('click', () => {
      switchView('profile');
    });
  }
  const userProfileBtn = document.getElementById('user-profile-btn');
  if (userProfileBtn) {
    userProfileBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      switchView('profile');
    });
  }
}

// ── View Switching Logic ──────────────────────────────────────────────────────
let activeViewName = 'chat';

function switchView(viewName) {
  activeViewName = viewName;
  const headerTitle = document.getElementById('main-header-title');

  // Update Nav Item Active State
  const navItems = document.querySelectorAll('#nav-list .nav-item');
  navItems.forEach(item => item.classList.remove('active'));

  const activeNav = document.getElementById(`nav-${viewName}`);
  if (activeNav) activeNav.classList.add('active');

  // Hide all views, show selected
  const allViews = document.querySelectorAll('.app-view');
  allViews.forEach(v => {
    v.style.display = 'none';
    v.classList.remove('active');
  });

  const targetView = document.getElementById(`view-${viewName}`);
  if (targetView) {
    targetView.style.display = '';
    targetView.classList.add('active');
  }

  // Update Header Title
  if (headerTitle) {
    if (viewName === 'chat') {
      headerTitle.textContent = 'Chat & Workflows';
    } else if (viewName === 'inbox') {
      headerTitle.textContent = 'Gmail Inbox';
      loadInboxView();
    } else if (viewName === 'calendar') {
      headerTitle.textContent = 'Schedule & Agenda';
      loadCalendarView();
    } else if (viewName === 'profile') {
      headerTitle.textContent = 'User Profile & Account';
      loadProfileView();
    } else if (viewName === 'settings') {
      headerTitle.textContent = 'Settings & Configuration';
      loadSettingsView();
    }
  }

  // Close mobile sidebar if open
  const sidebarLeft = document.getElementById('sidebar-left');
  const sidebarOverlay = document.getElementById('sidebar-overlay');
  if (sidebarLeft) sidebarLeft.classList.remove('mobile-open');
  if (sidebarOverlay) sidebarOverlay.classList.remove('active');
}

// ── Inbox View Loader ─────────────────────────────────────────────────────────
async function loadInboxView(forceRefresh = false) {
  const container = document.getElementById('inbox-list-container');
  if (!container) return;

  container.innerHTML = `<div class="dashboard-loading"><div class="spinner"></div> Loading recent emails from Gmail…</div>`;

  const data = await fetchRecentEmails(larviContext.sessionId);
  if (!data || data.status !== 'success' || !data.emails || data.emails.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">
          <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"></polyline>
            <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"></path>
          </svg>
        </div>
        <div class="empty-state-text">
          <strong>No recent emails loaded.</strong><br>
          Connect your Google account to sync your live Gmail inbox.
        </div>
        <button class="btn btn-primary btn-sm" style="margin-top: 16px;" onclick="window.location.href=getLoginUrl(larviContext.sessionId)">
          Connect Gmail Account
        </button>
      </div>
    `;
    return;
  }

  container.innerHTML = data.emails.map(e => `
    <div class="email-card-item" onclick="window.larviApp.openEmailInChat('${escapeHtml(e.subject || 'Email')}', '${escapeHtml(e.from || 'Sender')}')">
      <div class="email-card-header">
        <span class="email-sender">
          <span class="sender-avatar-icon">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          </span>
          ${escapeHtml(e.from || 'Unknown Sender')}
        </span>
        <span class="email-date">${escapeHtml(e.date || '')}</span>
      </div>
      <div class="email-subject">${escapeHtml(e.subject || '(No Subject)')}</div>
      <div class="email-snippet">${escapeHtml(e.snippet || '')}</div>
      <div class="email-card-actions">
        <button class="btn-card-action" onclick="event.stopPropagation(); window.larviApp.askSummarizeEmail('${escapeHtml(e.subject || '')}', '${escapeHtml(e.from || '')}')">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          <span>Summarize</span>
        </button>
        <button class="btn-card-action" onclick="event.stopPropagation(); window.larviApp.askReplyEmail('${escapeHtml(e.subject || '')}', '${escapeHtml(e.from || '')}')">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          <span>Draft Reply</span>
        </button>
      </div>
    </div>
  `).join('');
}

// ── Calendar View Loader ──────────────────────────────────────────────────────
async function loadCalendarView(forceRefresh = false) {
  const container = document.getElementById('calendar-list-container');
  if (!container) return;

  container.innerHTML = `<div class="dashboard-loading"><div class="spinner"></div> Loading Google Calendar agenda…</div>`;

  const data = await fetchCalendarEvents(larviContext.sessionId);
  if (!data || data.status !== 'success' || !data.events || data.events.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">
          <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="16" y1="2" x2="16" y2="6"></line>
            <line x1="8" y1="2" x2="8" y2="6"></line>
            <line x1="3" y1="10" x2="21" y2="10"></line>
          </svg>
        </div>
        <div class="empty-state-text">
          <strong>No upcoming meetings scheduled.</strong><br>
          Ask Larvi to schedule an event or connect your Google Calendar.
        </div>
        <button class="btn btn-primary btn-sm" style="margin-top: 16px;" onclick="window.location.href=getLoginUrl(larviContext.sessionId)">
          Connect Google Calendar
        </button>
      </div>
    `;
    return;
  }

  container.innerHTML = data.events.map(ev => {
    const startStr = ev.start ? (ev.start.dateTime || ev.start.date || '') : '';
    const formattedTime = startStr ? new Date(startStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'All Day';
    const formattedDate = startStr ? new Date(startStr).toLocaleDateString([], { month: 'short', day: 'numeric', weekday: 'short' }) : '';
    const attendees = ev.attendees ? ev.attendees.map(a => a.email || a.displayName).join(', ') : 'Solo event';

    return `
      <div class="calendar-card-item">
        <div class="calendar-time-badge">
          <div class="time-start">${formattedTime}</div>
          <div class="time-dur">${formattedDate}</div>
        </div>
        <div class="calendar-event-body">
          <div class="calendar-event-title">${escapeHtml(ev.summary || 'Meeting')}</div>
          <div class="calendar-event-details">
            <span class="event-detail-item">
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              <span>${escapeHtml(attendees)}</span>
            </span>
            ${ev.hangoutLink ? `
              <a href="${ev.hangoutLink}" target="_blank" class="event-meet-link">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                <span>Google Meet</span>
              </a>
            ` : ''}
          </div>
          <div class="email-card-actions" style="margin-top: 6px;">
            <button class="btn-card-action" onclick="window.larviApp.rescheduleEvent('${escapeHtml(ev.summary || 'Meeting')}')">
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              <span>Reschedule with Larvi</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ── Profile View Loader ───────────────────────────────────────────────────────
async function loadProfileView() {
  const stats = await fetchSettingsStats(larviContext.sessionId);
  const btnContainer = document.getElementById('profile-auth-action-container');
  const sessionsNum = document.getElementById('pf-stat-sessions');
  const messagesNum = document.getElementById('pf-stat-messages');

  if (stats && stats.db_stats) {
    if (sessionsNum) sessionsNum.textContent = stats.db_stats.total_sessions || '0';
    if (messagesNum) messagesNum.textContent = stats.db_stats.total_messages || '0';
  }

  if (stats && stats.auth) {
    larviContext.setAuthState(stats.auth);
  }

  const isAuth = stats && stats.auth && stats.auth.authenticated;

  if (btnContainer) {
    if (isAuth) {
      btnContainer.innerHTML = `
        <button id="btn-disconnect-google-profile" class="btn btn-secondary btn-sm text-rose">
          Disconnect Google Account
        </button>
      `;
      const btn = document.getElementById('btn-disconnect-google-profile');
      if (btn) btn.addEventListener('click', promptDisconnectGoogle);
    } else {
      btnContainer.innerHTML = `
        <button class="btn-google-auth" onclick="window.location.href=getLoginUrl(larviContext.sessionId)">
          <svg class="google-auth-icon" viewBox="0 0 24 24" width="16" height="16">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
          </svg>
          <span>Connect Google Account</span>
        </button>
      `;
    }
  }
}

// ── Settings View Loader ──────────────────────────────────────────────────────
async function loadSettingsView() {
  const stats = await fetchSettingsStats(larviContext.sessionId);
  const emailDisplay = document.getElementById('settings-user-email-display');
  const btnContainer = document.getElementById('settings-auth-action-btn-container');
  const sessionsNum = document.getElementById('stat-sessions-num');
  const messagesNum = document.getElementById('stat-messages-num');

  if (stats && stats.db_stats) {
    if (sessionsNum) sessionsNum.textContent = stats.db_stats.total_sessions || '0';
    if (messagesNum) messagesNum.textContent = stats.db_stats.total_messages || '0';
  }

  const isAuth = stats && stats.auth && stats.auth.authenticated;
  const userEmail = isAuth && stats.auth.user ? stats.auth.user.email : null;

  if (emailDisplay) {
    emailDisplay.innerHTML = isAuth
      ? `<strong class="text-accent">${escapeHtml(userEmail || 'Google Account Connected')}</strong> (Gmail &amp; Calendar Linked)`
      : `Not connected — connect to enable autonomous actions.`;
  }

  if (btnContainer) {
    if (isAuth) {
      btnContainer.innerHTML = `
        <button id="btn-disconnect-google" class="btn btn-secondary btn-sm text-rose">
          Disconnect Account
        </button>
      `;
      document.getElementById('btn-disconnect-google').addEventListener('click', promptDisconnectGoogle);
    } else {
      btnContainer.innerHTML = `
        <button class="btn-google-auth" onclick="window.location.href=getLoginUrl(larviContext.sessionId)">
          <svg class="google-auth-icon" viewBox="0 0 24 24" width="16" height="16">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
          </svg>
          <span>Connect Google</span>
        </button>
      `;
    }
  }
}

// ── Export Chat Data ──────────────────────────────────────────────────────────
async function exportChatData() {
  const sessions = await fetchSessions();
  if (!sessions || sessions.length === 0) {
    showToast('No chat conversations to export', 'info');
    return;
  }

  const exportData = {
    exported_at: new Date().toISOString(),
    service: 'Larvi AI Agent',
    total_sessions: sessions.length,
    sessions: [],
  };

  for (const s of sessions) {
    const hist = await fetchSessionHistory(s.id);
    exportData.sessions.push({
      session_id: s.id,
      title: s.title,
      created_at: s.created_at,
      updated_at: s.updated_at,
      messages: hist ? hist.messages : [],
    });
  }

  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `larvi_ai_conversations_${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('All conversations exported to JSON', 'success');
}

// ── Confirmation Modal System ─────────────────────────────────────────────────
let currentModalCallback = null;

function showConfirmModal({ title, description, subtext, confirmText = 'Confirm', isDanger = false, onConfirm }) {
  currentModalCallback = onConfirm;

  const titleEl = document.getElementById('modal-title');
  const descEl = document.getElementById('modal-description');
  const confirmBtn = document.getElementById('modal-confirm-btn');
  const modalBackdrop = document.getElementById('modal-backdrop');

  if (titleEl) titleEl.textContent = title;
  if (descEl) {
    descEl.innerHTML = description;
    const subtextEl = document.querySelector('.modal-subtext');
    if (subtextEl && subtext) subtextEl.textContent = subtext;
  }

  if (confirmBtn) {
    confirmBtn.textContent = confirmText;
    confirmBtn.className = isDanger ? 'btn-modal btn-modal-delete' : 'btn-modal btn-primary';
  }

  if (modalBackdrop) modalBackdrop.classList.add('active');
}

function hideModal() {
  currentModalCallback = null;
  const modalBackdrop = document.getElementById('modal-backdrop');
  if (modalBackdrop) modalBackdrop.classList.remove('active');
}

function promptDisconnectGoogle() {
  showConfirmModal({
    title: 'Disconnect Google Account?',
    description: 'This will unlink your <strong>Gmail &amp; Google Calendar</strong> credentials.',
    subtext: 'You will need to reconnect to send emails or manage meetings.',
    confirmText: 'Disconnect',
    isDanger: true,
    onConfirm: async () => {
      await logoutGoogleApi(larviContext.sessionId);
      larviContext.auth.authenticated = false;
      larviContext.updateAgentStatus({ gmail_connected: false, calendar_connected: false });
      await checkAuthAndHealth();
      await loadSettingsView();
      showToast('Google account disconnected', 'info');
    },
  });
}

function promptClearAllChats() {
  showConfirmModal({
    title: 'Clear All Conversations?',
    description: 'This will permanently delete <strong>all saved chat sessions and messages</strong>.',
    subtext: 'This action cannot be undone.',
    confirmText: 'Clear All Chats',
    isDanger: true,
    onConfirm: async () => {
      await clearAllDataApi();
      await handleNewChat();
      await loadSettingsView();
      showToast('All chat history cleared', 'success');
    },
  });
}

function promptDeleteAccount() {
  showConfirmModal({
    title: 'Delete Account & Wipe Everything?',
    description: 'This will permanently wipe <strong>all Google tokens, SQLite databases, and conversation records</strong>.',
    subtext: 'Larvi will be completely reset to factory state.',
    confirmText: 'Wipe Everything',
    isDanger: true,
    onConfirm: async () => {
      await logoutGoogleApi(larviContext.sessionId);
      await clearAllDataApi();
      larviContext.clearSession();
      await checkAuthAndHealth();
      switchView('chat');
      await handleNewChat();
      showToast('Account and all memory wiped clean', 'success');
    },
  });
}

// ── Message Handling ──────────────────────────────────────────────────────────

async function handleSend() {
  if (isSending) return;

  const input = document.getElementById('chat-input');
  const text = input ? input.value.trim() : '';
  if (!text) return;

  if (input) {
    input.value = '';
    input.style.height = 'auto';
  }

  await sendMessage(text);
}

async function sendMessage(text) {
  isSending = true;
  setSendButtonState(true);

  if (activeViewName !== 'chat') {
    switchView('chat');
  }

  renderUserMessage(text);
  workflowStepper.reset();
  showTyping();

  try {
    let finalData = null;

    await sendChatMessage(text, larviContext.sessionId, {
      onTyping: () => {},
      onStep: (step) => workflowStepper.updateStep(step),
      onToolCall: (toolCall) => {
        actionFeed.addToolCallAction(toolCall);
        appendStreamingToolCall(toolCall);
      },
      onToken: (token) => appendStreamingToken(token),
      onFinal: async (data) => {
        finalData = data;
        if (data.session_id) larviContext.setSessionId(data.session_id);
        if (data.working_memory) larviContext.updateWorkingMemory(data.working_memory);
        hideTyping();
        finalizeStreamingLarviMessage(data);
        await loadRecentChats();
      },
      onError: (err) => {
        hideTyping();
        renderErrorMessage(`Something went wrong: ${err.message}`);
        showToast(err.message, 'error');
      },
    });

    if (!finalData) {
      try {
        const { sendChatMessageSync } = await import('./api.js');
        const result = await sendChatMessageSync(text, larviContext.sessionId);
        hideTyping();
        renderLarviMessage(result);
        if (result.session_id) larviContext.setSessionId(result.session_id);
        if (result.working_memory) larviContext.updateWorkingMemory(result.working_memory);
        if (result.workflow_steps) workflowStepper.setSteps(result.workflow_steps);
        result.tool_calls?.forEach(tc => actionFeed.addToolCallAction(tc));
      } catch (syncErr) {
        hideTyping();
        renderErrorMessage('Could not get a response. Please try again.');
      }
    }
  } catch (err) {
    hideTyping();
    renderErrorMessage(`Unexpected error: ${err.message}`);
  } finally {
    isSending = false;
    setSendButtonState(false);
    const input = document.getElementById('chat-input');
    if (input) input.focus();
  }
}

// ── Welcome Chip Click ────────────────────────────────────────────────────────
window.sendQuickMessage = function(text) {
  const input = document.getElementById('chat-input');
  if (input) input.value = text;
  sendMessage(text);
};

// ── Recent Chats & Session Management ─────────────────────────────────────────

async function loadRecentChats() {
  const container = document.getElementById('recent-chats-list');
  if (!container) return;

  const sessions = await fetchSessions();
  if (!sessions || sessions.length === 0) {
    container.innerHTML = `<div class="chat-history-empty">No conversations yet</div>`;
    return;
  }

  const currentSid = larviContext.sessionId;

  container.innerHTML = sessions.map(s => {
    const isActive = s.id === currentSid ? 'active' : '';
    const title = s.title || 'Conversation';
    const escapedTitle = title.replace(/'/g, "\\'").replace(/"/g, '&quot;');
    return `
      <div class="chat-history-item ${isActive}" data-sid="${s.id}" onclick="window.larviApp.switchSession('${s.id}')">
        <div class="chat-item-text">
          <span class="chat-item-icon glassy-icon-sm">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          </span>
          <span class="truncate" title="${title}">${title}</span>
        </div>
        <button class="chat-item-delete" title="Delete conversation" onclick="window.larviApp.promptDelete('${s.id}', '${escapedTitle}', event)">
          ✕
        </button>
      </div>
    `;
  }).join('');
}

async function restoreSessionMessages(sessionId) {
  const history = await fetchSessionHistory(sessionId);
  if (!history || !history.messages || history.messages.length === 0) {
    return;
  }

  const chatArea = document.getElementById('chat-area');
  const welcomeScreen = document.getElementById('welcome-screen');
  if (welcomeScreen) welcomeScreen.style.display = 'none';

  if (chatArea) {
    const oldMsgs = chatArea.querySelectorAll('.message-group');
    oldMsgs.forEach(m => m.remove());
  }

  for (const msg of history.messages) {
    if (msg.role === 'user') {
      renderUserMessage(msg.content);
    } else {
      renderLarviMessage({
        response: msg.content,
        agent_used: msg.agent_used || 'Larvi',
        intent: msg.intent || '',
        tool_calls: msg.tool_calls || [],
      });
    }
  }

  if (history.working_memory) {
    larviContext.updateWorkingMemory(history.working_memory);
  }
}

async function handleNewChat() {
  const newSession = await createNewSessionApi();
  if (newSession && newSession.session_id) {
    larviContext.setSessionId(newSession.session_id);
  } else {
    larviContext.clearSession();
  }

  workflowStepper.reset();

  const chatArea = document.getElementById('chat-area');
  if (chatArea) {
    const messages = chatArea.querySelectorAll('.message-group');
    messages.forEach(m => m.remove());
  }

  const welcomeScreen = document.getElementById('welcome-screen');
  if (welcomeScreen) welcomeScreen.style.display = '';

  const sidebarLeft = document.getElementById('sidebar-left');
  const sidebarOverlay = document.getElementById('sidebar-overlay');
  if (sidebarLeft) sidebarLeft.classList.remove('mobile-open');
  if (sidebarOverlay) sidebarOverlay.classList.remove('active');

  await loadRecentChats();
  showToast('New conversation started', 'success');
}

// ── Global App Window Object ──────────────────────────────────────────────────
window.larviApp = {
  switchSession: async (sessionId) => {
    if (activeViewName !== 'chat') switchView('chat');
    if (sessionId === larviContext.sessionId) return;
    larviContext.setSessionId(sessionId);

    const sidebarLeft = document.getElementById('sidebar-left');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    if (sidebarLeft) sidebarLeft.classList.remove('mobile-open');
    if (sidebarOverlay) sidebarOverlay.classList.remove('active');

    await restoreSessionMessages(sessionId);
    await loadRecentChats();
  },
  promptDelete: (sessionId, title, event) => {
    if (event) event.stopPropagation();
    showConfirmModal({
      title: 'Delete chat?',
      description: `This will delete <strong>"${title}"</strong>.`,
      subtext: 'This action cannot be undone.',
      confirmText: 'Delete',
      isDanger: true,
      onConfirm: async () => {
        await window.larviApp.executeDeleteChat(sessionId);
      },
    });
  },
  executeDeleteChat: async (sessionId) => {
    await deleteSessionApi(sessionId);
    if (sessionId === larviContext.sessionId) {
      handleNewChat();
    } else {
      await loadRecentChats();
    }
    showToast('Conversation deleted', 'info');
  },
  openEmailInChat: (subject, from) => {
    switchView('chat');
    window.sendQuickMessage(`Open and details for email with subject "${subject}" from ${from}`);
  },
  askSummarizeEmail: (subject, from) => {
    switchView('chat');
    window.sendQuickMessage(`Summarize email from ${from} regarding "${subject}"`);
  },
  askReplyEmail: (subject, from) => {
    switchView('chat');
    window.sendQuickMessage(`Draft a professional reply to ${from} about "${subject}"`);
  },
  rescheduleEvent: (summary) => {
    switchView('chat');
    window.sendQuickMessage(`Reschedule my meeting "${summary}" to a better time`);
  },
};

// ── UI Helpers ────────────────────────────────────────────────────────────────
function setSendButtonState(disabled) {
  const btn = document.getElementById('send-btn');
  if (btn) btn.disabled = disabled;
}

function renderQuickChips() {
  const row = document.getElementById('quick-chips-row');
  if (!row) return;
  row.innerHTML = QUICK_CHIPS.map(chip => `
    <button class="quick-chip" onclick="window.sendQuickMessage('${chip.text.replace(/'/g, "\\'")}')">
      <span class="chip-glassy-icon">${chip.icon}</span>
      <span>${chip.label}</span>
    </button>
  `).join('');
}

function updateDateDisplay() {
  const el = document.getElementById('current-date');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric',
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

