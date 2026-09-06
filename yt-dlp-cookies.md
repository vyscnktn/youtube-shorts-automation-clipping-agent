# For Chrome
yt-dlp --cookies-from-browser chrome "VIDEO_LINK"

# For Firefox
yt-dlp --cookies-from-browser firefox "VIDEO_LINK"

# For Brave
yt-dlp --cookies-from-browser brave "VIDEO_LINK"

# Download Cookies
yt-dlp --cookies cookies.txt "VIDEO_LINK"



# Basic Python Script


```python

import yt_dlp

ydl_opts = {
    # to pull from browser:
    'cookiesfrombrowser': ('chrome', ),
    
    # to use as a file:
    # 'cookiefile': 'cookies.txt',
    
    'format': 'best',
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download(['https://www.youtube.com/watch?v=...'])

```
