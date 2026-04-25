import os
import logging
import pandas as pd
from pathlib import Path
from fuzzywuzzy import fuzz, process
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, skip loading .env file
    pass

# Set up logging
def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "telegram_bot.log"
    
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

class KarginTelegramBot:
    def __init__(self, token):
        self.token = token
        self.df = None
        self.load_data()
        
    def load_data(self):
        """Load the Kargin episodes data"""
        try:
            self.df = pd.read_csv("kargin_eng.csv")
            self.df['main_actors_count'] = pd.to_numeric(self.df['main_actors_count'], errors='coerce')
            self.df['main_actors_count'] = self.df['main_actors_count'].fillna(0)
            logging.info(f"Data loaded successfully. Found {len(self.df)} episodes.")
        except Exception as e:
            logging.error(f"Error loading data: {str(e)}")
            self.df = None

    def search_episodes(self, query, search_type="all", limit=5):
        """Search episodes based on query and type"""
        if self.df is None:
            return []
        
        results = []
        
        if search_type in ["all", "title"]:
            # Search in titles
            title_matches = process.extract(
                query, 
                self.df['titles'].fillna('').tolist(), 
                scorer=fuzz.partial_ratio,
                limit=limit
            )
            for match, score in title_matches:
                if score > 50:  # Minimum similarity threshold
                    idx = self.df[self.df['titles'] == match].index[0]
                    results.append({
                        'type': 'title',
                        'score': score,
                        'title': self.df.loc[idx, 'titles'],
                        'link': self.df.loc[idx, 'links'],
                        'actors': self.df.loc[idx, 'main_actors'],
                        'text': self.df.loc[idx, 'text'][:200] + "..." if len(str(self.df.loc[idx, 'text'])) > 200 else self.df.loc[idx, 'text']
                    })
        
        if search_type in ["all", "text"]:
            # Search in text content
            text_df = self.df[self.df['text'].notna()]
            text_matches = []
            
            for idx, row in text_df.iterrows():
                text = str(row['text']).lower()
                if query.lower() in text:
                    score = fuzz.partial_ratio(query.lower(), text)
                    text_matches.append((idx, score))
            
            # Sort by score and get top matches
            text_matches.sort(key=lambda x: x[1], reverse=True)
            for idx, score in text_matches[:limit]:
                if score > 40:
                    results.append({
                        'type': 'text',
                        'score': score,
                        'title': self.df.loc[idx, 'titles'],
                        'link': self.df.loc[idx, 'links'],
                        'actors': self.df.loc[idx, 'main_actors'],
                        'text': self.df.loc[idx, 'text'][:200] + "..." if len(str(self.df.loc[idx, 'text'])) > 200 else self.df.loc[idx, 'text']
                    })
        
        if search_type in ["all", "actors"]:
            # Search in actors
            actor_matches = process.extract(
                query,
                self.df['main_actors'].fillna('').tolist(),
                scorer=fuzz.partial_ratio,
                limit=limit
            )
            for match, score in actor_matches:
                if score > 60:
                    idx = self.df[self.df['main_actors'] == match].index[0]
                    results.append({
                        'type': 'actors',
                        'score': score,
                        'title': self.df.loc[idx, 'titles'],
                        'link': self.df.loc[idx, 'links'],
                        'actors': self.df.loc[idx, 'main_actors'],
                        'text': self.df.loc[idx, 'text'][:200] + "..." if len(str(self.df.loc[idx, 'text'])) > 200 else self.df.loc[idx, 'text']
                    })
        
        # Remove duplicates and sort by score
        unique_results = []
        seen_links = set()
        for result in results:
            if result['link'] not in seen_links:
                unique_results.append(result)
                seen_links.add(result['link'])
        
        return sorted(unique_results, key=lambda x: x['score'], reverse=True)[:limit]

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🎭 Welcome to Kargin Video Archive Bot! 🎭

I can help you search through Kargin episodes. Here's what you can do:

🔍 **Search Commands:**
• `/search <query>` - Search in all content
• `/search_title <query>` - Search in episode titles
• `/search_text <query>` - Search in episode dialogue
• `/search_actors <query>` - Search by actors

📊 **Other Commands:**
• `/stats` - Get archive statistics
• `/random` - Get a random episode
• `/help` - Show this help message

Just type your search query and I'll find relevant episodes for you!

Example: `/search Մկո` or `/search_actors Հայկո`
        """
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await self.start_command(update, context)

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        if self.df is None:
            await update.message.reply_text("❌ Data not available")
            return
        
        stats_message = f"""
