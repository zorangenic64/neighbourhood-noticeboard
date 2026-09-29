@echo off

call conda create -n neighbourhood python=3.12 -y

call conda activate neighbourhood

pip install flask flask-sqlalchemy flask-login waitress

echo.
echo Environment created successfully.
