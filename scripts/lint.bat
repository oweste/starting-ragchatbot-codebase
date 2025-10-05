@echo off
REM Run linting checks

echo Running flake8...
uv run flake8 backend/

echo Linting complete!
