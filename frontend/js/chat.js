/**
 * Larvi — Chat Rendering Engine
 * Handles message rendering, email/calendar widgets, typing indicator,
 * and confirmation banners.
 */

import { workflowStepper, actionFeed } from './workflow.js';

const chatArea = document.getElementById('chat-area');
const typingIndicator = document.getElementById('typing-indicator');
const welcomeScreen = document.getElementById('welcome-screen');

/**
 * Show the typing indicator.
 */
function showTyping() {
  if (typingIndicator) typingIndicator.classList.add('visible');
  scrollToBottom();
}

/**
 * Hide the typing indicator.
 */
function hideTyping() {
  if (typingIndicator) typingIndicator.classList.remove('visible');
}

/**
 * Render a user message bubble.
 */
function renderUserMessage(text) {
  hideWelcome();
  const group = document.createElement('div');
  group.className = 'message-group user';
  group.innerHTML = `
    <div class="msg-avatar user-avatar">U</div>
    <div class="msg-body">
      <div class="user-bubble">${escapeHtml(text)}</div>
    </div>
  `;
  insertBeforeTyping(group);
  scrollToBottom();
}

let currentStreamingGroup = null;
let currentStreamingBody = null;
let currentToolSec = null;
let streamingRawText = '';

/**
 * Start a live streaming message bubble for Larvi.
 */
function startStreamingLarviMessage(agentLabel = 'Larvi', intent = '') {
  if (currentStreamingGroup) {
    return currentStreamingGroup;
  }
  hideTyping();
  hideWelcome();

  const group = document.createElement('div');
  group.className = 'message-group larvi streaming';

  const agentBadge = buildAgentBadge(agentLabel, intent);

  group.innerHTML = `
    <div class="msg-avatar larvi-avatar">L</div>
    <div class="msg-body">
      <div class="larvi-card">
        <div class="larvi-card-header">
          <div class="agent-badge-row">
            ${agentBadge}
          </div>
          <span class="msg-timestamp">${getTime()}</span>
        </div>
        <div class="tool-calls-section" id="stream-tool-calls" style="display:none;"></div>
        <div class="larvi-card-body stream-text"><span class="streaming-cursor"></span></div>
      </div>
    </div>
  `;

  insertBeforeTyping(group);
  scrollToBottom();

  currentStreamingGroup = group;
  currentStreamingBody = group.querySelector('.stream-text');
  currentToolSec = group.querySelector('#stream-tool-calls');
  streamingRawText = '';
  return group;
}

/**
 * Append token chunk to the live streaming message bubble.
 */
function appendStreamingToken(token) {
  if (!currentStreamingGroup) {
    startStreamingLarviMessage();
  }
  streamingRawText += token;
  if (currentStreamingBody) {
    currentStreamingBody.innerHTML = formatResponseText(streamingRawText) + '<span class="streaming-cursor"></span>';
  }
  scrollToBottom();
}

/**
 * Append live tool call to the streaming message card.
 */
function appendStreamingToolCall(tc) {
  if (!currentStreamingGroup) {
    startStreamingLarviMessage();
  }
  if (currentToolSec) {
    currentToolSec.style.display = 'flex';
    const pill = document.createElement('div');
    pill.className = 'tool-call-pill';
    pill.innerHTML = `
      <span class="tool-status-dot"></span>
      <span class="tool-icon">🔧</span>
      ${escapeHtml(tc.summary || tc.tool || 'Tool Execution')}
    `;
    currentToolSec.appendChild(pill);
    scrollToBottom();
  }
}

/**
 * Finalize the streaming message with full cards, widgets, and confirmation.
 */
