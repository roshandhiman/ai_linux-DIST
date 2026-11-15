(() => {
const vscode = acquireVsCodeApi();
const app = document.getElementById('app');
const logo = app.dataset.logo;

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

function button(text, action, cls = 'quiet', label = text) {
  const node = el('button', cls, text);
  node.type = 'button';
  node.setAttribute('aria-label', label);
  node.title = label;
  node.addEventListener('click', action);
  return node;
}

const send = (type, details) => vscode.postMessage({type, ...details});
const remembered = vscode.getState() || {};
let mode = remembered.mode === 'edit' ? 'edit' : 'ask';
let state = {thread: [], plans: [], files: [], providers: [], config: {}};
let page = 'chat';
let queuedScroll = false;
let historyRows = [];
const messages = new Map();
const top = el('header', 'top');
const identity = el('div', 'identity');
const icon = el('img', 'brand');
icon.src = logo;
icon.alt = '';
const heading = el('div', 'heading');
heading.append(el('strong', '', 'MineOS Assistant'));
const end = el('div', 'header-actions');
end.append(
  button('＋', () => { show('chat'); send('new'); }, 'icon', 'New conversation'),
  button('↻', () => { historyRows = []; show('history'); send('history'); }, 'icon', 'Shared history'),
  button('⚙', () => send('settings'), 'icon', 'Model settings')
);
identity.append(icon, heading);
top.append(identity, end);
app.append(top);

const chat = el('section', 'chat current');
const scroll = el('div', 'scroll');
const welcome = el('div', 'welcome');
const welcomeLogo = el('img', 'welcome-logo');
welcomeLogo.src = logo;
welcomeLogo.alt = '';
welcome.append(welcomeLogo, el('h1', '', 'Work on your code'), el('p', '', 'Ask a question about your project or propose an edit.'));
const examples = el('div', 'examples');
for (const [label, prompt, value] of [
  ['Explain this file', 'Explain what the active file does and point out its entry point.', 'ask'],
  ['Review this code', 'Review the active file for correctness. Point out anything you can verify from the source.', 'ask'],
  ['Propose an edit', 'Suggest one small improvement to this file and show the change.', 'edit']
]) {
  examples.append(button(label, () => {
    setMode(value);
    input.value = prompt;
    input.focus();
    updateSend();
  }, 'suggestion'));
}
welcome.append(examples);
const transcript = el('div', 'transcript');
transcript.setAttribute('aria-label', 'Conversation');
const proposalList = el('div', 'proposals');
scroll.append(welcome, transcript, proposalList);
const composer = el('form', 'composer');
const chips = el('div', 'attachments');
const draft = el('div', 'draft');
const input = el('textarea', '', '');
input.placeholder = 'Ask MineOS about your code…';
input.rows = 3;
input.maxLength = 12000;
input.value = remembered.draft || '';
input.setAttribute('aria-label', 'Message MineOS');
input.addEventListener('input', () => {
  updateSend();
  vscode.setState({draft: input.value.slice(0, 12000), mode});
});
input.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    if (!sendButton.disabled) composer.requestSubmit();
  } else if (event.key === 'Escape' && state.busy) {
    send('cancel');
  }
});
const draftBottom = el('div', 'draft-bottom');
const controls = el('div', 'composer-controls');
const switcher = el('div', 'segmented');
switcher.setAttribute('aria-label', 'Assistant mode');
const ask = button('Ask', () => setMode('ask'), 'segment');
const edit = button('Edit', () => setMode('edit'), 'segment');
switcher.append(ask, edit);
const attach = button('＋ File', () => send('attach'), 'attach', 'Attach project files');
controls.append(switcher, attach);
const sendButton = button('↑', () => composer.requestSubmit(), 'submit', 'Send message');
draftBottom.append(controls, sendButton);
draft.append(input, draftBottom);

const footer = el('div', 'footer');
const activeLabel = el('label', 'active-file');
const activeToggle = document.createElement('input');
activeToggle.type = 'checkbox';
activeToggle.checked = remembered.includeActive !== false;
activeToggle.addEventListener('change', () => vscode.setState({draft: input.value, mode, includeActive: activeToggle.checked}));
const activeText = el('span', '', 'Active editor');
activeLabel.append(activeToggle, activeText);
const configButton = button('MineOS Local', () => send('settings'), 'provider-button');
footer.append(activeLabel, configButton);
composer.append(chips, draft, footer);
composer.addEventListener('submit', event => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || state.busy) return;
  send('send', {text, mode, includeActive: activeToggle.checked});
  input.value = '';
  vscode.setState({draft: '', mode, includeActive: activeToggle.checked});
  updateSend();
});
chat.append(scroll, composer);
app.append(chat);

const settings = el('section', 'subpage');
const history = el('section', 'subpage');
const notice = el('div', 'notice');
notice.setAttribute('role', 'status');
app.append(settings, history, notice);

