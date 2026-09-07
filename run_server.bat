@echo off
echo Starting Subject Bank (Django + MongoDB GridFS)...
echo Local PC URL: http://127.0.0.1:8000/
echo Mobile Phone Wi-Fi URL: http://10.0.110.59:8000/
start http://127.0.0.1:8000/
.\venv\Scripts\python manage.py runserver 0.0.0.0:8000
pause
