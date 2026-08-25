/**
 * Larvi — Backend API Client
 * Clean fetch wrapper for all backend communication.
 */

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? (window.location.port === '5500' ? 'http://127.0.0.1:8000' : window.location.origin)
  : window.location.origin;

/**
 * Send a chat message and get SSE stream back.
 * @param {string} message - User message
 * @param {string|null} sessionId - Session ID (null for new session)
 * @param {object} callbacks - { onStep, onToolCall, onFinal, onToken, onTyping, onError, onAbort }
 * @param {AbortSignal|null} signal - Optional abort signal
 */
async function sendChatMessage(message, sessionId, callbacks = {}, signal = null) {
  const { onStep, onToolCall, onFinal, onToken, onTyping, onError, onAbort } = callbacks;

  try {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
      signal: signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Server error: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line in buffer

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const data = line.slice(6).trim();
        if (data === '[DONE]') continue;

        try {
          const event = JSON.parse(data);

          if (event.type === 'typing' && onTyping) {
            onTyping(event);
          } else if (event.type === 'workflow_step' && onStep) {
            onStep(event.step);
          } else if (event.type === 'tool_call' && onToolCall) {
            onToolCall(event.tool_call);
          } else if (event.type === 'token' && onToken) {
            onToken(event.token);
          } else if (event.type === 'final' && onFinal) {
            onFinal(event);
          }
        } catch (e) {
          // Skip malformed SSE events
        }
      }
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      if (onAbort) onAbort();
      return;
    }
    if (onError) onError(err);
    else console.error('[API] Chat error:', err);
  }
}

/**
 * Non-streaming fallback chat (for when SSE is unavailable).
 */
async function sendChatMessageSync(message, sessionId, signal = null) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
    signal: signal,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Request failed');
  }
  return response.json();
}

/**
 * Check Google OAuth status for a session.
 * @param {string|null} sessionId
 */
async function getAuthStatus(sessionId = null) {
  try {
    const url = sessionId
      ? `${API_BASE}/auth/status?session_id=${encodeURIComponent(sessionId)}`
      : `${API_BASE}/auth/status`;
    const res = await fetch(url);
    return res.json();
  } catch {
    return { authenticated: false };
  }
}

/**
 * Get Google OAuth Login URL for a session.
 * @param {string|null} sessionId
 */
function getLoginUrl(sessionId = null) {
  return sessionId
    ? `${API_BASE}/auth/login?session_id=${encodeURIComponent(sessionId)}`
    : `${API_BASE}/auth/login`;
}

/**
 * Check server health.
 */
async function checkHealth(sessionId = null) {
  try {
    const url = sessionId
      ? `${API_BASE}/health?session_id=${encodeURIComponent(sessionId)}`
      : `${API_BASE}/health`;
    const res = await fetch(url);
    return res.json();
  } catch {
    return { status: 'offline' };
  }
}

/**
 * Get session working memory.
 */
async function getSessionMemory(sessionId) {
  try {
    const res = await fetch(`${API_BASE}/session/${sessionId}/memory`);
    return res.json();
  } catch {
    return null;
  }
}

/**
 * Fetch all sessions for chat history sidebar.
 */
async function fetchSessions() {
  try {
    const res = await fetch(`${API_BASE}/sessions`);
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

/**
 * Fetch full message history for a specific session.
 */
async function fetchSessionHistory(sessionId) {
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

/**
 * Create a new session in SQLite DB.
 */
async function createNewSessionApi() {
  try {
    const res = await fetch(`${API_BASE}/sessions`, { method: 'POST' });
    return res.json();
  } catch {
    return null;
  }
}

/**
 * Delete a session from DB.
 */
async function deleteSessionApi(sessionId) {
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' });
    return res.json();
  } catch {
    return null;
  }
}

/**
 * Fetch recent emails for inbox view.
 */
async function fetchRecentEmails(sessionId) {
  try {
    const url = sessionId ? `${API_BASE}/emails/list?session_id=${sessionId}` : `${API_BASE}/emails/list`;
    const res = await fetch(url);
    if (!res.ok) return { status: 'error', emails: [] };
    return res.json();
  } catch {
    return { status: 'error', emails: [] };
  }
}

/**
 * Fetch upcoming calendar events for schedule view.
 */
async function fetchCalendarEvents(sessionId) {
  try {
    const url = sessionId ? `${API_BASE}/calendar/list?session_id=${sessionId}` : `${API_BASE}/calendar/list`;
    const res = await fetch(url);
    if (!res.ok) return { status: 'error', events: [] };
    return res.json();
  } catch {
    return { status: 'error', events: [] };
  }
}

/**
 * Fetch settings metrics and database telemetry.
 */
async function fetchSettingsStats(sessionId) {
  try {
    const url = sessionId ? `${API_BASE}/settings/stats?session_id=${sessionId}` : `${API_BASE}/settings/stats`;
    const res = await fetch(url);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

/**
 * Clear all data from SQLite database.
 */
async function clearAllDataApi() {
  try {
    const res = await fetch(`${API_BASE}/settings/clear-all`, { method: 'POST' });
    return res.json();
  } catch {
    return null;
  }
}

/**
 * Disconnect Google Account.
 */
async function logoutGoogleApi(sessionId) {
  try {
    const url = sessionId ? `${API_BASE}/auth/logout?session_id=${sessionId}` : `${API_BASE}/auth/logout`;
    const res = await fetch(url, { method: 'POST' });
    return res.json();
  } catch {
    return null;
  }
}

export {
  API_BASE,
  sendChatMessage,
  sendChatMessageSync,
  getAuthStatus,
  getLoginUrl,
  checkHealth,
  getSessionMemory,
  fetchSessions,
  fetchSessionHistory,
  createNewSessionApi,
  deleteSessionApi,
  fetchRecentEmails,
  fetchCalendarEvents,
  fetchSettingsStats,
  clearAllDataApi,
  logoutGoogleApi,
};
