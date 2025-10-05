@echo off
REM Run all quality checks

echo === Code Quality Checks ===
echo.

echo 1. Checking import sorting with isort...
uv run isort --check-only backend/
set ISORT_EXIT=%ERRORLEVEL%

echo.
echo 2. Checking code formatting with black...
uv run black --check backend/
set BLACK_EXIT=%ERRORLEVEL%

echo.
echo 3. Running linting with flake8...
uv run flake8 backend/
set FLAKE8_EXIT=%ERRORLEVEL%

echo.
echo === Results ===
if %ISORT_EXIT%==0 if %BLACK_EXIT%==0 if %FLAKE8_EXIT%==0 (
    echo [32m✓ All quality checks passed![0m
    exit /b 0
) else (
    echo [31m✗ Some quality checks failed:[0m
    if not %ISORT_EXIT%==0 echo   - isort found import sorting issues
    if not %BLACK_EXIT%==0 echo   - black found formatting issues
    if not %FLAKE8_EXIT%==0 echo   - flake8 found linting issues
    echo.
    echo Run 'scripts\format.bat' to fix formatting issues automatically.
    exit /b 1
)
