# Optional pytubefix Installation Guide

## Overview
The Kargin Video Archive app now supports running without pytubefix installed. This is useful when:
- You don't need YouTube features
- pytubefix installation fails on your system
- You want faster app startup times
- Network restrictions prevent YouTube access

## What Works Without pytubefix

### ✅ Core Features (Always Available)
- **Episode Search**: Full text search with fuzzy matching
- **Data Analysis**: All statistics and charts
- **Random Episode Selection**: Browse episodes randomly
- **CSV Data Display**: View all episode metadata
- **Filters**: Location, language, actor count filtering

### ❌ YouTube Features (Disabled Without pytubefix)
- Video thumbnails (replaced with custom placeholders)
- Video metadata fetching (views, likes, duration)
- Embedded video player (shows direct links instead)

## Installation Options

### Option 1: Core Only (No YouTube)
```bash
pip install -r requirements-core.txt
```

### Option 2: Full Installation
```bash
pip install -r requirements.txt
```

### Option 3: Interactive Installation
```bash
install_optional.bat
```

## App Behavior

### When pytubefix is NOT installed:
1. **Home Page**: Shows warning about missing pytubefix
2. **YouTube Toggle**: Disabled and grayed out
3. **Search Results**: Shows custom Kargin placeholders instead of thumbnails
4. **Video Links**: Direct YouTube links provided instead of embedded player
5. **Performance**: Faster loading since no YouTube API calls

### When pytubefix IS installed:
1. **Home Page**: YouTube toggle available
2. **Full Features**: All YouTube functionality works
3. **User Choice**: Can still disable YouTube features if needed

## Error Handling

The app gracefully handles missing pytubefix:
- No import errors or crashes
- Clear user messaging about missing features
- Fallback UI elements for disabled features
- Direct links still provided for video access

## Testing

Run the test to verify functionality without pytubefix:
```bash
python test_without_pytubefix.py
```

## Dynamic Import Implementation

The `youtube_utils.py` now uses dynamic imports:
```python
def _import_youtube():
    try:
        from pytubefix import YouTube
        return YouTube
    except ImportError:
        return None
```

This ensures pytubefix is only imported when actually needed and available.

## Benefits

1. **Flexible Deployment**: App works in minimal environments
2. **Faster Startup**: No YouTube imports when disabled
3. **Error Resilience**: No crashes from missing dependencies
4. **User Control**: Clear indication of feature availability
5. **Progressive Enhancement**: Core features always work, YouTube is bonus
