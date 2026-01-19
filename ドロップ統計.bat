@echo off
echo ========================================
echo Grablu ドロップ統計ツールを起動中...
echo ========================================
echo.

REM 仮想環境を有効化してPythonスクリプトを実行
call .venv\Scripts\activate.bat
python drop_main.py

echo.
echo ========================================
echo 処理が完了しました
echo ========================================
echo.
pause
