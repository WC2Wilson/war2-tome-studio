@echo off
cd /d "%~dp0"
py tome_workbench.py
if errorlevel 1 pause