function finalizeStreamingLarviMessage(data) {
  if (currentStreamingGroup) {
    currentStreamingGroup.classList.remove('streaming');
    const cursor = currentStreamingGroup.querySelector('.streaming-cursor');
    if (cursor) cursor.remove();

    const badgeRow = currentStreamingGroup.querySelector('.agent-badge-row');
    if (badgeRow && data.agent_used) {
      badgeRow.innerHTML = buildAgentBadge(data.agent_used, data.intent || '');
    }

    if (currentStreamingBody) {
      currentStreamingBody.innerHTML = formatResponseText(data.response || streamingRawText);
    }

    const card = currentStreamingGroup.querySelector('.larvi-card');
    if (card) {
      if (data.requires_confirmation) {
        card.insertAdjacentHTML('beforeend', buildConfirmationBanner(data));
      }
      const smartWidgets = extractSmartWidgets(data);
      if (smartWidgets) {
        card.insertAdjacentHTML('beforeend', smartWidgets);
      }
    }

    currentStreamingGroup = null;
    currentStreamingBody = null;
    currentToolSec = null;
    streamingRawText = '';
    scrollToBottom();
  } else {
    renderLarviMessage(data);
  }
}

/**
 * Smart widget extraction from response text & metadata.
 */
function extractSmartWidgets(data) {
  let widgetsHtml = '';
  const text = data.response || '';

  // 1. Email Draft detection
  if (data._draft_data) {
    widgetsHtml += buildDraftWidget(data._draft_data);
  } else if (/draft/i.test(text) && (/to:\s*/i.test(text) || /subject:\s*/i.test(text))) {
    const toMatch = text.match(/to:\s*([^\n\r]+)/i);
    const subjMatch = text.match(/subject:\s*([^\n\r]+)/i);
    if (toMatch || subjMatch) {
      widgetsHtml += buildDraftWidget({
        to: toMatch ? toMatch[1].trim() : 'recipient@example.com',
        subject: subjMatch ? subjMatch[1].trim() : 'Draft Subject',
        body: text.split(/subject:[^\n\r]+/i)[1]?.trim() || text.slice(0, 150),
      });
    }
  }

  // 2. Email detection
  if (data._email_data) {
    widgetsHtml += buildEmailWidget(data._email_data);
  }

  // 3. Calendar Event detection
  if (data._event_data) {
    widgetsHtml += buildEventWidget(data._event_data);
  } else if ((data.intent === 'calendar' || /schedule|meeting|appointment|event/i.test(text)) && /\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b/i.test(text)) {
    const timeMatch = text.match(/\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b/i);
    widgetsHtml += buildEventWidget({
      title: 'Scheduled Meeting / Event',
      time: timeMatch ? timeMatch[0].toUpperCase() : '3:00 PM',
      status: 'confirmed',
    });
  }

  return widgetsHtml;
}

/**
 * Render a full Larvi response card with all sub-components.
 */
function renderLarviMessage(data) {
  hideTyping();
  hideWelcome();

  const {
    response = '',
    agent_used = 'Larvi',
    intent = '',
    tool_calls = [],
    requires_confirmation = false,
  } = data;

  const group = document.createElement('div');
  group.className = 'message-group larvi';

  const agentBadge = buildAgentBadge(agent_used, intent);
  const toolCallsHtml = buildToolCallsSection(tool_calls);
  const bodyHtml = formatResponseText(response);
  const confirmBannerHtml = requires_confirmation
    ? buildConfirmationBanner(data)
    : '';

  // Extract embedded widgets from data
  const smartWidgetsHtml = extractSmartWidgets(data);

  group.innerHTML = `
    <div class="msg-avatar larvi-avatar">L</div>
    <div class="msg-body">
      <div class="larvi-card">
        <div class="larvi-card-header">
          <div class="agent-badge-row">
            ${agentBadge}
          </div>
          <span class="msg-timestamp">${getTime()}</span>
        </div>
        ${toolCallsHtml}
        <div class="larvi-card-body">${bodyHtml}</div>
        ${smartWidgetsHtml}
        ${confirmBannerHtml}
      </div>
    </div>
  `;

  insertBeforeTyping(group);
  scrollToBottom();
  return group;
}

/**
 * Build agent identifier badge HTML.
 */
