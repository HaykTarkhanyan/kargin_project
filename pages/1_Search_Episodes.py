import streamlit as st
from fuzzywuzzy import fuzz
import pandas as pd
import re
import logging
from urllib.parse import urlparse, parse_qs
from youtube_utils import get_cached_video_info, display_video_info

def get_youtube_id(url):
    """Extract YouTube video ID from various YouTube URL formats"""
    if not url:
        return None
    
    parsed_url = urlparse(url)
    
    if parsed_url.hostname in ('youtu.be', 'www.youtu.be'):
        return parsed_url.path[1:]
    
    if parsed_url.hostname in ('youtube.com', 'www.youtube.com'):
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query)['v'][0]
        elif parsed_url.path.startswith(('/embed/', '/v/')):
            return parsed_url.path.split('/')[2]
    
    return None

def highlight_text(text, search_text, is_fuzzy=False):
    if not text or not search_text:
        return ""
    
    text = str(text)
    search_text = str(search_text)
    
    if is_fuzzy:
        # For fuzzy matching, find the best matching substring
        text_lower = text.lower()
        search_lower = search_text.lower()
        
        # Find all substrings of length similar to search text
        search_len = len(search_text)
        best_ratio = 0
        best_substr = ""
        
        for i in range(len(text) - search_len + 1):
            substr = text[i:i + search_len]
            ratio = fuzz.ratio(substr.lower(), search_lower)
            if ratio > best_ratio:
                best_ratio = ratio
                best_substr = substr
        
        if best_substr:
            # Get context (up to 50 chars before and after)
            start = max(text.find(best_substr) - 50, 0)
            end = min(text.find(best_substr) + len(best_substr) + 50, len(text))
            context = text[start:end]
            
            # Bold the matching part
            highlighted = context.replace(best_substr, f"**{best_substr}**")
            return f"...{highlighted}..." if start > 0 or end < len(text) else highlighted
    else:
        # For exact matching, highlight all occurrences
        text_lower = text.lower()
        search_lower = search_text.lower()
        
        if search_lower in text_lower:
            # Find all occurrences with original case preserved
            matches = []
            last_end = 0
            pattern = re.compile(re.escape(search_text), re.IGNORECASE)
            
            for match in pattern.finditer(text):
                start, end = match.span()
                # Get context around match
                context_start = max(start - 50, last_end)
                context_end = min(end + 50, len(text))
                
                # Extract and highlight the match
                context = text[context_start:context_end]
                match_text = text[start:end]
                highlighted = context.replace(match_text, f"**{match_text}**")
                
                matches.append(f"...{highlighted}..." if context_start > 0 or context_end < len(text) else highlighted)
                last_end = end
            
            return "\n".join(matches)
    
    return ""

