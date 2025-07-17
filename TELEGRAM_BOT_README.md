# Kargin Telegram Bot Setup Guide

This guide will help you set up and run the Kargin Telegram Bot that allows users to search through the Kargin video archive directly from Telegram.

## Prerequisites

1. **Python Environment**: Make sure you have Python 3.8+ installed
2. **Telegram Account**: You'll need a Telegram account to create a bot
3. **BotFather Access**: Access to Telegram's @BotFather

## Step 1: Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Start a conversation with BotFather by clicking "Start"
3. Send the command `/newbot`
4. Choose a name for your bot (e.g., "Kargin Archive Bot")
5. Choose a username for your bot (must end in 'bot', e.g., "kargin_archive_bot")
6. BotFather will give you a **bot token** - save this token securely!

## Step 2: Set Up Environment

### Option A: Using Command Prompt (Windows)
```cmd
set TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### Option B: Using PowerShell (Windows)
```powershell
$env:TELEGRAM_BOT_TOKEN="your_bot_token_here"
```

### Option C: Using .env file (Recommended)
1. Create a `.env` file in the project root
2. Add this line:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

## Step 3: Install Dependencies

```cmd
pip install -r requirements.txt
```

## Step 4: Run the Bot

### Quick Start (Windows):
```cmd
run_telegram_bot.bat
```

### Manual Start:
```cmd
python telegram_bot.py
```

## Bot Features

### Search Commands:
- `/search <query>` - Search in all content (titles, text, actors)
- `/search_title <query>` - Search specifically in episode titles
- `/search_text <query>` - Search in episode dialogue/text
- `/search_actors <query>` - Search by actor names

### Other Commands:
- `/start` - Welcome message and help
- `/help` - Show available commands
- `/stats` - Display archive statistics
- `/random` - Get a random episode

### Text Search:
Users can also send regular text messages (without commands) and the bot will search for relevant episodes.

## Example Usage

```
/search Մկո
/search_actors Հայկո
/search_title sketch 401
/random
```

## Bot Responses

The bot will respond with:
- Episode title
- Main actors
- Text excerpt (first 200 characters)
- Match score percentage
- Direct link to watch the episode

## Troubleshooting

### Bot doesn't respond:
1. Check that the bot token is correctly set
2. Verify the bot is running (check console for errors)
3. Make sure the CSV data file exists

### "Data not available" error:
- Ensure `kargin_eng.csv` is in the same directory as `telegram_bot.py`
- Check that the CSV file is not corrupted

### Import errors:
- Run `pip install -r requirements.txt` to install dependencies
- Make sure you're using the correct Python environment

## Security Notes

- Keep your bot token secret and never share it publicly
- Consider using environment variables or a .env file for the token
- The bot logs all interactions in `logs/telegram_bot.log`

## File Structure

```
Kargin_project/
├── telegram_bot.py          # Main bot code
├── kargin_eng.csv          # Episode data
├── requirements.txt        # Dependencies
├── run_telegram_bot.bat    # Quick start script
└── logs/
    └── telegram_bot.log    # Bot activity logs
```

## Customization

You can customize the bot by modifying `telegram_bot.py`:
- Change search algorithms in `search_episodes()`
- Modify response formats in `send_search_result()`
- Add new commands by creating new handler functions
- Adjust similarity thresholds for better/looser matching

## Support

If you encounter issues:
1. Check the logs in `logs/telegram_bot.log`
2. Verify your bot token with @BotFather
3. Ensure all dependencies are installed correctly
