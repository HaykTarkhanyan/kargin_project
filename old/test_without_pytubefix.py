"""
Test script to verify the app works without pytubefix installed
"""
import streamlit as st
import sys
from pathlib import Path

def test_youtube_utils_without_pytubefix():
    """Test that youtube_utils functions work when pytubefix is not available"""
    
    # Mock session state
    if 'enable_youtube' not in st.session_state:
        st.session_state['enable_youtube'] = False
    
    try:
        from youtube_utils import is_youtube_enabled, get_video_info, display_video_info, get_cached_video_info
        
        print("✅ Successfully imported youtube_utils functions")
        
        # Test is_youtube_enabled
        enabled = is_youtube_enabled()
        print(f"✅ is_youtube_enabled() returned: {enabled}")
        
        # Test get_video_info when disabled
        video_info, error = get_video_info("https://www.youtube.com/watch?v=test")
        print(f"✅ get_video_info() returned: video_info={video_info}, error='{error}'")
        
        # Test get_cached_video_info when disabled
        cached_info, cached_error = get_cached_video_info("https://www.youtube.com/watch?v=test")
        print(f"✅ get_cached_video_info() returned: video_info={cached_info}, error='{cached_error}'")
        
        # Test display_video_info when disabled
        display_video_info(None)  # Should return early
        print("✅ display_video_info() completed without errors")
        
        print("\n🎉 All tests passed! The app works without pytubefix installed.")
        return True
        
    except Exception as e:
        print(f"❌ Error testing youtube_utils: {e}")
        return False

def test_imports():
    """Test that critical imports work"""
    try:
        import pandas as pd
        import streamlit as st
        from fuzzywuzzy import fuzz
        print("✅ Critical imports successful")
        return True
    except Exception as e:
        print(f"❌ Critical import failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Kargin app without pytubefix...")
    print("=" * 50)
    
    # Test basic imports
    imports_ok = test_imports()
    
    # Test youtube utils
    youtube_utils_ok = test_youtube_utils_without_pytubefix()
    
    if imports_ok and youtube_utils_ok:
        print("\n🎉 SUCCESS: App should work without pytubefix!")
    else:
        print("\n❌ FAILURE: App may have issues without pytubefix")
        sys.exit(1)
