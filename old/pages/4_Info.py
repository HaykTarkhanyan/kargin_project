import streamlit as st

def show_info():
    st.markdown("""
    <style>
        .main-title {
            color: #FF4B4B;
            font-size: 2.5em;
            font-weight: bold;
            text-align: center;
            margin-bottom: 1em;
        }
        .section-title {
            color: #FF725C;
            font-size: 1.8em;
            margin: 1em 0;
            padding-left: 10px;
            border-left: 5px solid #FF4B4B;
        }
        .quiz-link {
            display: block;
            margin: 1em 0;
            padding: 1em;
            background-color: #f0f2f6;
            border-radius: 10px;
            text-decoration: none;
            color: #4B4B4B;
            transition: all 0.3s;
        }
        .quiz-link:hover {
            background-color: #FF725C;
            color: white;
            transform: translateX(10px);
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="main-title">📚 Հղումներ</p>', unsafe_allow_html=True)
    
    # Quiz section
    st.markdown('<p class="section-title">✍️ Թեստեր</p>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="padding: 1em;">
        <a href="https://docs.google.com/forms/d/e/1FAIpQLSd99rjjFwKas8vIiVTdfkXuIYJblKN2qct-e05BztBMiT9M5Q/viewform" class="quiz-link">
            📝 Թեստ 1
        </a>
        <a href="https://docs.google.com/forms/d/e/1FAIpQLSeXV2r44kmyRNtMkaBxshS86ZHSVP_9Hft_E26Pkug3-ZhnNg/viewform" class="quiz-link">
            📝 Թեստ 2
        </a>
        <a href="https://docs.google.com/forms/d/e/1FAIpQLSfKV-wC1fh043B3UffO1qgLAITHXrRyutlrquZQMu7DIKtsHw/viewform" class="quiz-link">
            📝 Թեստ 3
        </a>
        <a href="https://docs.google.com/forms/d/e/1FAIpQLSe_3NBgJwXichYb1b9dyyzye-8MWgcyJNKYTSCdVbYDlhM8aA/viewform" class="quiz-link">
            📝 Թեստ 4
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    # Music section
    st.markdown('<p class="section-title">🎵 Երաժշտություն</p>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="padding: 1em; background-color: #f0f2f6; border-radius: 10px; margin: 1em 0;">
        <a href="https://www.youtube.com/playlist?list=PL8sh2VJuXs-t-FQZ4OkeQdBCFqwJWCNQP" 
           style="text-decoration: none; color: #FF4B4B; font-size: 1.2em;">
            🎼 Կարգին երգերի փլեյլիստ
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    # Add embedded playlist with improved styling
    st.markdown('<p class="section-title" style="font-size: 1.4em;">🎬 Փլեյլիստի նախադիտում</p>', unsafe_allow_html=True)
    
    playlist_embed = """
        <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <iframe 
                style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" 
                src="https://www.youtube.com/embed/videoseries?list=PL8sh2VJuXs-t-FQZ4OkeQdBCFqwJWCNQP" 
                frameborder="0" 
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen>
            </iframe>
        </div>
    """
    st.components.v1.html(playlist_embed, height=315)
    
    # Add some spacing
    st.markdown("<br><br>", unsafe_allow_html=True)
    
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
    show_info()
