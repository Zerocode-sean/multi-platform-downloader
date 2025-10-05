<#
Purges any committed .venv (site-packages with embedded keys) from git history using git-filter-repo.
Run from repository root in PowerShell.
#>

Write-Host "=== Purging .venv from git history ===" -ForegroundColor Cyan
Write-Host "Ensure you have a backup of your repo before proceeding!" -ForegroundColor Yellow
Write-Host "==🐧🐧Made with love by Sean darkcoder mwenyewe😂😂👨‍💻 ==." -ForegroundColor Green

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Error "git not found"; exit 1 }

# 1. Ensure working tree clean
$changes = git status --porcelain
if ($changes) { Write-Error "Working tree not clean. Commit/stash first."; exit 1 }

# 2. Ensure .venv is ignored
if (-not (Select-String -Path .gitignore -Pattern '^\.venv/?$' -SimpleMatch -ErrorAction SilentlyContinue)) {
  Add-Content .gitignore "`n.venv/"
  git add .gitignore
  git commit -m "chore: ensure .venv ignored"
}

# 3. Remove cached .venv if present in current index
$tracked = git ls-files .venv 2>$null
if ($tracked) {
  git rm -r --cached .venv
  git commit -m "chore: remove tracked .venv"
}

# 4. Install git-filter-repo if missing
$gfr = (Get-Command git-filter-repo -ErrorAction SilentlyContinue)
if (-not $gfr) {
  Write-Host "Installing git-filter-repo via pip..." -ForegroundColor Yellow
  if (-not (Get-Command pip -ErrorAction SilentlyContinue)) { Write-Error "pip not found"; exit 1 }
  pip install git-filter-repo
  if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install git-filter-repo"; exit 1 }
}

# 5. Run filter to drop .venv from entire history
Write-Host "Rewriting history (removing .venv)..." -ForegroundColor Yellow
git filter-repo --path .venv --invert-paths --force

if ($LASTEXITCODE -ne 0) { Write-Error "git-filter-repo failed"; exit 1 }

# 6. Force push (ASK before pushing)
Write-Host "History rewritten. Review log (git log --oneline)." -ForegroundColor Green
Write-Host "Run: git push --force --all && git push --force --tags" -ForegroundColor Green

Write-Host "After remote update, fresh-clone and run secret scan again." -ForegroundColor Cyan
