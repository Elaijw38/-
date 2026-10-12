// WCAG 对比度审计：把 theme.css 各主题的变量解出来，逐对算对比度
const fs = require('fs'), path = require('path');
const CSS = fs.readFileSync(path.join(__dirname, '..', 'css', 'theme.css'), 'utf8');

/* ---------- 解析变量块 ---------- */
function block(selector) {
  const i = CSS.indexOf(selector);
  if (i < 0) return null;
  const s = CSS.indexOf('{', i), e = CSS.indexOf('}', s);
  const body = CSS.slice(s + 1, e);
  const vars = {};
  for (const m of body.matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/g)) {
    vars[m[1]] = m[2].trim().replace(/\/\*[\s\S]*?\*\//g, '').trim();
  }
  return vars;
}

const root = block(':root');
/* 站点只有一套外观：:root 打底，再被 html[data-theme="bone"] 覆盖。
   实际生效值 = 两者合并（后者优先）。 */
const themes = {
  'bone（唯一外观）': Object.assign({}, root, block('html[data-theme="bone"]') || {}),
};

/* ---------- 解析颜色（支持 var() 别名、#rgb、#rrggbb） ---------- */
function resolve(name, vars, depth) {
  depth = depth || 0;
  if (depth > 8) return null;
  let v = vars[name];
  if (v === undefined) v = root[name];
  if (v === undefined) return null;
  const alias = v.match(/^var\(\s*(--[a-z0-9-]+)\s*\)$/);
  if (alias) return resolve(alias[1], vars, depth + 1);
  /* 面料分层用 color-mix() 混出"面中面"。
     不认这个函数，审计就会漏检——而漏检比算错更危险。 */
  const mix = v.match(
    /^color-mix\(in srgb,\s*var\((--[a-z0-9-]+)\)\s*([\d.]+)%\s*,\s*var\((--[a-z0-9-]+)\)\s*\)$/);
  if (mix) {
    const ca = resolve(mix[1], vars, depth + 1), cb = resolve(mix[3], vars, depth + 1);
    if (!ca || !cb) return null;
    const p = parseFloat(mix[2]) / 100;
    const out = rgb(ca).map((x, i) => Math.round(x * p + rgb(cb)[i] * (1 - p)));
    return '#' + out.map(x => x.toString(16).padStart(2, '0')).join('');
  }
  const m = v.match(/#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b/);
  if (!m) return null;
  let h = m[1];
  if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
  return '#' + h.toLowerCase();
}
/* rgb() 在 resolve() 里就被用到了，提到前面（函数声明会提升，但可读性更好） */
function rgb(hex) {
  return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)];
}
function lum(hex) {
  const [r, g, b] = rgb(hex).map(c => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrast(a, b) {
  const la = lum(a), lb = lum(b);
  const hi = Math.max(la, lb), lo = Math.min(la, lb);
  return (hi + 0.05) / (lo + 0.05);
}

/* ---------- 实际用到的「文字色 × 背景」组合 ---------- */
const pairs = [
  ['--on-dark',   '--ink-deep', '深色面正文（品牌主视觉）'],
  ['--on-dark-2', '--ink-deep', '深色面次要文字'],
  ['--ink',      '--bone',    '正文（.lead/.glyph/.info）'],
  ['--ink',      '--card',    '正文（卡片内）'],
  ['--ink',      '--sheet',   '正文（纸面：卡片 / 展板 / 分区块）'],
  ['--ink',      '--sheet-in','正文（内嵌托盘 / 面中面）'],
  ['--ink',      '--bone1',   '正文（构件格/比分板）'],
  ['--ink-2',    '--bone',    '次要文字（.mc-desc/.hc-note 说明）'],
  ['--ink-2',    '--card',    '次要文字（卡片内）'],
  ['--ink-2',    '--sheet',   '次要文字（纸面）'],
  ['--ink-2',    '--bone1',   '次要文字（比分板/构件）'],
  ['--ink-soft', '--bone',    '最弱文字（.mc-foot 类型/字包）'],
  ['--ink-soft', '--bone1',   '最弱文字（.piece .n 构件名）'],
  ['--ink-soft', '--sheet',   '最弱文字（纸面上的出处 / 注记）'],
  ['--cinnabar-tint', '--bone',  '朱砂文字（.prob）'],
  ['--cinnabar-tint', '--bone1', '朱砂文字（.rv .g-no）'],
  ['--cinnabar-tint', '--card',  '朱砂文字（.hc-icon 图标字）'],
  ['--bronze-tint', '--bone',  '青铜文字（.hc-note）'],
  ['--bronze-tint', '--bone1', '青铜文字（.pts 比分/.mc-tagline）'],
  ['--bronze-tint', '--card',  '青铜文字（.mc-badge）'],
  ['--blue-tint',   '--bone1', '蓝文字（.pl.p2 .pts）'],
  ['--blue-tint',   '--card',  '蓝文字（.rv .g-ch）'],
  ['--green-tint',  '--bone',  '绿文字（.rv .g-ok）'],
  ['--green-tint',  '--card',  '绿文字（.rv .g-ok 卡片内）'],
  ['--cinnabar-tint', '--bone', '朱砂文字（.rv .g-no 大字/题面）'],
  ['--glyph-line', '--bone1', '甲骨字形描边（.glyph.glyphob 构件字形）'],
  ['--glyph-line', '--sheet',   '甲骨字形描边（纸面上的字形）'],
  ['--glyph-line', '--sheet-in','甲骨字形描边（内嵌托盘上的字形）'],
  ['--cinnabar',  '--bone',   '大号朱砂（.panel.end .score 58px）'],
  ['--glyph-line', '--card',  '甲骨字形描边（卡片上的甲骨形）'],
  ['--green',     '--bone',   '绿（.rv .g-ok）'],
  ['--red',       '--bone',   '朱砂别名（.rv .g-no 旧名）'],
  ['--edge',      '--bone',   '描边/分隔线（非文字，参考）'],
];

const AA = 4.5, AA_LARGE = 3.0;
let fails = 0;

for (const [tname, vars] of Object.entries(themes)) {
  if (!vars) { console.log('!! 找不到主题 ' + tname); continue; }
  console.log('\n===== 主题 ' + tname + ' =====');
  for (const [fgName, bgName, label] of pairs) {
    const fg = resolve(fgName, vars), bg = resolve(bgName, vars);
    if (!fg || !bg) { console.log('  ?  ' + label + '  (' + fgName + '/' + bgName + ') 无法解析'); continue; }
    const r = contrast(fg, bg);
    const tag = r >= AA ? 'AA ' : (r >= AA_LARGE ? '大字' : '不足');
    if (r < AA) fails++;
    console.log('  ' + tag + '  ' + r.toFixed(2).padStart(5) + '  ' +
      fgName.padEnd(10) + ' on ' + bgName.padEnd(9) + fg + ' / ' + bg + '   ' + label);
  }
}
console.log('\n低于 AA(4.5) 的组合数: ' + fails);