function show(target) {
  page = target;
  for (const [name, node] of [['chat', chat], ['settings', settings], ['history', history]]) {
    node.classList.toggle('current', name === target);
  }
  if (target === 'chat') send('closeSettings');
}

function setMode(value) {
  mode = value;
  for (const [id, choice] of [['ask', ask], ['edit', edit]]) choice.setAttribute('aria-pressed', String(id === mode));
  input.placeholder = value === 'edit' ? 'Describe what you want to change…' : 'Ask MineOS about your code…';
  vscode.setState({draft: input.value, mode, includeActive: activeToggle.checked});
}

function updateSend() {
  sendButton.disabled = !state.busy && !input.value.trim();
  sendButton.textContent = state.busy ? '■' : '↑';
  sendButton.setAttribute('aria-label', state.busy ? 'Stop response' : 'Send message');
  sendButton.title = state.busy ? 'Stop response' : 'Send message';
  sendButton.onclick = state.busy ? event => { event.stopImmediatePropagation(); send('cancel'); } : null;
  input.setAttribute('aria-busy', String(state.busy));
}

function stickToEnd() {
  if (queuedScroll || scroll.scrollHeight - scroll.scrollTop - scroll.clientHeight > 220) return;
  queuedScroll = true;
  requestAnimationFrame(() => {
    scroll.scrollTop = scroll.scrollHeight;
    queuedScroll = false;
  });
}

function updateThread(thread) {
  welcome.hidden = thread.length !== 0;
  const current = new Set(thread.map(item => item.id));
  for (const [id, node] of messages) {
    if (!current.has(id)) {
      node.remove();
      messages.delete(id);
    }
  }
  for (const item of thread) {
    let node = messages.get(item.id);
    if (!node) {
      node = el('article', 'message ' + item.role);
      node.append(el('div', 'message-label', item.role === 'user' ? 'You' : 'MineOS'), el('div', 'message-body'));
      transcript.append(node);
      messages.set(item.id, node);
    }
    node.classList.toggle('error', Boolean(item.error));
    const body = node.lastElementChild;
    const value = item.text || (state.busy ? (item.mode === 'edit' ? 'Preparing changes…' : 'Thinking…') : '');
    if (body.textContent !== value) body.textContent = value;
  }
  stickToEnd();
}

function updateProposals(plans) {
  proposalList.replaceChildren();
  for (const item of plans) {
    const row = el('article', 'proposal');
    const lead = el('div', 'proposal-content');
    lead.append(el('span', 'proposal-kind', item.type === 'edit' ? 'File change' : 'Terminal command'));
    lead.append(el('strong', '', item.label));
    if (item.reason) lead.append(el('p', '', item.reason));
    const actions = el('div', 'proposal-actions');
    if (item.type === 'edit') actions.append(button('View Diff', () => send('diff', {id: item.id}), 'quiet'));
    if (item.awaitingConfirmation) {
      actions.append(button('Confirm and Run', () => send('runCommand', {id: item.id}), 'small-primary'));
      actions.append(button('Cancel', () => send('cancelCommand', {id: item.id}), 'quiet'));
    } else if (!item.done) {
      const label = item.type === 'edit' ? 'Apply' : 'Run in Terminal';
      actions.append(button(label, () => send(item.type === 'edit' ? 'apply' : 'command', {id: item.id}), 'small-primary'));
      actions.append(button('Dismiss', () => send('dismiss', {id: item.id}), 'quiet'));
    } else {
      actions.append(el('span', 'complete', item.type === 'edit' ? 'Applied' : 'Sent to Terminal'));
    }
    row.append(lead, actions);
    proposalList.append(row);
  }
}

function formHeader(title) {
  const container = el('div', 'subhead');
  container.append(button('‹', () => show('chat'), 'icon', 'Back to chat'), el('h1', '', title));
  return container;
}

function field(label, item, help) {
  const node = el('label', 'field');
  node.append(el('span', '', label), item);
  if (help) node.append(el('small', '', help));
  return node;
}

function settingInput(value, placeholder, type = 'text') {
  const node = document.createElement('input');
  node.type = type;
  node.value = value || '';
  node.placeholder = placeholder || '';
  node.autocapitalize = 'none';
  node.spellcheck = false;
  node.autocomplete = 'off';
  return node;
}