function buildAgentBadge(agentUsed, intent) {
  const INTENT_BADGE = {
    email: { cls: 'badge-amber', label: '📧 Email Agent' },
    calendar: { cls: 'badge-emerald', label: '📅 Calendar Agent' },
    multi: { cls: 'badge-accent', label: '🤖 Master Agent → Email + Calendar' },
    chitchat: { cls: 'badge-stone', label: '🤖 Larvi' },
    error: { cls: 'badge-stone', label: '⚠️ System' },
  };
  const cfg = INTENT_BADGE[intent] || { cls: 'badge-stone', label: agentUsed };
  return `<span class="badge ${cfg.cls}">${cfg.label}</span>`;
}

/**
 * Build collapsed tool call pills.
 */
function buildToolCallsSection(toolCalls) {
  if (!toolCalls || toolCalls.length === 0) return '';
  const pills = toolCalls.map(tc => `
    <div class="tool-call-pill">
      <span class="tool-status-dot"></span>
      <span class="tool-icon">🔧</span>
      ${escapeHtml(tc.summary || tc.tool)}
    </div>
  `).join('');
  return `<div class="tool-calls-section">${pills}</div>`;
}

/**
 * Format response markdown-like text to safe HTML.
 */
function formatResponseText(text) {
  if (!text) return '';
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code style="font-family:monospace;background:var(--color-surface-2);padding:1px 4px;border-radius:3px;">$1</code>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
    .replace(/^(.+)$/, '<p>$1</p>');
}

/**
 * Build an embedded email widget if email data is present.
 */
function buildEmailWidget(emailData) {
  if (!emailData) return '';
  const initial = (emailData.from || 'U').charAt(0).toUpperCase();
  const date = emailData.date ? new Date(emailData.date).toLocaleDateString() : '';
  return `
    <div class="email-widget">
      <div class="email-widget-header">
        <div class="email-sender-avatar">${initial}</div>
        <div class="email-meta">
          <div class="email-sender-name">${escapeHtml(emailData.from || 'Unknown')}</div>
          <div class="email-date">${escapeHtml(date)}</div>
        </div>
      </div>
      <div class="email-widget-subject">${escapeHtml(emailData.subject || '(No Subject)')}</div>
      <div class="email-widget-snippet">${escapeHtml(emailData.snippet || emailData.body?.slice(0, 120) || '')}</div>
      <div class="email-widget-footer">
        <span class="badge badge-stone">📧 Gmail</span>
      </div>
    </div>
  `;
}

/**
 * Build an interactive draft composer widget.
 */
function buildDraftWidget(draftData) {
  if (!draftData) return '';
  const to = draftData.to || draftData.recipient || 'recipient@example.com';
  const subject = draftData.subject || '(No Subject)';
  const body = draftData.body || draftData.content || '';

  return `
    <div class="draft-widget">
      <div class="draft-widget-header">
        <span>✍️ Email Draft</span>
        <span class="badge badge-amber">Draft Ready</span>
      </div>
      <div class="draft-row">
        <span class="draft-label">To:</span>
        <span class="draft-val">${escapeHtml(to)}</span>
      </div>
      <div class="draft-row">
        <span class="draft-label">Subject:</span>
        <span class="draft-val">${escapeHtml(subject)}</span>
      </div>
      <div class="draft-body-preview">${escapeHtml(body)}</div>
      <div class="draft-actions">
        <button class="btn btn-ghost btn-sm" onclick="window.sendQuickMessage('Discard this email draft')">
          🗑️ Discard
        </button>
        <button class="btn btn-primary btn-sm" onclick="window.sendQuickMessage('Yes, send this email to ' + '${escapeHtml(to)}')">
          ✉️ Send Email
        </button>
      </div>
    </div>
  `;
}

/**
 * Build an embedded calendar event widget if event data is present.
 */
