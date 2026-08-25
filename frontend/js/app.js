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
  { label: '📧 Check latest emails', text: 'Show me my latest emails' },
  { label: '📅 Today\'s schedule',   text: 'What meetings do I have today?' },
  { label: '✍️ Draft an email',      text: 'Help me draft an email' },
  { label: '🗓️ Am I free tomorrow?', text: 'Am I free tomorrow at 3 PM?' },
  { label: '📋 Unread summary',      text: 'Summarize my unread emails' },
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

  // New conversation
  if (newChatBtn) {
    newChatBtn.addEventListener('click', handleNewChat);
  }
  const sidebarNewChatBtn = document.getElementById('sidebar-new-chat-btn');
  if (sidebarNewChatBtn) {
    sidebarNewChatBtn.addEventListener('click', handleNewChat);
  }

  // Auth connect button in banner
  const connectBtn = document.getElementById('connect-google-btn');
  if (connectBtn) {
    connectBtn.addEventListener('click', () => {
      const loginUrl = getLoginUrl(larviContext.sessionId);
      window.location.href = loginUrl;
    });
  }

  // Clicking user profile in sidebar to connect if not authenticated
  if (userProfile) {
    userProfile.style.cursor = 'pointer';
    userProfile.title = 'Click to connect Google account';
    userProfile.addEventListener('click', () => {
      if (!larviContext.auth.authenticated) {
        const loginUrl = getLoginUrl(larviContext.sessionId);
        window.location.href = loginUrl;
      }
    });
  }
}

// ── Message Handling ──────────────────────────────────────────────────────────

async function handleSend() {
  if (isSending) return;

  const input = document.getElementById('chat-input');
  const text = input ? input.value.trim() : '';
  if (!text) return;

  // Clear input
  if (input) {
    input.value = '';
    input.style.height = 'auto';
  }

  await sendMessage(text);
}

async function sendMessage(text) {
  isSending = true;
  setSendButtonState(true);

  // Render user message
  renderUserMessage(text);

  // Reset workflow stepper
  workflowStepper.reset();

  // Show typing
  showTyping();

  try {
    let finalData = null;

    await sendChatMessage(text, larviContext.sessionId, {
      onTyping: () => {
        // Show typing
      },
      onStep: (step) => {
        workflowStepper.updateStep(step);
      },
      onToolCall: (toolCall) => {
        actionFeed.addToolCallAction(toolCall);
        appendStreamingToolCall(toolCall);
      },
      onToken: (token) => {
        appendStreamingToken(token);
      },
      onFinal: async (data) => {
        finalData = data;

        // Store session ID
        if (data.session_id) {
          larviContext.setSessionId(data.session_id);
        }

        // Update working memory
        if (data.working_memory) {
          larviContext.updateWorkingMemory(data.working_memory);
        }

        // Finalize streaming response card
        hideTyping();
        finalizeStreamingLarviMessage(data);

        // Refresh recent chats sidebar list
        await loadRecentChats();
      },
      onError: (err) => {
        hideTyping();
        renderErrorMessage(`Something went wrong: ${err.message}`);
        showToast(err.message, 'error');
      },
    });

    // If SSE failed silently, finalData might be null — nothing to do
    if (!finalData) {
      // Try sync fallback
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

    // Refocus input
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
    return `
      <div class="chat-history-item ${isActive}" data-sid="${s.id}" onclick="window.larviApp.switchSession('${s.id}')">
        <div class="chat-item-text">
          <span class="chat-item-icon">💬</span>
          <span class="truncate" title="${title}">${title}</span>
        </div>
        <button class="chat-item-delete" title="Delete conversation" onclick="window.larviApp.deleteChat('${s.id}', event)">
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

  await loadRecentChats();
  showToast('New conversation started', 'success');
}

// ── Global App Window Object ──────────────────────────────────────────────────
window.larviApp = {
  switchSession: async (sessionId) => {
    if (sessionId === larviContext.sessionId) return;
    larviContext.setSessionId(sessionId);
    await restoreSessionMessages(sessionId);
    await loadRecentChats();
  },
  deleteChat: async (sessionId, event) => {
    if (event) event.stopPropagation();
    await deleteSessionApi(sessionId);
    if (sessionId === larviContext.sessionId) {
      handleNewChat();
    } else {
      await loadRecentChats();
    }
    showToast('Conversation deleted', 'info');
  },
  confirmAction: () => {
    showToast('Action confirmed — executing...', 'success');
    const banner = document.querySelector('.confirmation-banner');
    if (banner) banner.remove();
  },
  cancelConfirmation: () => {
    showToast('Action cancelled', 'warning');
    const banner = document.querySelector('.confirmation-banner');
    if (banner) banner.remove();
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
      ${chip.label}
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
