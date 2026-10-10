# ============================================================
#  字趣 · 一键部署
#  用法：右键本文件 → 使用 PowerShell 运行
#        或在本目录执行：  powershell -ExecutionPolicy Bypass -File deploy.ps1
#
#  它会：把当前改动提交，然后推送到 GitHub。
#  推送成功后等 1~2 分钟，刷新 https://elaijw38.github.io/-/
# ============================================================
$ErrorActionPreference = 'Continue'
$repo = $PSScriptRoot

# git 可能不在 PATH（安装后需要重开窗口），这里自己找
$git = 'C:\Program Files\Git\cmd\git.exe'
if (-not (Test-Path $git)) {
    $cmd = Get-Command git -ErrorAction SilentlyContinue
    if ($cmd) { $git = $cmd.Source } else {
        Write-Host '找不到 git，请先安装：winget install --id Git.Git -e' -ForegroundColor Red
        Read-Host '按回车退出'; exit 1
    }
}

function Step($msg) { Write-Host ''; Write-Host ('==> ' + $msg) -ForegroundColor Cyan }
function Ok($msg)   { Write-Host ('    ' + $msg) -ForegroundColor Green }
function Warn($msg) { Write-Host ('    ' + $msg) -ForegroundColor Yellow }

Write-Host '============================================' -ForegroundColor DarkGray
Write-Host '  字趣 · 部署到 GitHub Pages' -ForegroundColor White
Write-Host '============================================' -ForegroundColor DarkGray

# 别让 git 因为要密码而挂住
$env:GIT_TERMINAL_PROMPT = '0'

# ---------- 1. 提交本地改动 ----------
Step '检查并提交本地改动'
$changes = & $git -C $repo status --porcelain
if ($changes) {
    Write-Host '    待提交的文件：' -ForegroundColor Gray
    $changes | ForEach-Object { Write-Host ('      ' + $_) -ForegroundColor Gray }
    & $git -C $repo add -A | Out-Null
    $msg = '更新：' + (Get-Date -Format 'yyyy-MM-dd HH:mm')
    & $git -C $repo commit -q -m $msg
    Ok ('已提交：' + $msg)
} else {
    Ok '没有新改动，跳过提交'
}

# ---------- 2. 推送 ----------
Step '推送到 GitHub'
$push = & $git -C $repo push origin main 2>&1
$code = $LASTEXITCODE

if ($code -ne 0) {
    $text = ($push | Out-String)
    if ($text -match 'rejected|non-fast-forward|fetch first|behind') {
        Warn '远端有本地没有的提交（之前网页上传留下的历史），改用强制覆盖'
        Write-Host '    这会把远端换成你本地的完整版本，线上内容以本地为准。' -ForegroundColor Gray
        $ans = Read-Host '    继续强制推送？(y/N)'
        if ($ans -eq 'y' -or $ans -eq 'Y') {
            $push = & $git -C $repo push --force origin main 2>&1
            $code = $LASTEXITCODE
        } else {
            Warn '已取消'
            Read-Host '按回车退出'; exit 1
        }
    }
}

if ($code -eq 0) {
    Write-Host ''
    Ok '推送成功！'
    Write-Host ''
    Write-Host '  等 1~2 分钟，GitHub Pages 会自动重新构建，然后刷新：' -ForegroundColor White
    Write-Host '    https://elaijw38.github.io/-/' -ForegroundColor White
    Write-Host ''
    Write-Host '  想确认资源都在，访问这个地址看有没有 CSS 文本：' -ForegroundColor Gray
    Write-Host '    https://elaijw38.github.io/-/css/theme.css' -ForegroundColor Gray
} else {
    Write-Host ''
    Write-Host '  推送失败，原始信息：' -ForegroundColor Red
    $push | ForEach-Object { Write-Host ('    ' + $_) -ForegroundColor Red }
    Write-Host ''
    Write-Host '  常见原因：' -ForegroundColor Yellow
    Write-Host '    · 要输密码：这里必须填 Personal Access Token（ghp_...），不是登录密码' -ForegroundColor Yellow
    Write-Host '    · 网络：github.com 连不上，检查代理/加速器是否在运行' -ForegroundColor Yellow
}
Write-Host ''
Read-Host '按回车退出'
