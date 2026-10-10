// 执行探针：用最小 DOM 替身按真实顺序执行各脚本，定位运行期首个异常。
const fs = require('fs'), path = require('path'), vm = require('vm');
const ROOT = path.join(__dirname, '..');

/* ---------- 最小 DOM ---------- */
function mkEl(tag) {
  const el = {
    tagName: String(tag || 'div').toUpperCase(),
    children: [], childNodes: [], parentElement: null,
    _attr: {}, _html: '', _text: '', className: '', id: '',
    dataset: {},
    style: { cssText: '', setProperty() {}, getPropertyValue() { return ''; } },
    classList: { _s: new Set(), add(...c) { c.forEach(x => this._s.add(x)); }, remove(...c) { c.forEach(x => this._s.delete(x)); }, contains(c) { return this._s.has(c); }, toggle(c, f) { const has = this._s.has(c); const on = f === undefined ? !has : f; on ? this._s.add(c) : this._s.delete(c); return on; } },
    get innerHTML() { return this._html; },
    set innerHTML(v) { this._html = String(v); this.children = []; },
    get firstChild() { return this.children[0] || null; },
    get lastChild() { return this.children[this.children.length - 1] || null; },
    get textContent() { return this._text; },
    set textContent(v) { this._text = String(v); },
    appendChild(c) { if (c) { c.parentElement = this; this.children.push(c); } return c; },
    insertBefore(c) { return this.appendChild(c); },
    removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); return c; },
    prepend(c) { this.children.unshift(c); return c; },
    replaceChild(n) { return n; },
    insertAdjacentHTML(pos, h) { this._html += h; },
    setAttribute(k, v) { this._attr[k] = String(v); if (k === 'class') this.className = String(v); if (k.startsWith('data-')) this.dataset[k.slice(5)] = String(v); },
    getAttribute(k) { return this._attr[k] === undefined ? null : this._attr[k]; },
    removeAttribute(k) { delete this._attr[k]; },
    hasAttribute(k) { return k in this._attr; },
    addEventListener() {}, removeEventListener() {}, dispatchEvent() { return true; },
    click() { if (this.onclick) this.onclick(); },
    focus() {}, blur() {}, select() {}, remove() {},
    getBoundingClientRect() { return { top: 0, left: 0, width: 375, height: 667, right: 375, bottom: 667 }; },
    querySelector() { return null; }, querySelectorAll() { return []; },
    closest() { return null; }, contains() { return false; },
    scrollIntoView() {}, animate() { return { finished: Promise.resolve() }; },
    getContext() { return { drawImage() {}, fillRect() {}, clearRect() {}, getImageData() { return { data: [] }; }, putImageData() {} }; },
    toDataURL() { return 'data:image/png;base64,AAAA'; },
    cloneNode() { return mkEl(tag); },
  };
  return el;
}
const document = {
  documentElement: mkEl('html'), head: mkEl('head'), body: mkEl('body'),
  createElement: mkEl, createTextNode: t => ({ textContent: t, nodeValue: t }),
  createDocumentFragment: () => mkEl('fragment'),
  getElementById: () => null, querySelector: () => null, querySelectorAll: () => [],
  addEventListener() {}, removeEventListener() {},
  readyState: 'complete', title: '', cookie: '',
  fonts: { ready: Promise.resolve(), load: () => Promise.resolve() },
};

/* ---------- 沙箱 ---------- */
let step = '(初始化)';
const App = {};
const sandbox = {
  document, console,
  location: { hash: '', href: 'file:///C:/DSH/字趣/index.html', pathname: '/C:/DSH/字趣/index.html', search: '' },
  history: { pushState() {}, replaceState() {}, back() {} },
  navigator: { userAgent: 'node-probe', language: 'zh-CN', platform: 'Win32', maxTouchPoints: 0, clipboard: { writeText: () => Promise.resolve() } },
  localStorage: (() => { const m = new Map(); return { getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k), clear: () => m.clear(), key: i => [...m.keys()][i], get length() { return m.size; } }; })(),
  sessionStorage: (() => { const m = new Map(); return { getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k), clear: () => m.clear(), get length() { return m.size; } }; })(),
  matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }),
  getComputedStyle: () => ({ getPropertyValue: () => '' }),
  requestAnimationFrame: cb => setTimeout(cb, 0), cancelAnimationFrame() {},
  setTimeout, clearTimeout, setInterval: () => 1, clearInterval() {},
  addEventListener() {}, removeEventListener() {}, dispatchEvent() { return true; },
  alert() {}, confirm: () => true, prompt: () => null,
  fetch: () => Promise.reject(new Error('no network in probe')),
  URL: { createObjectURL: () => 'blob:x', revokeObjectURL() {} },
  Blob: function () {}, Image: function () { return mkEl('img'); },
  btoa: s => Buffer.from(String(s), 'binary').toString('base64'),
  atob: s => Buffer.from(String(s), 'base64').toString('binary'),
  App,
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
sandbox.self = sandbox;
const ctx = vm.createContext(sandbox);

/* ---------- 顺序执行 ---------- */
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
// 内联脚本（OB_PATTERN 等）
const inline = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const files = [...html.matchAll(/<script src="([^"]+)"><\/script>/g)].map(m => m[1]);

const pieces = [
  ...inline.map((s, i) => ({ name: '(内联脚本 #' + (i + 1) + ')', src: s })),
  ...files.map(f => ({ name: f, src: fs.readFileSync(path.join(ROOT, f), 'utf8') })),
];

let failed = 0;
for (const p of pieces) {
  step = p.name;
  try {
    new vm.Script(p.src, { filename: p.name }).runInContext(ctx);
    console.log('执行通过  ' + p.name);
  } catch (e) {
    failed++;
    console.log('运行异常  ' + p.name);
    console.log('          ' + e.constructor.name + ': ' + e.message);
    const m = (e.stack || '').match(/evalmachine[^:]*:(\d+):(\d+)/);
    if (m) {
      const lines = p.src.split('\n');
      const n = parseInt(m[1], 10);
      for (let i = Math.max(0, n - 4); i < Math.min(lines.length, n + 3); i++) {
        console.log('          ' + (i + 1) + (i + 1 === n ? ' >> ' : '    ') + (lines[i] || '').slice(0, 160));
      }
    }
    break; // 首个异常即停：它就是白屏根因
  }
}

console.log('\n=== 平台就绪状态 ===');
console.log('App 命名空间键: ' + Object.keys(App).join(', '));
console.log('已注册模式: ' + (App.modes && App.modes.list ? App.modes.list().map(m => m.id).join(',') : '(不可用)'));
console.log('主题: ' + (sandbox.document.documentElement.getAttribute('data-theme') || '(未设)'));
console.log('\n结论: ' + (failed ? '在「' + step + '」处首个运行期异常' : '全链路可执行，无运行期异常'));
