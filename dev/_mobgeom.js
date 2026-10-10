// 读取手机模拟页里 iframe 的几何：靠 --dump-dom 取回 data-geom
const fs = require('fs'), path = require('path');
const { execFileSync } = require('child_process');

void fs; void path;
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const url = process.argv[2];
const size = process.argv[3] || '420,860';

let dom = '';
try {
  dom = execFileSync(EDGE, ['--headless=new', '--disable-gpu', '--no-sandbox',
    '--user-data-dir=' + path.join(require('os').tmpdir(), 'zq_mobprof'),
    '--window-size=' + size, '--virtual-time-budget=16000', '--dump-dom', url],
    { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, timeout: 120000 });
} catch (e) { dom = (e.stdout || '') + (e.stderr || ''); }

const m = dom.match(/data-geom="([^"]*)"/);
if (!m) { console.log('未取到 data-geom（长度 ' + dom.length + '）'); process.exit(1); }
const json = m[1].replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
const o = JSON.parse(json);
console.log('iframe 视口宽 = ' + o.iframeW + '   body[data-nav]=' + o.nav);
console.log('  文档 scrollW=' + o.scrollW + '  clientW=' + o.clientW +
  (o.scrollW > o.clientW ? '   <-- 横向溢出' : '   无横向溢出'));
for (const k of ['navEl', 'brand', 'sub', 'item1', 'item4', 'foot', 'wrap', 'modeCard']) {
  console.log('  ' + k.padEnd(9) + ' ' + o[k]);
}
