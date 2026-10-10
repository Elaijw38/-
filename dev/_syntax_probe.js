// 逐文件语法探针：只编译不执行，定位“脚本解析即失败”这类整页白屏故障。
const fs = require('fs'), path = require('path'), vm = require('vm');

const ROOT = path.join(__dirname, '..');
const files = [
  'js/core/data.js', 'js/core/util.js', 'js/core/packs.js',
  'js/core/modes.js', 'js/core/shell.js',
  'js/modes/bone-build.js', 'js/core/build.js',
];

let bad = 0;
for (const f of files) {
  const p = path.join(ROOT, f);
  if (!fs.existsSync(p)) { console.log('缺失   ' + f); bad++; continue; }
  const src = fs.readFileSync(p, 'utf8');
  try {
    new vm.Script(src, { filename: f });
    console.log('OK     ' + f + '  (' + src.length + ' 字符)');
  } catch (e) {
    bad++;
    console.log('语法错误 ' + f + ' -> ' + e.message);
    const ln = (e.stack.match(/evalmachine[^:]*:(\d+)/) || [])[1];
    if (ln) {
      const lines = src.split('\n');
      const n = parseInt(ln, 10);
      for (let i = Math.max(0, n - 3); i < Math.min(lines.length, n + 2); i++) {
        console.log('   ' + (i + 1) + (i + 1 === n ? ' >> ' : '    ') + lines[i]);
      }
    }
  }
}

// 同时检查 index.html 里所有引用的本地资源是否存在
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const refs = [...html.matchAll(/(?:src|href)="([^"]+)"/g)]
  .map(m => m[1]).filter(u => !/^(https?:|data:|#)/.test(u));
console.log('\n=== index.html 本地引用 ===');
for (const r of refs) {
  const ok = fs.existsSync(path.join(ROOT, decodeURIComponent(r)));
  if (!ok) bad++;
  console.log((ok ? 'OK   ' : '缺失 ') + r);
}

console.log('\n结论: ' + (bad ? bad + ' 处问题' : '全部可解析，无缺失引用'));
