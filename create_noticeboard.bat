@echo off
set PROJECT_ROOT=C:\zoran-um890pro\projects\neighbourhood_noticeboard

echo Creating project structure...

mkdir "%PROJECT_ROOT%"
mkdir "%PROJECT_ROOT%\instance"

mkdir "%PROJECT_ROOT%\static"
mkdir "%PROJECT_ROOT%\static\css"
mkdir "%PROJECT_ROOT%\static\js"
mkdir "%PROJECT_ROOT%\static\images"

mkdir "%PROJECT_ROOT%\templates"

mkdir "%PROJECT_ROOT%\models"

echo Creating starter files...

type nul > "%PROJECT_ROOT%\app.py"
type nul > "%PROJECT_ROOT%\config.py"
type nul > "%PROJECT_ROOT%\requirements.txt"

type nul > "%PROJECT_ROOT%\templates\base.html"
type nul > "%PROJECT_ROOT%\templates\index.html"
type nul > "%PROJECT_ROOT%\templates\login.html"
type nul > "%PROJECT_ROOT%\templates\register.html"
type nul > "%PROJECT_ROOT%\templates\create_post.html"

type nul > "%PROJECT_ROOT%\models\models.py"

echo.
echo Project created at:
echo %PROJECT_ROOT%
echo.
pause
