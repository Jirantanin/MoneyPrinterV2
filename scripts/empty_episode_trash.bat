@echo off
rem Permanently deletes .mp\_trash (files staged by scripts\episode_storage.py). Run it yourself; Claude never does.
setlocal
cd /d "%~dp0.."
if not exist ".mp\_trash" (
  echo .mp\_trash is empty. Nothing to delete.
  exit /b 0
)
for /f %%S in ('powershell -NoProfile -Command "[math]::Round(((Get-ChildItem '.mp\_trash' -Recurse -File -Force | Measure-Object Length -Sum).Sum)/1GB,2)"') do set SIZE=%%S
echo .mp\_trash holds %SIZE% GB:
dir /b ".mp\_trash"
choice /c YN /m "Delete it permanently"
if errorlevel 2 (
  echo Kept.
  exit /b 0
)
rmdir /s /q ".mp\_trash"
echo Deleted.