def show_search_page():
    st.title("Search Episodes")
    
    if 'df_processed' not in st.session_state:
        st.error("Please start from the home page to load the data.")
        return
        
    df = st.session_state['df_processed']
    
    # Text search
    search_text = st.text_input("Enter search text:")
    
    # Search type
    search_type = st.radio(
        "Search Type",
        ["Exact Match", "Simple Fuzzy", "Advanced Fuzzy"],
        horizontal=True,
        help="""
        Exact Match: Regular text search
        Simple Fuzzy: Automatic best match using all fuzzy algorithms
        Advanced Fuzzy: Manually select specific fuzzy algorithm
        """
    )
    
    # Fields to search in
    search_fields = st.multiselect(
        "Fields to search in",
        ["text", "text_common", "titles", "main_actors", "roles_names"],
        default=["text", "text_common"]
    )
    
    # Fuzzy search options
    if search_type in ["Simple Fuzzy", "Advanced Fuzzy"]:
        col1, col2 = st.columns(2)
        with col1:
            threshold = st.slider("Similarity Threshold", 50, 100, 70,
                                help="Minimum similarity score required for a match")
        
        if search_type == "Advanced Fuzzy":
            with col2:
                fuzzy_algorithm = st.radio(
                    "Fuzzy Algorithm",
                    ["All Methods", "Levenshtein", "Token Sort", "Token Set", "Partial Match"],
                    help="""
                    Levenshtein: Character-by-character similarity
                    Token Sort: Word order insensitive
                    Token Set: Word frequency based
                    Partial Match: Finds best matching substring
                    All Methods: Combines all algorithms
                    """
                )
    
    # Filters
    st.sidebar.header("Filters")
    
    # Location filter
    locations = ['All'] + list(df['location'].dropna().unique())
    selected_location = st.sidebar.selectbox("Select Location", locations)
    
    # Language filter
    languages = ['All'] + list(df['languages'].dropna().unique())
    selected_language = st.sidebar.selectbox("Select Language", languages)
    
    # Main actors count filter
    min_actors = int(df['main_actors_count'].min())
    max_actors = int(df['main_actors_count'].max())
    selected_actors = st.sidebar.slider("Number of Main Actors", min_actors, max_actors, (min_actors, max_actors))
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_location != 'All':
        filtered_df = filtered_df[filtered_df['location'] == selected_location]
    
    if selected_language != 'All':
        filtered_df = filtered_df[filtered_df['languages'] == selected_language]
    
    filtered_df = filtered_df[
        (filtered_df['main_actors_count'] >= selected_actors[0]) & 
        (filtered_df['main_actors_count'] <= selected_actors[1])
    ]
    
    if search_text:
        logging.info(f"Search initiated - Text: '{search_text}', Type: {search_type}, Fields: {search_fields}")
        logging.info(f"Filters - Location: {selected_location}, Language: {selected_language}, Actors: {selected_actors}")
        
        results = []
        
        for _, row in filtered_df.iterrows():
            max_similarity = 0
            best_field = ""
            best_algorithm = ""
            
            for field in search_fields:
                field_text = str(row[field]) if pd.notna(row[field]) else ""
                
                if search_type == "Exact Match":
                    if search_text.lower() in field_text.lower():
                        max_similarity = 100
                        best_field = field
                        best_algorithm = "Exact Match"
                        break
                        
                elif search_type == "Simple Fuzzy":
                    # Use all fuzzy methods just like "All Methods"
                    # Levenshtein distance
                    ratio = fuzz.ratio(search_text.lower(), field_text.lower())
                    if ratio > max_similarity:
                        max_similarity = ratio
                        best_field = field
                        best_algorithm = "Levenshtein"
                    
                    # Token Sort
                    token_sort = fuzz.token_sort_ratio(search_text.lower(), field_text.lower())
                    if token_sort > max_similarity:
                        max_similarity = token_sort
                        best_field = field
                        best_algorithm = "Token Sort"
                    
                    # Token Set
                    token_set = fuzz.token_set_ratio(search_text.lower(), field_text.lower())
                    if token_set > max_similarity:
                        max_similarity = token_set
                        best_field = field
                        best_algorithm = "Token Set"
                    
                    # Partial Match
                    partial = fuzz.partial_ratio(search_text.lower(), field_text.lower())
                    if partial > max_similarity:
                        max_similarity = partial
                        best_field = field
                        best_algorithm = "Partial Match"
                        
                else:  # Advanced Fuzzy
                    if fuzzy_algorithm in ["All Methods", "Levenshtein"]:
                        ratio = fuzz.ratio(search_text.lower(), field_text.lower())
                        if ratio > max_similarity:
                            max_similarity = ratio
                            best_field = field
                            best_algorithm = "Levenshtein"
                    
                    if fuzzy_algorithm in ["All Methods", "Token Sort"]:
                        token_sort = fuzz.token_sort_ratio(search_text.lower(), field_text.lower())
                        if token_sort > max_similarity:
                            max_similarity = token_sort
                            best_field = field
                            best_algorithm = "Token Sort"
                    
                    if fuzzy_algorithm in ["All Methods", "Token Set"]:
                        token_set = fuzz.token_set_ratio(search_text.lower(), field_text.lower())
                        if token_set > max_similarity:
                            max_similarity = token_set
                            best_field = field
                            best_algorithm = "Token Set"
                    
                    if fuzzy_algorithm in ["All Methods", "Partial Match"]:
                        partial = fuzz.partial_ratio(search_text.lower(), field_text.lower())
                        if partial > max_similarity:
                            max_similarity = partial
                            best_field = field
                            best_algorithm = "Partial Match"
            
            if (search_type == "Exact Match" and max_similarity == 100) or \
               (search_type in ["Simple Fuzzy", "Advanced Fuzzy"] and max_similarity >= threshold):
                results.append({
                    'row': row,
                    'similarity': max_similarity
                })
        
        # Sort results by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Display results
        if results:
            logging.info(f"Search completed - Found {len(results)} matches")
            st.subheader(f"Search Results ({len(results)} found)")
            for result in results:
                row = result['row']
                
                # Create columns for layout
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # Get YouTube video ID and create thumbnail
                    video_id = get_youtube_id(row['links'])
                    if video_id:
                        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                        try:
                            st.image(thumbnail_url, use_container_width=True)
                        except Exception:
                            st.warning("🎬 Thumbnail not available")

                        # Display match information with styling
                        score_color = "#00ff00" if result['similarity'] > 90 else "#ffbf00" if result['similarity'] > 70 else "#ff4b4b"
                        emoji = "🎯" if result['similarity'] > 90 else "👍" if result['similarity'] > 70 else "🔍"
                        
                        st.markdown(f"""
                        <div style='background-color: #f0f2f6; padding: 1em; border-radius: 10px; text-align: center; margin: 0.5em 0;'>
                            <div style='font-size: 1.2em; font-weight: bold;'>
                                <span style='color: {score_color};'>{result['similarity']}% {emoji}</span>
                            </div>
                            <div style='margin: 0.5em 0; font-size: 0.9em; color: #666;'>
                                Match Score
                            </div>
                            <div style='border-top: 1px solid #ddd; padding-top: 0.5em; margin-top: 0.5em; font-size: 0.8em;'>
                                <div>📍 Found in: {best_field}</div>
                                <div>🔍 Method: {best_algorithm}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        # Fetch and display video information
                        video_info, error = get_cached_video_info(row['links'])
                        if error:
                            st.warning(f"❌ Couldn't fetch video info: {error}")
                        elif video_info:
                            display_video_info(video_info)

                        # Add button to show/hide video
                        if st.button("▶️ Play Video", key=f"play_{video_id}"):
                            logging.info(f"Video played - ID: {video_id}, Title: {row['titles']}")
                            st.video(row['links'])
                
                with col2:
                    # Show Kargin title and metadata
                    st.markdown(f"### {row['titles']}")
                    st.write(f"⭐ Match Score: {result['similarity']}%")
                    st.write(f"📍 Location: {row['location']}")
                    st.write(f"👥 Main Actors: {row['main_actors']}")
                    
                    # Show matching text contexts for each field
                    for field in search_fields:
                        if pd.notna(row[field]):
                            highlighted = highlight_text(
                                row[field], 
                                search_text, 
                                is_fuzzy=(search_type == "Fuzzy Search")
                            )
                            if highlighted:
                                st.markdown(f"**Matched in {field}:**")
                                st.markdown(highlighted)
                
                if pd.notna(row['text_common']):
                    st.write(f"Common Expression: {row['text_common']}")
                st.write("---")
        else:
            logging.info(f"No matches found for search text: '{search_text}'")
            st.warning("No matches found")
    else:
        st.info("Enter some text to search for episodes")
    
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
    show_search_page()
