// 校验部署包：index.html 里每个本地引用，按大小写精确逐级命中。
const fs = require('fs'), path = require('path');

const D = process.argv[2] || path.join(__dirname, '..');
const html = fs.readFileSync(path.join(D, 'index.html'), 'utf8');
// 注意：引用可能带缓存版本串（如 js/core/util.js?v=20261012-2）。
// 版本串不进文件路径，校验前必须剥掉，否则会把真实存在的文件报成 404。
// 这个假 404 从校验脚本诞生起就在（同一个提交里 index.html 已带 ?v=），
// 与 HANDOFF「现 18 个」的记录不符——实际是 16 真通过 + 2 假 404。
const refs = [...html.matchAll(/(?:src|href)="([^"]+)"/g)]
  .map(m => m[1]).filter(u => !/^(https?:|data:|#)/.test(u))
  .map(u => u.split('?')[0].split('#')[0]).filter(Boolean);

let bad = 0;
console.log('=== 逐项校验（大小写精确，模拟 Linux 上的 GitHub Pages）===');
for (const r of refs) {
  const parts = r.split('/');
  let cur = D, ok = true, missAt = '';
  for (const p of parts) {
    const list = fs.readdirSync(cur);
    if (!list.includes(p)) { ok = false; missAt = p; break; }
    cur = path.join(cur, p);
  }
  if (!ok) bad++;
  console.log((ok ? 'OK   ' : '404  ') + r + (ok ? '' : '   <- 大小写不符或缺失: ' + missAt));
}

console.log('');
console.log(bad ? bad + ' 项有问题' : '全部 ' + refs.length + ' 个引用可精确命中');
process.exit(bad ? 1 : 0);
