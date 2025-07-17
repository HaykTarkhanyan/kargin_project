from pytubefix import YouTube
import streamlit as st
from datetime import datetime
import logging

def get_video_info(url):
    """
    Fetch video information from YouTube without using API.
    Returns a tuple (video_info, error_message).
    video_info is a dictionary containing video metadata if successful, None otherwise.
    error_message is a string containing error details if failed, None otherwise.
    """
    try:
        # Create YouTube object with retries
        for _ in range(3):  # Try up to 3 times
            try:
                yt = YouTube(url)
                break
            except Exception as e:
                if "unavailable" in str(e).lower():
                    return None, "Video is unavailable"
                logging.warning(f"Retry connecting to YouTube: {str(e)}")
                continue
        else:
            return None, "Failed to connect to YouTube after multiple attempts"
        
        # Get publish date and format it
        try:
            publish_date = yt.publish_date
            formatted_date = publish_date.strftime("%Y-%m-%d") if publish_date else "Not available"
        except Exception as e:
            logging.warning(f"Failed to get publish date: {str(e)}")
            formatted_date = "Not available"
        
        # Get duration in minutes and seconds
        try:
            duration_seconds = yt.length
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            duration = f"{minutes}:{seconds:02d}"
        except Exception as e:
            logging.warning(f"Failed to get duration: {str(e)}")
            duration = "Unknown"
        
        # Format view count with commas
        try:
            views = "{:,}".format(yt.views)
        except Exception as e:
            logging.warning(f"Failed to get view count: {str(e)}")
            views = "Unknown"
        
        # Get likes count
        try:
            likes = "{:,}".format(yt.initial_data['videoPrimaryInfoRenderer']['videoActions']['menuRenderer']['topLevelButtons'][0]['segmentedLikeDislikeButtonRenderer']['likeButton']['toggleButtonRenderer']['toggledText']['accessibility']['accessibilityData']['label'].split()[0])
        except Exception as e:
            logging.warning(f"Failed to get likes count: {str(e)}")
            likes = "Hidden"

        # Calculate days ago
        try:
            if publish_date:
                days_ago = (datetime.now() - publish_date).days
                days_ago_text = f"{days_ago} days ago"
            else:
                days_ago_text = "Unknown"
        except Exception as e:
            logging.warning(f"Failed to calculate days ago: {str(e)}")
            days_ago_text = "Unknown"

        # Collect video information with safe access
        video_info = {
            "title": getattr(yt, 'title', 'Unknown'),
            "views": views,
            "duration": duration,
            "publish_date": formatted_date,
            "days_ago": days_ago_text,
            "author": getattr(yt, 'author', 'Unknown'),
            "likes": likes,
            # "keywords": getattr(yt, 'keywords', []),
            "thumbnail_url": getattr(yt, 'thumbnail_url', None),
            "rating": round(yt.rating, 2) if hasattr(yt, 'rating') and yt.rating else None
        }
        
        return video_info, None
        
    except Exception as e:
        error_msg = str(e)
        if "unavailable" in error_msg.lower():
            error_msg = "Video is unavailable"
        elif "private" in error_msg.lower():
            error_msg = "This is a private video"
        logging.error(f"Error fetching video info: {error_msg}")
        return None, error_msg

def display_video_info(video_info):
    """
    Display video information in a nicely formatted Streamlit component
    """
    if not video_info:
        return
    
    # Add CSS styles
    st.markdown("""
    <style>
        .video-info {
            background-color: #f8f9fa;
            padding: 1em;
            border-radius: 10px;
            margin: 1em 0;
        }
        .video-stat {
            color: #666;
            font-size: 0.9em;
            margin: 0.2em 0;
        }
        .video-description {
            background-color: white;
            padding: 1em;
            border-radius: 5px;
            margin-top: 1em;
            font-size: 0.9em;
            max-height: 200px;
            overflow-y: auto;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Create rating and likes HTML
    rating_html = f'<div class="video-stat">⭐ Rating: {video_info.get("rating", "Not rated")}</div>' if video_info.get("rating") else ''
    
    # Create keywords HTML if keywords exist
    # keywords_html = ''
    # if video_info.get("keywords"):
    #     keywords_str = ", ".join(video_info.get("keywords", []))
    #     keywords_html = f'<h4>🏷️ Keywords</h4><div class="video-stat">{keywords_str}</div>'
    
    # Format publish date info
    publish_info = video_info.get('publish_date', 'Not available')
    
    # Combine all parts
    html = f"""
    <div class="video-info">
        <h4>📊 Video Statistics</h4>
        <div class="video-stat">👤 Author: {video_info.get('author', 'Unknown')}</div>
        <div class="video-stat">📅 Published: {publish_info}</div>
        <div class="video-stat">👁️ Views: {video_info.get('views', 'Unknown')}</div>
        <div class="video-stat">❤️ Likes: {video_info.get('likes', 'Hidden')}</div>
        <div class="video-stat">⏱️ Duration: {video_info.get('duration', 'Unknown')}</div>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)

def cache_video_info():
    """
    Initialize or get the video info cache from session state
    """
    if 'video_info_cache' not in st.session_state:
        st.session_state['video_info_cache'] = {}
    return st.session_state['video_info_cache']

def get_cached_video_info(url):
    """
    Get video info from cache or fetch it if not available
    """
    cache = cache_video_info()
    
    if url in cache:
        return cache[url], None
    
    video_info, error = get_video_info(url)
    if video_info:
        cache[url] = video_info
    
    return video_info, error
