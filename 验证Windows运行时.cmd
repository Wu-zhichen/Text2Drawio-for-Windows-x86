@echo off
setlocal
cd /d "%~dp0"
echo [1/4] Checking bundled Python...
runtime\python\python.exe --version || goto :failed
echo [2/4] Checking backend imports...
runtime\python\python.exe -c "import fastapi, uvicorn, pydantic, PIL, pypdf, openpyxl, docx, pptx; print('Backend imports: OK')" || goto :failed
echo [3/4] Checking manager executable...
if not exist "Text2Drawio Manager\Text2Drawio Manager.exe" goto :failed
echo [4/4] Checking draw.io executable...
if not exist "Text2Drawio draw.io\Text2Drawio draw.io.exe" goto :failed
echo.
echo All Windows runtime checks passed.
pause
exit /b 0
:failed
echo.
echo Validation failed. Please keep the extracted folder structure unchanged.
pause
exit /b 1