function buildEventWidget(eventData) {
  if (!eventData) return '';
  const startDate = eventData.start ? new Date(eventData.start) : new Date();
  const day  = isNaN(startDate.getDate()) ? '26' : startDate.getDate();
  const mon  = isNaN(startDate.getDate()) ? 'AUG' : startDate.toLocaleString('en', { month: 'short' }).toUpperCase();
  const startTime = eventData.time || (isNaN(startDate.getTime()) ? '3:00 PM' : startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
  const endTime = eventData.end_time || '';
  const title = eventData.title || eventData.summary || 'Scheduled Meeting';

  const attendeesHtml = (eventData.attendees || []).slice(0, 3).map(a =>
    `<span class="attendee-chip">${escapeHtml(a)}</span>`
  ).join('');

  return `
    <div class="event-widget">
      <div class="event-widget-accent-bar"></div>
      <div class="event-widget-body">
        <div class="event-date-block">
          <span class="event-date-day">${day}</span>
          <span class="event-date-mon">${mon}</span>
        </div>
        <div class="event-details">
          <div class="event-title">${escapeHtml(title)}</div>
          <div class="event-time">🕐 ${startTime}${endTime ? ' – ' + endTime : ''}</div>
          ${attendeesHtml ? `<div class="event-attendees">${attendeesHtml}</div>` : ''}
        </div>
      </div>
      <div class="event-widget-footer">
        <span class="badge badge-emerald">📅 Google Calendar</span>
        <div class="event-action-bar">
          <button class="btn btn-ghost btn-sm" onclick="window.sendQuickMessage('Check other free time slots')">
            🕒 Reschedule
          </button>
          <button class="btn btn-primary btn-sm" onclick="window.sendQuickMessage('Confirm and add this event to Google Calendar')">
            ✅ Add to Calendar
          </button>
        </div>
      </div>
    </div>
  `;
}

/**
 * Build confirmation banner for destructive actions.
 */
function buildConfirmationBanner(data) {
  return `
    <div class="confirmation-banner">
      <div class="confirmation-banner-header">
        ⚠️ Action Requires Confirmation
      </div>
      <div class="confirmation-banner-text">
        Larvi is about to perform an action that cannot be undone.
        Please review and confirm.
      </div>
      <div class="confirmation-banner-actions">
        <button class="btn btn-ghost btn-sm" onclick="window.larviApp.cancelConfirmation()">
          Cancel
        </button>
        <button class="btn btn-primary btn-sm" onclick="window.larviApp.confirmAction()">
          Confirm & Execute
        </button>
      </div>
    </div>
  `;
}

/**
 * Render an error message.
 */
function renderErrorMessage(text) {
  hideTyping();
  const group = document.createElement('div');
  group.className = 'message-group larvi';
  group.innerHTML = `
    <div class="msg-avatar larvi-avatar">L</div>
    <div class="msg-body">
      <div class="larvi-card">
        <div class="larvi-card-header">
          <span class="badge badge-stone">⚠️ System</span>
          <span class="msg-timestamp">${getTime()}</span>
        </div>
        <div class="larvi-card-body">
          <p style="color:var(--color-rose);">${escapeHtml(text)}</p>
        </div>
      </div>
    </div>
  `;
  insertBeforeTyping(group);
  scrollToBottom();
}

/**
 * Show toast notification.
 */
function showToast(text, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const icons = { success: '✅', error: '❌', warning: '⚠️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || '✅'}</span>
    <span class="toast-text">${escapeHtml(text)}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('exit');
    setTimeout(() => toast.remove(), 220);
  }, 3500);
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function hideWelcome() {
  if (welcomeScreen) welcomeScreen.style.display = 'none';
}

function insertBeforeTyping(el) {
  if (chatArea && typingIndicator && chatArea.contains(typingIndicator)) {
    chatArea.insertBefore(el, typingIndicator);
  } else if (chatArea) {
    chatArea.appendChild(el);
  }
}

function scrollToBottom() {
  if (chatArea) {
    requestAnimationFrame(() => {
      chatArea.scrollTop = chatArea.scrollHeight;
    });
  }
}

function getTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export {
  renderUserMessage,
  renderLarviMessage,
  renderErrorMessage,
  showTyping,
  hideTyping,
  showToast,
  escapeHtml,
  startStreamingLarviMessage,
  appendStreamingToken,
  appendStreamingToolCall,
  finalizeStreamingLarviMessage,
};
