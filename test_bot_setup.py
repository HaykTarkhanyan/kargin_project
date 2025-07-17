#!/usr/bin/env python3
"""
Test script to validate Telegram bot setup
"""
import sys
import os

def test_imports():
    """Test if all required packages can be imported"""
    print("Testing package imports...")
    
    try:
        import pandas
        print("✓ pandas - OK")
    except ImportError as e:
        print(f"✗ pandas - FAILED: {e}")
        return False
    
    try:
        from fuzzywuzzy import fuzz, process
        print("✓ fuzzywuzzy - OK")
    except ImportError as e:
        print(f"✗ fuzzywuzzy - FAILED: {e}")
        return False
    
    try:
        from telegram import Update
        from telegram.ext import Application
        print("✓ python-telegram-bot - OK")
    except ImportError as e:
        print(f"✗ python-telegram-bot - FAILED: {e}")
        print("Please install with: pip install python-telegram-bot")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✓ python-dotenv - OK")
    except ImportError as e:
        print(f"✗ python-dotenv - FAILED: {e}")
        print("Please install with: pip install python-dotenv")
        return False
    
    return True

def test_data_file():
    """Test if the data file exists and can be loaded"""
    print("\nTesting data file...")
    
    if not os.path.exists("kargin_eng.csv"):
        print("✗ kargin_eng.csv not found in current directory")
        return False
    
    try:
        import pandas as pd
        df = pd.read_csv("kargin_eng.csv")
        print(f"✓ Data file loaded successfully - {len(df)} episodes found")
        return True
    except Exception as e:
        print(f"✗ Failed to load data file: {e}")
        return False

def test_bot_token():
    """Test if bot token is configured"""
    print("\nTesting bot token configuration...")
    
    # Try to load from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("✗ TELEGRAM_BOT_TOKEN not set")
        print("Please set your bot token:")
        print("1. Create a bot with @BotFather on Telegram")
        print("2. Set environment variable: set TELEGRAM_BOT_TOKEN=your_token")
        print("3. Or create .env file with: TELEGRAM_BOT_TOKEN=your_token")
        return False
    
    if len(token) < 40:
        print("✗ Bot token seems too short (should be ~45 characters)")
        return False
    
    print("✓ Bot token is configured")
    return True

def main():
    """Run all tests"""
    print("Kargin Telegram Bot - Setup Validation")
    print("=" * 40)
    
    all_tests_passed = True
    
    # Test imports
    if not test_imports():
        all_tests_passed = False
    
    # Test data file
    if not test_data_file():
        all_tests_passed = False
    
    # Test bot token
    if not test_bot_token():
        all_tests_passed = False
    
    print("\n" + "=" * 40)
    
    if all_tests_passed:
        print("🎉 All tests passed! Your bot is ready to run.")
        print("Run the bot with: python telegram_bot.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
