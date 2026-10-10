@echo off

call conda create -n neighbourhood python=3.12 -y

call conda activate neighbourhood

python -m pip install -r requirements.txt

echo.
echo Environment created successfully.
