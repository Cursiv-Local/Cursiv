@echo off
:: ============================================================
:: Cursiv — Quick build verification
:: Checks that Cursiv.exe exists and has correct structure.
:: Run from repo root:  scripts\verify_build.bat
:: ============================================================
setlocal

set "ROOT=%~dp0.."
set "DIST=%ROOT%\dist\Cursiv"

echo.
echo  Verifying Cursiv build...
echo.

:: Check exe exists
if not exist "%DIST%\Cursiv.exe" (
    echo  [FAIL] dist\Cursiv\Cursiv.exe not found.
    echo         Run scripts\build.bat first.
    exit /b 1
)

:: Check icons bundled
if not exist "%DIST%\_internal\launcher\resources\icons\cursiv.ico" (
    echo  [WARN] Icon not found in bundle — launcher may use default icon.
) else (
    echo  [OK]   Icons bundled.
)

:: Check cursiv_engine data bundled
if not exist "%DIST%\_internal\cursiv_engine" (
    echo  [WARN] cursiv_engine data not found in bundle.
) else (
    echo  [OK]   cursiv_engine bundled.
)

:: Report size
for /f "tokens=1" %%s in ('powershell -noprofile -command "$s=(Get-ChildItem \"%DIST%\" -Recurse -File | Measure-Object -Property Length -Sum).Sum; [math]::Round($s/1MB,0)"') do set SIZEMB=%%s
echo  [OK]   Cursiv.exe exists (%SIZEMB% MB total bundle).
echo.
echo  Build looks good. Run dist\Cursiv\Cursiv.exe to test.
echo.
