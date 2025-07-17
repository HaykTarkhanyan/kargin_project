import streamlit as st
import pandas as pd
import logging

def show_analysis_page():
    st.title("Kargin Dataset Analysis")
    
    if 'df_processed' not in st.session_state:
        st.error("Please start from the home page to load the data.")
        return
        
    df = st.session_state['df_processed']
    
    st.header("Dataset Overview")
    st.write(f"Total number of episodes: {len(df)}")
    
    # Basic statistics
    st.subheader("Basic Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Unique Locations", df['location'].nunique())
    with col2:
        st.metric("Unique Actors", df['main_actors'].nunique())
    with col3:
        avg_actors = df['main_actors_count'].mean()
        st.metric("Average Actors per Episode", f"{avg_actors:.1f}")
    
    # Location distribution
    st.subheader("Episode Locations")
    location_counts = df['location'].value_counts()
    st.bar_chart(location_counts)
    
    # Actor count distribution
    st.subheader("Number of Actors Distribution")
    fig_actors = pd.DataFrame(df['main_actors_count'].value_counts().sort_index()).reset_index()
    fig_actors.columns = ['Actor Count', 'Number of Episodes']
    st.bar_chart(data=fig_actors, x='Actor Count', y='Number of Episodes')
    
    # Language distribution
    st.subheader("Languages Used")
    language_counts = df['languages'].value_counts()
    st.bar_chart(language_counts)
    
    # Common expressions analysis
    st.subheader("Common Expressions Analysis")
    expressions_count = df['text_common'].notna().sum()
    st.write(f"Number of episodes with common expressions: {expressions_count}")
    
    # Sample episodes
    st.subheader("Sample Episodes")
    if st.checkbox("Show Random Sample of Episodes"):
        sample_size = st.slider("Sample size", 1, 10, 5)
        st.write(df[['titles', 'location', 'main_actors', 'main_actors_count']].sample(sample_size))
    
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
    show_analysis_page()
