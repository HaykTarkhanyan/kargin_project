import streamlit as st
from pathlib import Path
import pandas as pd
import logging

# Set up logging
def setup_logging():
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Use a single log file
    log_file = log_dir / "kargin_search.log"
    
    # Set up logging format
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Configure logging to write to both file and console
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logging.info("Logging initialized")

def main():
    setup_logging()
    st.title("Kargin Video Archive")
    
    # Load the data
    try:
        df = pd.read_csv("kargin_eng.csv")
        logging.info(f"Data loaded successfully. Found {len(df)} episodes.")
        
        # Store the dataframe in session state so it can be accessed by other pages
        st.session_state['df'] = df
        
        # Convert main_actors_count to numeric and store in session state
        df['main_actors_count'] = pd.to_numeric(df['main_actors_count'], errors='coerce')
        df['main_actors_count'] = df['main_actors_count'].fillna(0)
        st.session_state['df_processed'] = df
        
    except Exception as e:
        logging.error(f"Error loading data: {str(e)}")
        st.error("Error loading data. Please check if the CSV file exists.")
        return
    
    # Settings section
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        
        # YouTube functionality toggle
        enable_youtube = st.checkbox(
            "🎥 Enable YouTube features",
            value=st.session_state.get('enable_youtube', True),
            help="Disable this if YouTube video fetching is failing or slow"
        )
        st.session_state['enable_youtube'] = enable_youtube
        
        if not enable_youtube:
            st.info("🚫 YouTube features disabled")
            st.caption("• Video thumbnails\n• Video information\n• Embedded video player")
        else:
            st.success("✅ YouTube features enabled")
        
        st.markdown("---")
    
    st.write("""
    Welcome to the Kargin Video Archive! This application allows you to:
    
    1. 🔍 Search through episodes (Search Episodes page)
    2. 📊 View dataset analytics (Data Analysis page)
    3. 🎲 Explore random episodes (Random Videos page)
    4. ℹ️ View additional information (Info page)
    
    Use the sidebar to navigate between pages.
    """)
    
    # Add some spacing at the bottom
    st.markdown("<div style='text-align: center; margin: 2em 0;'>✨ • ✨ • ✨</div>", unsafe_allow_html=True)
    
    # Add flag counter at the bottom
    st.markdown("""
    <div style="text-align: center; margin: 2em 0; padding: 1em; background-color: #f8f9fa; border-radius: 10px;">
        <p style="color: #666; margin-bottom: 1em;">👥 Visitor Statistics</p>
        <a href="https://info.flagcounter.com/Wa1D">
            <img src="https://s01.flagcounter.com/count2/Wa1D/bg_FFFFFF/txt_000000/border_CCCCCC/columns_2/maxflags_10/viewers_0/labels_0/pageviews_0/flags_0/percent_0/" 
                 alt="Flag Counter" 
                 style="border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-radius: 5px;">
        </a>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