function settingsPage(form) {
  settings.replaceChildren(formHeader('Model settings'));
  const body = el('div', 'form-body');
  const formNode = el('form', 'settings-form');
  const provider = document.createElement('select');
  for (const entry of state.providers) {
    const option = el('option', '', entry.label);
    option.value = entry.id;
    provider.append(option);
  }
  provider.value = form.id;
  provider.addEventListener('change', () => {
    formNode.inert = true;
    send('settings', {id: provider.value});
  });
  const url = settingInput(form.url, 'https://provider.example/v1');
  url.readOnly = !form.editableUrl;
  const model = settingInput(form.model, 'Model ID');
  if (form.modelIds?.length) {
    const candidates = document.createElement('datalist');
    candidates.id = 'models';
    for (const name of form.modelIds) {
      const option = document.createElement('option');
      option.value = name;
      candidates.append(option);
    }
    model.setAttribute('list', candidates.id);
    formNode.append(candidates);
  }
  const key = settingInput('', form.sessionOnly ? 'Kept for this session' : (form.keySaved ? 'Saved in editor credential storage' : 'Paste an API key'), 'password');
  const gather = () => ({id: provider.value, url: url.value, model: model.value, key: key.value});
  formNode.append(field('Provider', provider), field('Base URL', url), field('Model', model));
  if (form.id !== 'local') formNode.append(field('API key', key, 'Hosted requests use your provider account.'));
  const links = el('div', 'settings-links');
  if (form.keyUrl) links.append(button('Get API key ↗', () => send('keyLink', {id: provider.value}), 'text-button'));
  if (form.keySaved) links.append(button('Remove saved key', () => send('deleteKey', {id: provider.value}), 'text-button'));
  if (links.childNodes.length) formNode.append(links);
  const actions = el('div', 'settings-actions');
  actions.append(button('Fetch models', () => send('listModels', gather()), 'quiet'));
  const save = el('button', 'small-primary', 'Save and use');
  save.type = 'submit';
  actions.append(save);
  formNode.append(actions);
  formNode.addEventListener('submit', event => {
    event.preventDefault();
    send('saveSettings', gather());
  });
  body.append(formNode);
  settings.append(body);
  show('settings');
}

function historyPage(rows, unavailable, append = false) {
  historyRows = append ? [...historyRows, ...rows] : rows;
  history.replaceChildren(formHeader('Shared history'));
  const content = el('div', 'history-list');
  if (!historyRows.length) content.append(el('p', 'empty', unavailable ? 'Shared history requires the MineOS terminal agent.' : 'No saved requests yet.'));
  for (const [_, at, request, answer, channel] of historyRows) {
    const row = el('article', 'history-item');
    const meta = el('div', 'history-meta', (channel === 'ide' ? 'IDE' : 'Terminal') + ' · ' + new Date(at * 1000).toLocaleString());
    row.append(meta, el('strong', '', request));
    if (answer) {
      const details = el('details', 'history-answer');
      details.append(el('summary', '', 'Show response'), el('p', '', answer));
      row.append(details);
    }
    row.append(button('Reuse request', () => {
      show('chat');
      input.value = request;
      input.focus();
      updateSend();
    }, 'text-button'));
    content.append(row);
  }
  if (rows.length === 15 && rows.at(-1)?.[0]) {
    content.append(button('Load earlier requests', () => send('history', {before: rows.at(-1)[0]}), 'quiet earlier'));
  }
  history.append(content);
}

let noticeTimer;
function displayNotice(text, error = false) {
  clearTimeout(noticeTimer);
  notice.textContent = text;
  notice.classList.toggle('alert', error);
  notice.classList.toggle('visible', Boolean(text));
  if (text) noticeTimer = setTimeout(() => notice.classList.remove('visible'), 5500);
}

window.addEventListener('message', event => {
  const data = event.data;
  if (data.type === 'state') {
    state = data;
    configButton.textContent = state.config.label || 'Model settings';
    configButton.title = state.config.model || '';
    activeText.textContent = state.activeFile ? state.activeFile.split('/').pop() : 'Active editor';
    activeLabel.title = state.activeFile || 'Include the active editor';
    activeToggle.disabled = !state.activeFile;
    chips.replaceChildren();
    for (const file of state.files) {
      const chip = el('span', 'chip');
      chip.title = file;
      chip.append(el('span', '', file.split('/').pop()), button('×', () => send('removeFile', {path: file}), 'chip-close', 'Remove ' + file));
      chips.append(chip);
    }
    updateThread(state.thread);
    updateProposals(state.plans);
    updateSend();
  } else if (data.type === 'stream') {
    const node = messages.get(data.id);
    if (node) {
      node.lastElementChild.textContent = data.text;
      stickToEnd();
    }
  } else if (data.type === 'settings') {
    settingsPage(data.form);
  } else if (data.type === 'settingsClosed') {
    show('chat');
  } else if (data.type === 'history') {
    if (page === 'history') historyPage(data.rows, data.unavailable, data.append);
  } else if (data.type === 'notice') {
    displayNotice(data.text, data.error);
  }
});

history.append(formHeader('Shared history'), el('p', 'empty', 'Loading history…'));
setMode(mode);
updateSend();
send('ready');
})();
