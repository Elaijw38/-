// 量真实渲染几何：把结果写进 DOM，供 --dump-dom 读回
const fs = require('fs'), path = require('path'), vm = require('vm');
const ROOT = 'C:\\DSH\\字趣';
const out = path.join(__dirname, '..', '_check', 'geom.html');

const base = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const probe = `
<script>
(function(){
  function rect(sel){
    var el = document.querySelector(sel);
    if (!el) return null;
    var r = el.getBoundingClientRect();
    var cs = getComputedStyle(el);
    return { l: Math.round(r.left), t: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height),
             cols: cs.gridTemplateColumns, disp: cs.display, mw: cs.maxWidth };
  }
  var o = {
    vw: window.innerWidth, vh: window.innerHeight,
    nav: document.body.getAttribute('data-nav'),
    top: getComputedStyle(document.getElementById('siteTop')).display,
    shell: rect('.app-shell'),
    main: rect('.app-main'),
    wrap: rect('.wrap'),
    lead: rect('.home-lead'),
    grid: rect('.home-grid'),
    card1: rect('.home-card'),
    card2: rect('.home-card:nth-child(2)'),
    card3: rect('.home-card:nth-child(3)'),
    navbox: rect('.app-nav'),
    modegrid: rect('.mode-grid'),
    modecard: rect('.mode-card'),
    sect: rect('.sect'),
    shellDisp: (function () {
      var el = document.querySelector('.app-shell');
      return el ? getComputedStyle(el).display + ' / cols=' + getComputedStyle(el).gridTemplateColumns : null;
    })(),
    bodyBox: (function () {
      var cs = getComputedStyle(document.body), r = document.body.getBoundingClientRect();
      return { w: Math.round(r.width), l: Math.round(r.left),
               maxW: cs.maxWidth, w2: cs.width, pad: cs.padding, margin: cs.margin, disp: cs.display };
    })(),
    htmlBox: (function () {
      var cs = getComputedStyle(document.documentElement);
      var r = document.documentElement.getBoundingClientRect();
      return { w: Math.round(r.width), maxW: cs.maxWidth, disp: cs.display };
    })(),
    shellParent: (function () {
      var el = document.querySelector('.app-shell');
      var p = el && el.parentElement;
      return p ? (p.tagName + '.' + (p.className || '')) : null;
    })()
  };
  document.documentElement.setAttribute('data-geom', JSON.stringify(o));
})();
</script>
`;
const tmpName = '_geom.html';
fs.writeFileSync(path.join(ROOT, tmpName), base.replace('</body>', probe + '</body>'), 'utf8');

const { execFileSync } = require('child_process');
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const APP = process.argv[2] || '#/home';
const SIZE = process.argv[3] || '1440,900';
const url = 'file:///' + path.join(ROOT, tmpName).replace(/\\/g, '/') + APP;

let dom = '';
try {
  dom = execFileSync(EDGE, ['--headless=new', '--disable-gpu', '--no-sandbox',
    '--user-data-dir=' + path.join(ROOT, '_check', 'geomprof'),
    '--window-size=' + SIZE, '--virtual-time-budget=12000', '--dump-dom', url],
    { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, timeout: 120000 });
} catch (e) { dom = (e.stdout || '') + (e.stderr || ''); }

try { fs.unlinkSync(path.join(ROOT, tmpName)); } catch (e) {}

const m = dom.match(/data-geom="([^"]*)"/);
if (!m) { console.log('未取到 data-geom（长度 ' + dom.length + '）'); process.exit(1); }
const json = m[1].replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
const o = JSON.parse(json);
console.log('视口 ' + o.vw + 'x' + o.vh + '   body[data-nav]=' + o.nav + '   站点头 display=' + o.top);
const rows = [['.app-shell', o.shell], ['.app-main', o.main], ['.wrap', o.wrap],
              ['.home-lead', o.lead], ['.home-grid', o.grid],
              ['卡片1', o.card1], ['卡片2', o.card2], ['卡片3', o.card3],
              ['.app-nav', o.navbox], ['.mode-grid', o.modegrid], ['.mode-card', o.modecard],
              ['.sect', o.sect]];
console.log('  app-shell: ' + o.shellDisp + '   父元素: ' + o.shellParent);
console.log('  html: w=' + o.htmlBox.w + ' maxW=' + o.htmlBox.maxW);
console.log('  body: w=' + o.bodyBox.w + ' left=' + o.bodyBox.l + ' width=' + o.bodyBox.w2 +
  ' maxW=' + o.bodyBox.maxW + ' margin=' + o.bodyBox.margin + ' display=' + o.bodyBox.disp);
console.log('  body padding=' + o.bodyBox.pad);
for (const [n, r] of rows) {
  if (!r) { console.log('  ' + n.padEnd(12) + ' 不存在'); continue; }
  console.log('  ' + n.padEnd(12) + ' left=' + String(r.l).padStart(5) +
    ' width=' + String(r.w).padStart(5) + '  maxW=' + r.mw.padEnd(7) + '  cols=' + r.cols);
}
