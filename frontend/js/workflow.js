/**
 * Larvi — Workflow Stepper UI Controller
 * Manages the live workflow progress visualization in the right sidebar.
 */

class WorkflowStepper {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.steps = [];
  }

  /**
   * Reset stepper for a new conversation turn.
   */
  reset() {
    this.steps = [];
    this._render();
  }

  /**
   * Add or update a workflow step.
   */
  updateStep(stepData) {
    const existing = this.steps.findIndex(s => s.step === stepData.step);
    if (existing >= 0) {
      this.steps[existing] = { ...this.steps[existing], ...stepData };
    } else {
      this.steps.push(stepData);
    }
    this._render();
  }

  /**
   * Replace all steps at once (used when final result arrives).
   */
  setSteps(steps) {
    this.steps = steps || [];
    this._render();
  }

  /**
   * Mark a step as in-progress.
   */
  setInProgress(stepNum) {
    const step = this.steps.find(s => s.step === stepNum);
    if (step) {
      step.status = 'in-progress';
      this._render();
    }
  }

  /**
   * Mark a step as done.
   */
  setDone(stepNum) {
    const step = this.steps.find(s => s.step === stepNum);
    if (step) {
      step.status = 'done';
      this._render();
    }
  }

  _render() {
    if (!this.container) return;

    if (this.steps.length === 0) {
      this.container.innerHTML = `<p class="stepper-empty">No active workflow.</p>`;
      return;
    }

    const ICONS = {
      done: '✓',
      'in-progress': '●',
      pending: '○',
      error: '✕',
    };

    this.container.innerHTML = `
      <div class="stepper-list">
        ${this.steps.map(step => `
          <div class="stepper-item">
            <div class="stepper-dot ${step.status || 'pending'}">
              ${ICONS[step.status] || step.step}
            </div>
            <div class="stepper-content">
              <div class="stepper-name">${this._escapeHtml(step.name || `Step ${step.step}`)}</div>
              ${step.detail ? `<div class="stepper-detail">${this._escapeHtml(step.detail)}</div>` : ''}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  _escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }
}

/**
 * Recent Actions Feed
 */
class ActionFeed {
  constructor(containerId, maxItems = 8) {
    this.container = document.getElementById(containerId);
    this.items = [];
    this.maxItems = maxItems;
  }

  addAction(icon, text) {
    const now = new Date();
    const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    this.items.unshift({ icon, text, time });
    if (this.items.length > this.maxItems) {
      this.items = this.items.slice(0, this.maxItems);
    }
    this._render();
  }

  addToolCallAction(toolCall) {
    const TOOL_ICONS = {
      search_emails: '🔍',
      read_email: '📧',
      get_recent_emails: '📥',
      create_draft: '✍️',
      send_email: '📤',
      reply_to_email: '↩️',
      get_events: '📅',
      search_events: '🔎',
      check_availability: '⏰',
      create_event: '➕',
      update_event: '✏️',
      delete_event: '🗑️',
    };
    const icon = TOOL_ICONS[toolCall.tool] || '🔧';
    const statusText = toolCall.result_status === 'success' ? '✅' : '⚙️';
    const text = `${statusText} ${toolCall.summary || toolCall.tool}`;
    this.addAction(icon, text);
  }

  _render() {
    if (!this.container) return;

    if (this.items.length === 0) {
      this.container.innerHTML = `<p class="memory-empty">No recent actions.</p>`;
      return;
    }

    this.container.innerHTML = this.items.map(item => `
      <div class="action-feed-item">
        <span class="action-feed-icon">${item.icon}</span>
        <span class="action-feed-text">${item.text}</span>
        <span class="action-feed-time">${item.time}</span>
      </div>
    `).join('');
  }
}

// Singletons
const workflowStepper = new WorkflowStepper('workflow-stepper-content');
const actionFeed = new ActionFeed('recent-actions-content');

export { workflowStepper, actionFeed };
