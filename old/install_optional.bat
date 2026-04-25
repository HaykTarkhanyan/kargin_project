@echo off
echo Kargin Project - Optional Dependencies Installer
echo ================================================
echo.

echo Installing core dependencies...
pip install streamlit pandas fuzzywuzzy python-Levenshtein python-dateutil

echo.
echo Core dependencies installed!
echo.

set /p install_youtube="Do you want to install YouTube features (pytubefix)? (y/n): "
if /i "%install_youtube%"=="y" (
    echo Installing YouTube dependencies...
    pip install pytubefix
    echo YouTube features will be available!
) else (
    echo Skipping YouTube dependencies...
    echo YouTube features will be disabled.
)

echo.
set /p install_telegram="Do you want to install Telegram bot features? (y/n): "
if /i "%install_telegram%"=="y" (
    echo Installing Telegram bot dependencies...
    pip install python-telegram-bot python-dotenv
    echo Telegram bot features will be available!
) else (
    echo Skipping Telegram bot dependencies...
    echo Telegram bot will not be available.
)

echo.
echo Installation complete!
echo.
echo You can now run the app with: streamlit run Home.py
echo.
pause
