const fs = require('node:fs/promises');
const path = require('node:path');

const excluded = '{**/.*,**/.*/**,**/node_modules/**,**/vendor/**,**/dist/**,**/build/**,**/coverage/**,**/__pycache__/**,**/*.pem,**/*.key,**/*.pfx}';
const maxFileBytes = 1024 * 1024;
const maxContextChars = 11000;
const deniedText = /(?:-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----|\b(?:gh[pousr]_|github_pat_|sk-(?:proj-)?|gsk_|AIza)[A-Za-z0-9_-]{16,})/;

function inside(root, candidate) {
  const rel = path.relative(root, candidate);
  return Boolean(rel) && rel !== '..' && !rel.startsWith('..' + path.sep) && !path.isAbsolute(rel);
}

function cleanRelative(value) {
  if (typeof value !== 'string' || value.length > 240 || /[\x00-\x1f\\:]/.test(value)) return null;
  if (value.startsWith('../') || path.isAbsolute(value)) return null;
  const rel = value.replace(/^\.\//, '');
  if (!rel || rel.split('/').some(part => !part || part === '.' || part === '..' ||
      part.startsWith('.') ||
      /^(?:node_modules|vendor|dist|build|coverage|__pycache__|secrets?|credentials?|id_rsa|id_ed25519)$/i.test(part) ||
      /^(?:env|secrets?|credentials?)\./i.test(part) ||
      /\.(?:p12|pem|key|pfx|sqlite3?|db|lock)$/i.test(part) ||
      /^(?:package-lock\.json|bun\.lockb)$/i.test(part))) return null;
  return rel;
}

async function resolve(vscode, folder, relative, allowNew = false) {
  const safe = cleanRelative(relative);
  if (!safe || folder.uri.scheme !== 'file') throw new Error('Select a regular file inside this workspace.');
  const root = await fs.realpath(folder.uri.fsPath);
  const target = path.join(root, safe);
  if (!inside(root, target)) throw new Error('File is outside the workspace.');
  let info;
  try {
    info = await fs.lstat(target);
  } catch (error) {
    if (!allowNew || error.code !== 'ENOENT') throw error;
  }
  if (info) {
    if (!info.isFile() || info.size > maxFileBytes || await fs.realpath(target) !== target) {
      throw new Error('File is too large or resolves outside its original path.');
    }
  } else {
    const parent = path.dirname(target);
    if (await fs.realpath(parent) !== parent) throw new Error('New files require a regular workspace directory.');
  }
  return {uri: vscode.Uri.joinPath(folder.uri, ...safe.split('/')), safe, exists: Boolean(info)};
}

async function read(vscode, folder, relative) {
  const file = await resolve(vscode, folder, relative);
  const doc = await vscode.workspace.openTextDocument(file.uri);
  const value = doc.getText();
  if (/\0/.test(value) || value.length > maxFileBytes || deniedText.test(value)) throw new Error('File contains unsupported or sensitive content.');
  return {...file, doc, value};
}

async function contextFor(vscode, folder, files, limit = maxContextChars) {
  const snippets = [];
  const omitted = [];
  let remaining = limit;
  for (const [name, selected] of files) {
    if (remaining < 100) break;
    try {
      const item = await read(vscode, folder, name);
      const selection = selected?.trim() && item.value.includes(selected) ? selected : item.value;
      const slice = selection.slice(0, remaining);
      remaining -= slice.length;
      snippets.push({path: item.safe, text: slice, excerpt: slice.length < item.value.length});
    } catch {
      omitted.push(name);
    }
  }
  return {snippets, omitted};
}

async function filesIn(vscode, folder) {
  const results = await vscode.workspace.findFiles(new vscode.RelativePattern(folder, '**/*'), excluded, 220);
  return results.map(uri => cleanRelative(path.relative(folder.uri.fsPath, uri.fsPath))).filter(Boolean).sort();
}

function planFrom(text) {
  const trimmed = text.trim().replace(/^\x60{3}(?:json)?\s*/i, '').replace(/\s*\x60{3}$/, '');
  let plan;
  try {
    plan = JSON.parse(trimmed);
  } catch {
    const fenced = text.match(/\x60{3}json\s*([\s\S]+?)\x60{3}/i);
    if (!fenced) return null;
    try { plan = JSON.parse(fenced[1]); } catch { return null; }
  }
  if (!plan || typeof plan !== 'object' || Array.isArray(plan)) return null;
  return {
    summary: typeof plan.summary === 'string' ? plan.summary.slice(0, 4000) : '',
    read: Array.isArray(plan.read) ? plan.read.filter(cleanRelative).slice(0, 3) : [],
    edits: Array.isArray(plan.edits) ? plan.edits.slice(0, 8) : [],
    commands: Array.isArray(plan.commands) ? plan.commands.filter(item => item &&
      typeof item.command === 'string' && item.command.trim() && item.command.length <= 400 &&
      !/[\x00-\x1f\x7f]/.test(item.command)).slice(0, 4).map(item => ({
      command: item.command.trim(), reason: typeof item.reason === 'string' ? item.reason.slice(0, 200) : ''
    })) : []
  };
}

function replaceOnce(original, before, after) {
  if (typeof before !== 'string' || before.length === 0 || typeof after !== 'string') return null;
  const start = original.indexOf(before);
  if (start === -1 || original.indexOf(before, start + 1) !== -1) return null;
  return original.slice(0, start) + after + original.slice(start + before.length);
}

module.exports = {cleanRelative, contextFor, filesIn, planFrom, read, replaceOnce, resolve};
