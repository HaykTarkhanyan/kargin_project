import streamlit as st
import pandas as pd
from urllib.parse import urlparse, parse_qs

def get_youtube_id(url):
    """Extract YouTube video ID from various YouTube URL formats"""
    try:
        # Handle NaN, None, and non-string values
        if pd.isna(url) or not isinstance(url, str):
            return None
            
        url = url.strip()
        if not url:
            return None
        
        parsed_url = urlparse(url)
        
        if parsed_url.hostname in ('youtu.be', 'www.youtu.be'):
            return parsed_url.path[1:]
        
        if parsed_url.hostname in ('youtube.com', 'www.youtube.com'):
            if parsed_url.path == '/watch':
                query_params = parse_qs(parsed_url.query)
                return query_params.get('v', [None])[0]
            elif parsed_url.path.startswith(('/embed/', '/v/')):
                return parsed_url.path.split('/')[2]
        
        return None
    except Exception:
        st.error(f"Error processing URL: {url}")
        return None

def show_random_videos():
    st.markdown("""
    <style>
        .main-title {
            color: #FF4B4B;
            font-size: 2.5em;
            font-weight: bold;
            text-align: center;
            margin-bottom: 1em;
        }
        .video-title {
            color: #FF725C;
            font-size: 1.1em;
            margin: 0.5em 0;
        }
        .location-caption {
            color: #4B4B4B;
            font-style: italic;
        }
        .stButton button {
            background-color: #FF4B4B;
            color: white;
            border-radius: 20px;
            padding: 0.5em 1em;
            border: none;
            transition: all 0.3s;
        }
        .stButton button:hover {
            background-color: #FF725C;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="main-title">🎬 Random Episodes Explorer</p>', unsafe_allow_html=True)
    
    if 'df' not in st.session_state:
        st.error("🚫 Please start from the home page to load the data.")
        return
    
    df = st.session_state['df']
    
    # Initialize session state for random videos if not exists
    if 'random_videos' not in st.session_state:
        st.session_state['random_videos'] = None
    
    # Add controls in the sidebar
    st.sidebar.markdown("### 🎮 Display Options")
    
    # Filter options
    location_filter = st.sidebar.multiselect(
        "📍 Filter by Location",
        options=['All'] + list(df['location'].dropna().unique()),
        default=['All']
    )
    
    # Apply filters to the dataframe
    filtered_df = df.copy()
    if location_filter and 'All' not in location_filter:
        filtered_df = filtered_df[filtered_df['location'].isin(location_filter)]
    
    # Button to load new random videos
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🎲 Load New Random Videos", type="primary"):
            # Get 9 random rows with animation
            with st.spinner("🔄 Loading new episodes..."):
                random_videos = filtered_df.sample(n=min(9, len(filtered_df)))
                st.session_state['random_videos'] = random_videos
                st.balloons()
    
    # If no videos loaded yet, load initial set
    if st.session_state['random_videos'] is None:
        with st.spinner("🎥 Loading initial episodes..."):
            videos = filtered_df.sample(n=min(9, len(filtered_df)))
            st.session_state['random_videos'] = videos
    else:
        videos = st.session_state['random_videos']
    
    # Create a 3x3 grid using columns
    for i in range(0, 9, 3):
        cols = st.columns(3)
        for j in range(3):
            idx = i + j
            if idx < len(videos):
                with cols[j]:
                    try:
                        video = videos.iloc[idx]
                        video_id = get_youtube_id(video['links'])
                        
                        if video_id:
                            with st.container():
                                # Display thumbnail with error handling
                                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                                try:
                                    st.image(thumbnail_url, use_container_width=True)
                                except Exception:
                                    st.warning("Thumbnail not available")
                                
                                # Show title and basic info
                                st.markdown(f'<p class="video-title">🎯 {video["titles"]}</p>', unsafe_allow_html=True)
                                st.markdown(f'<p class="location-caption">📍 {video["location"]}</p>', unsafe_allow_html=True)
                                
                                # Add play button with hover effect
                                if st.button("▶️ Watch Now", key=f"play_{video_id}"):
                                    with st.spinner("🎥 Loading video..."):
                                        st.video(video['links'])
                        else:
                            st.warning("🚫 Invalid YouTube URL")
                    except Exception:
                        st.error(f"❌ Error loading video {idx + 1}")
    
    # Add some spacing at the bottom with a decorative element
    st.markdown("<div style='text-align: center; margin: 2em 0;'>✨ • ✨ • ✨</div>", unsafe_allow_html=True)
    
    # Display statistics with a more attractive design
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Statistics")
    st.sidebar.markdown(f"""
    <div style='background-color: #f0f2f6; padding: 1em; border-radius: 10px;'>
        <p>📺 Total episodes: <strong>{len(filtered_df)}</strong></p>
        {f'🎯 Filtered episodes: <strong>{len(filtered_df)}</strong>' if 'All' not in location_filter else ''}
    </div>
    """, unsafe_allow_html=True)
    
    # Add flag counter at the bottom
    st.markdown("---")
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
    show_random_videos()
