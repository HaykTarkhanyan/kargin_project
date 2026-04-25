@echo off
echo Starting Kargin Telegram Bot...
echo.

REM Check if TELEGRAM_BOT_TOKEN is set
if "%TELEGRAM_BOT_TOKEN%"=="" (
    echo ERROR: TELEGRAM_BOT_TOKEN environment variable is not set!
    echo.
    echo To set up your Telegram bot:
    echo 1. Message @BotFather on Telegram
    echo 2. Create a new bot with /newbot
    echo 3. Get your bot token
    echo 4. Set the environment variable:
    echo    set TELEGRAM_BOT_TOKEN=your_token_here
    echo.
    echo Then run this script again.
    pause
    exit /b 1
)

REM Activate virtual environment if it exists
if exist "kargin\Scripts\activate.bat" (
    echo Activating virtual environment...
    call kargin\Scripts\activate.bat
)

REM Install/update dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Run the bot
echo.
echo Starting Telegram bot...
python telegram_bot.py

pause
