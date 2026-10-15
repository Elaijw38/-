# -*- coding: utf-8 -*-
"""通过 GitHub REST API 推送改动（Elaijw38/jiagugouciji）。

为什么不用 git push：这份工作副本是从仓库压缩包解开的，**没有 `.git`**；
而且本机代理对 git 的 push 返回 502。所以走 API 的 git 数据接口
（blob → tree → commit → 更新 ref），和此前几次部署同一套机制。

令牌从本机凭据管理器取，不落盘、不打印：

    GH_TOKEN=$(printf "protocol=https\\nhost=github.com\\n\\n" | \\
      GIT_TERMINAL_PROMPT=0 git credential fill 2>/dev/null | sed -n 's/^password=//p')

用法：
    GH_TOKEN=... python dev/_push_api.py --dry            # 只看清单，不提交
    GH_TOKEN=... python dev/_push_api.py --message-file msg.txt
    GH_TOKEN=... python dev/_push_api.py -m "提交说明"

判定"要不要推"用 git blob sha（sha1("blob <len>\\0" + content)），和 git 自身的
对象标识一致，所以"内容相同"就是真的相同，不受解包时间戳影响。
"""
import argparse
import base64
import hashlib
import io
import os
import sys

import requests

OWNER, REPO, BRANCH = "Elaijw38", "jiagugouciji", "main"
API = "https://api.github.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 临时产物目录：验证脚本的截图/日志/profile 都往这些地方丢，不属于仓库内容
SKIP_DIRS = {"_check", "_bak", "_edgeprof", "_docpages", "__pycache__", ".git"}

# 刻意不推的文件。
# deploy.ps1：与远端只差行尾符（远端 LF、本地 CRLF 是 Windows 解包带进来的）。
#             推上去等于把整个文件重写一遍，提交里全是没有意义的噪音。
#             `_eol_check` 那个文件里有逐字节的核验过程。
SKIP_FILES = {"deploy.ps1"}


def call(H, method, url, **kw):
    r = requests.request(method, url, headers=H, timeout=300, **kw)
    if r.status_code >= 300:
        raise SystemExit("HTTP %s %s\n%s" % (r.status_code, url, r.text[:600]))
    return r.json()


def blob_sha(data):
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def token():
    t = os.environ.get("GH_TOKEN") or ""
    if not t:
        raise SystemExit("没有 GH_TOKEN。先按文件头的办法从凭据管理器取一个。")
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只列清单，不产生提交")
    ap.add_argument("-m", "--message", default="", help="提交说明")
    ap.add_argument("--message-file", default="", help="从文件读提交说明（避免中文被 shell 转义）")
    ap.add_argument("--force", action="store_true", help="允许非快进更新 ref（一般不用）")
    a = ap.parse_args()

    msg = a.message
    if a.message_file:
        msg = io.open(a.message_file, encoding="utf-8").read()
    if not msg and not a.dry:
        raise SystemExit("提交说明不能为空：用 -m 或 --message-file。")

    H = {"Authorization": "Bearer " + token(), "Accept": "application/vnd.github+json"}

    ref = call(H, "GET", "%s/repos/%s/%s/git/ref/heads/%s" % (API, OWNER, REPO, BRANCH))
    base_commit = ref["object"]["sha"]
    base_tree = call(H, "GET", "%s/repos/%s/%s/git/commits/%s"
                     % (API, OWNER, REPO, base_commit))["tree"]["sha"]
    tree = call(H, "GET", "%s/repos/%s/%s/git/trees/%s?recursive=1"
                % (API, OWNER, REPO, base_tree))
    if tree.get("truncated"):
        raise SystemExit("远端树被截断了，不能拿它当基线比对。")
    remote = {e["path"]: e["sha"] for e in tree.get("tree", []) if e["type"] == "blob"}
    print("基线 commit: %s（远端 blob %d 个）" % (base_commit[:10], len(remote)))

    todo, skipped = [], []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if fn.endswith(".pyc"):
                continue
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            if rel in SKIP_FILES:
                skipped.append((rel, "仅行尾符差异，见文件头说明"))
                continue
            # 根目录下跑验证时生成的 _cdp_*.js 探针
            if "/" not in rel and fn.startswith("_cdp") and fn.endswith(".js"):
                skipped.append((rel, "临时探针产物"))
                continue
            try:
                data = open(p, "rb").read()
            except OSError as e:
                skipped.append((rel, "读不了：%s" % e))
                continue
            if remote.get(rel) != blob_sha(data):
                todo.append((rel, p, len(data)))

    todo.sort()
    new_cnt = sum(1 for t in todo if t[0] not in remote)
    print("\n待推送 %d 个文件，合计 %.1f MB（新增 %d / 修改 %d）"
          % (len(todo), sum(t[2] for t in todo) / 1048576.0, new_cnt, len(todo) - new_cnt))
    for rel, why in skipped:
        print("  跳过 %s（%s）" % (rel, why))
    if not todo:
        print("\n没有需要推的东西，远端已经是最新的。")
        return
    if a.dry:
        for rel, p, size in todo:
            print("  %-46s %9d B  %s" % (rel, size, "新增" if rel not in remote else "改"))
        print("\n--dry：没有产生任何提交。")
        return

    entries = []
    for i, (rel, p, size) in enumerate(todo, 1):
        content = base64.b64encode(open(p, "rb").read()).decode()
        sha = call(H, "POST", "%s/repos/%s/%s/git/blobs" % (API, OWNER, REPO),
                   json={"content": content, "encoding": "base64"})["sha"]
        entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": sha})
        if i % 20 == 0 or i == len(todo):
            print("  blob %d/%d" % (i, len(todo)))

    new_tree = call(H, "POST", "%s/repos/%s/%s/git/trees" % (API, OWNER, REPO),
                    json={"base_tree": base_tree, "tree": entries})["sha"]
    new_commit = call(H, "POST", "%s/repos/%s/%s/git/commits" % (API, OWNER, REPO),
                      json={"message": msg, "tree": new_tree,
                            "parents": [base_commit]})["sha"]
    call(H, "PATCH", "%s/repos/%s/%s/git/refs/heads/%s" % (API, OWNER, REPO, BRANCH),
         json={"sha": new_commit, "force": bool(a.force)})
    print("\n推送完成")
    print("  %s → %s" % (base_commit[:10], new_commit[:10]))
    print("  https://github.com/%s/%s/commit/%s" % (OWNER, REPO, new_commit))
    print("\nGitHub Pages 是异步构建的，别拿「提交成功」当「线上生效」。")
    print("用 dev/_live_check.py 盯线上真实内容。")


if __name__ == "__main__":
    main()
