@echo off
echo Kargin Telegram Bot Installation and Setup
echo ==========================================
echo.

echo Step 1: Installing required packages...
pip install python-telegram-bot python-dotenv pandas fuzzywuzzy python-Levenshtein

echo.
echo Step 2: Checking if bot token is set...
if "%TELEGRAM_BOT_TOKEN%"=="" (
    echo.
    echo WARNING: TELEGRAM_BOT_TOKEN environment variable is not set!
    echo.
    echo To create and set up your Telegram bot:
    echo 1. Open Telegram and message @BotFather
    echo 2. Send /newbot command
    echo 3. Follow the instructions to create your bot
    echo 4. Copy the token you receive
    echo 5. Run this command: set TELEGRAM_BOT_TOKEN=your_token_here
    echo 6. Then run this script again
    echo.
    echo Alternatively, create a .env file with:
    echo TELEGRAM_BOT_TOKEN=your_token_here
    echo.
    pause
    exit /b 1
)

echo.
echo Step 3: Starting the bot...
python telegram_bot.py

echo.
echo Bot stopped. Press any key to exit.
pause
