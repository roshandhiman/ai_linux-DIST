const {createHash} = require('node:crypto');

const providers = {
  local: {label: 'MineOS Local', url: 'http://127.0.0.1:8080/v1', model: 'qwen2.5-1.5b-instruct'},
  openai: {label: 'OpenAI', url: 'https://api.openai.com/v1', model: 'gpt-5-mini', keyUrl: 'https://platform.openai.com/api-keys'},
  gemini: {label: 'Google Gemini', url: 'https://generativelanguage.googleapis.com/v1beta/openai', model: 'gemini-4-hydrogen', keyUrl: 'https://aistudio.google.com/apikey'},
  groq: {label: 'Groq', url: 'https://api.groq.com/openai/v1', model: 'llama-3.3-70b-versatile', keyUrl: 'https://console.groq.com/keys'},
  opencode: {label: 'OpenCode Console', url: 'https://opencode.ai/inference/openai/v1', model: 'deepseek-v4.1-flash', modelsUrl: 'https://opencode.ai/inference/v1/models', keyUrl: 'https://opencode.ai/console'},
  custom: {label: 'OpenAI-compatible', url: '', model: ''}
};

function endpoint(value, localOnly) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error('Enter a valid API base URL, including its version path.');
  }
  const loopback = ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname);
  if (url.username || url.password || url.search || url.hash ||
      (url.protocol !== 'https:' && !(loopback && url.protocol === 'http:')) ||
      (localOnly && !loopback)) {
    throw new Error('Use HTTPS for hosted providers or a loopback URL for a local model.');
  }
  return url.href.replace(/\/+$/, '');
}

function keyId(id, url) {
  const originKey = createHash('sha256').update(url).digest('hex').slice(0, 16);
  return 'mineos.provider.' + id + '.' + originKey;
}

async function request(url, key, options = {}) {
  const headers = {Accept: 'application/json', ...options.headers};
  if (key) headers.Authorization = 'Bearer ' + key;
  let result;
  try {
    result = await fetch(url, {...options, headers, redirect: 'error'});
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new Error('Could not connect to the model endpoint. Check the provider URL or local service.');
  }
  if (!result.ok) {
    await result.body?.cancel();
    const explanations = {
      401: 'Check the API key for this provider.', 403: 'Check your account and model access.',
      404: 'Check the model ID and base URL.', 429: 'The provider reached its usage limit. Try another model.'
    };
    throw new Error('HTTP ' + result.status + '. ' + (explanations[result.status] || 'The provider rejected the request.'));
  }
  return result;
}

async function listModels(config, signal) {
  const res = await request(config.modelsUrl || config.url + '/models', config.key, {signal});
  const data = await res.json();
  const entries = Array.isArray(data) ? data : data.data || data.models || [];
  return [...new Set(entries.map(row => row?.id || row?.model || row?.name)
    .filter(id => typeof id === 'string' && id.length < 200))].sort().slice(0, 350);
}

function extract(data) {
  const message = data?.choices?.[0]?.delta || data?.choices?.[0]?.message;
  if (typeof message?.content === 'string') return message.content;
  if (Array.isArray(message?.content)) return message.content.map(part => part.text || '').join('');
  return '';
}

async function parseSse(body, delta) {
  const decoder = new TextDecoder();
  let residue = '';
  let full = '';
  function readLine(raw) {
    if (!raw.startsWith('data:')) return;
    const value = raw.slice(5).trim();
    if (!value || value === '[DONE]') return;
    const data = JSON.parse(value);
    if (data.error) throw new Error('The model stopped the response early.');
    const part = extract(data);
    if (part) {
      full += part;
      if (full.length > 100000) throw new Error('The model response exceeded the editor limit.');
      delta?.(part);
    }
  }
  for await (const block of body) {
    const lines = (residue + decoder.decode(block, {stream: true})).split('\n');
    residue = lines.pop();
    if (residue.length > 131072) throw new Error('Invalid model stream.');
    lines.forEach(readLine);
  }
  readLine(residue + decoder.decode());
  return full;
}

async function complete(config, messages, maxTokens, signal, delta, structured = false) {
  const body = {model: config.model, messages, stream: Boolean(delta)};
  body[config.id === 'openai' ? 'max_completion_tokens' : 'max_tokens'] = maxTokens;
  if (structured && config.id === 'local') {
    body.response_format = {type: 'json_object'};
    body.temperature = 0.15;
  }
  const res = await request(config.url + '/chat/completions', config.key, {
    method: 'POST',
    signal,
    headers: {'Content-Type': 'application/json', Accept: delta ? 'text/event-stream' : 'application/json'},
    body: JSON.stringify(body)
  });
  const text = res.headers.get('content-type')?.includes('text/event-stream')
    ? await parseSse(res.body, delta)
    : extract(await res.json());
  if (!text.trim()) throw new Error('The selected model returned no text. Check its model ID and chat support.');
  return text;
}

module.exports = {providers, endpoint, keyId, listModels, complete};
