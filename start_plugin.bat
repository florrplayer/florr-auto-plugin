@echo off
cd /d C:\Users\intel\Downloads\florr-auto-pathing-main
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8
powershell -WindowStyle Hidden -Command "Start-Process py -ArgumentList '-3.12','main.py','desert' -WorkingDirectory 'C:\Users\intel\Downloads\florr-auto-pathing-main' -RedirectStandardOutput 'C:\Users\intel\Downloads\florr-auto-pathing-main\live_capture.log' -RedirectStandardError 'C:\Users\intel\Downloads\florr-auto-pathing-main\live_capture_err.log' -WindowStyle Hidden"
