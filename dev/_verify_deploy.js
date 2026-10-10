// 校验部署包：index.html 里每个本地引用，按大小写精确逐级命中。
const fs = require('fs'), path = require('path');

const D = process.argv[2] || path.join(__dirname, '..');
const html = fs.readFileSync(path.join(D, 'index.html'), 'utf8');
const refs = [...html.matchAll(/(?:src|href)="([^"]+)"/g)]
  .map(m => m[1]).filter(u => !/^(https?:|data:|#)/.test(u));

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
