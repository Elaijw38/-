# -*- coding: utf-8 -*-
"""安全清理：只关掉「本项目自查用的无头 Edge」，绝不碰用户正在用的浏览器。

用法：
  python dev/_cleanup_edge.py            # 演练（只列出，不杀）
  python dev/_cleanup_edge.py --kill     # 真关

判定依据（缺一不可）：
  1) 命令行里含 --headless           —— 只处理无头实例
  2) 命令行里的 --user-data-dir 指向本项目的 _check/ 目录 —— 只处理自己的实例

为什么不按「进程名 + 启动时间」过滤：
  曾用 Get-Process msedge | Where StartTime -gt ... | Stop-Process -Force 清理，
  结果把用户当时正在用的浏览器一起强杀了（无头实例恰好在同一时间窗内启动）。
  时间窗无法区分「谁启动的」，必须看命令行里的 profile 路径。

补充：headless 跑完通常会自行退出，多数情况下压根不需要清理。
"""
import os, subprocess, sys

PROJECT = r"C:\DSH\字趣"
OUR_PROFILES = [os.path.join(PROJECT, "_check")]

PS = (
    "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
    "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
)


def main():
    kill = "--kill" in sys.argv
    raw = subprocess.run(["powershell", "-NoProfile", "-Command", PS],
                         capture_output=True, text=True, encoding="utf-8",
                         errors="replace")
    out = (raw.stdout or "").strip()
    if not out:
        print("没有 msedge 进程（或无法读取命令行）")
        return
    import json
    try:
        procs = json.loads(out)
    except Exception:
        print("无法解析进程列表")
        return
    if isinstance(procs, dict):
        procs = [procs]

    mine, others = [], []
    for p in procs:
        cl = p.get("CommandLine") or ""
        pid = p.get("ProcessId")
        is_headless = "--headless" in cl
        is_ours = any(("--user-data-dir=" + d) in cl or ("--user-data-dir=" + d.replace("\\", "/")) in cl
                      for d in OUR_PROFILES)
        if is_headless and is_ours:
            mine.append((pid, cl))
        else:
            others.append((pid, is_headless))

    print("=== 本项目无头实例（可安全关闭）===")
    if not mine:
        print("  无")
    for pid, cl in mine:
        tag = ""
        for d in OUR_PROFILES:
            if d in cl:
                tag = d
        print("  PID %-7s profile=%s" % (pid, tag))
    print("")
    print("=== 其它 Edge 进程（一律不动）===")
    print("  共 %d 个（含用户浏览器及其子进程）" % len(others))
    head = [x for x in others if not x[1]]
    print("  其中非无头（用户浏览器）%d 个" % len(head))

    if not mine:
        print("\n无需清理（headless 通常跑完自行退出）")
        return
    if not kill:
        print("\n这是演练模式，未关闭任何进程。要真关请加 --kill")
        return
    for pid, _ in mine:
        r = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, text=True, errors="replace")
        print("  taskkill PID %s → %s" % (pid, "已关闭" if r.returncode == 0 else "失败"))


if __name__ == "__main__":
    main()