📊 **Kargin Archive Statistics:**

📺 Total Episodes: {len(self.df)}
👥 Episodes with Actors Data: {len(self.df[self.df['main_actors'].notna()])}
📝 Episodes with Text: {len(self.df[self.df['text'].notna()])}
🎬 Most Active Actor: {self.df['main_actors'].mode()[0] if not self.df['main_actors'].mode().empty else 'N/A'}
        """
        await update.message.reply_text(stats_message)

    async def random_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /random command"""
        if self.df is None:
            await update.message.reply_text("❌ Data not available")
            return
        
        random_episode = self.df.sample(1).iloc[0]
        await self.send_episode_result(update, random_episode, "🎲 Random Episode")

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        await self.handle_search(update, context, "all")

    async def search_title_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search_title command"""
        await self.handle_search(update, context, "title")

    async def search_text_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search_text command"""
        await self.handle_search(update, context, "text")

    async def search_actors_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search_actors command"""
        await self.handle_search(update, context, "actors")

    async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_type="all"):
        """Handle search commands"""
        if not context.args:
            await update.message.reply_text(f"Please provide a search query. Example: /{update.message.text.split()[0][1:]} Մկո")
            return
        
        query = " ".join(context.args)
        logging.info(f"Search query: '{query}' type: {search_type}")
        
        if self.df is None:
            await update.message.reply_text("❌ Data not available")
            return
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        results = self.search_episodes(query, search_type)
        
        if not results:
            await update.message.reply_text(f"😕 No results found for '{query}'")
            return
        
        # Send results
        search_type_emoji = {
            "all": "🔍",
            "title": "🎬",
            "text": "💬",
            "actors": "👥"
        }
        
        header = f"{search_type_emoji.get(search_type, '🔍')} Found {len(results)} result(s) for '{query}':\n\n"
        await update.message.reply_text(header)
        
        for i, result in enumerate(results[:3], 1):  # Limit to 3 results to avoid spam
            await self.send_search_result(update, result, i)

    async def send_search_result(self, update: Update, result, index):
        """Send a formatted search result"""
        message = f"""
🎭 **Episode {index}:**
📺 {result['title']}
👥 Actors: {result['actors'] if result['actors'] else 'N/A'}
📝 Text: {result['text'] if result['text'] else 'N/A'}
⭐ Match Score: {result['score']}%
        """
        
        keyboard = [[InlineKeyboardButton("🔗 Watch Episode", url=result['link'])]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)

    async def send_episode_result(self, update: Update, episode, title):
        """Send a formatted episode result"""
        message = f"""
{title}

🎭 **{episode['titles']}**
👥 Actors: {episode['main_actors'] if pd.notna(episode['main_actors']) else 'N/A'}
📝 Text: {str(episode['text'])[:200] + '...' if pd.notna(episode['text']) and len(str(episode['text'])) > 200 else (episode['text'] if pd.notna(episode['text']) else 'N/A')}
        """
        
        keyboard = [[InlineKeyboardButton("🔗 Watch Episode", url=episode['links'])]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages as search queries"""
        query = update.message.text
        logging.info(f"Text search query: '{query}'")
        
        if self.df is None:
            await update.message.reply_text("❌ Data not available")
            return
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        results = self.search_episodes(query, "all", limit=3)
        
        if not results:
            await update.message.reply_text(f"😕 No results found for '{query}'\n\nTry using specific commands:\n• /search_title for titles\n• /search_text for dialogue\n• /search_actors for actors")
            return
        
        await update.message.reply_text(f"🔍 Found {len(results)} result(s) for '{query}':\n")
        
        for i, result in enumerate(results, 1):
            await self.send_search_result(update, result, i)

def main():
    """Start the bot"""
    setup_logging()
    
    # Get bot token from environment variable
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        print("Please set your Telegram bot token:")
        print("1. Create a bot with @BotFather on Telegram")
        print("2. Set the environment variable: set TELEGRAM_BOT_TOKEN=your_token_here")
        return
    
    # Create bot instance
    bot = KarginTelegramBot(token)
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("stats", bot.stats_command))
    application.add_handler(CommandHandler("random", bot.random_command))
    application.add_handler(CommandHandler("search", bot.search_command))
    application.add_handler(CommandHandler("search_title", bot.search_title_command))
    application.add_handler(CommandHandler("search_text", bot.search_text_command))
    application.add_handler(CommandHandler("search_actors", bot.search_actors_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text_message))
    
    logging.info("Starting Kargin Telegram Bot...")
    
    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
