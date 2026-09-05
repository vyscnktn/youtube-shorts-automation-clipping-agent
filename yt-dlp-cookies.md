# Chrome için
yt-dlp --cookies-from-browser chrome "VIDEO_LINKI"

# Firefox için
yt-dlp --cookies-from-browser firefox "VIDEO_LINKI"

# Brave için
yt-dlp --cookies-from-browser brave "VIDEO_LINKI"


yt-dlp --cookies cookies.txt "VIDEO_LINKI"




import yt_dlp

ydl_opts = {
    # Tarayıcıdan doğrudan çekmek için:
    'cookiesfrombrowser': ('chrome', ),
    
    # VEYA dosya kullanmak için:
    # 'cookiefile': 'cookies.txt',
    
    'format': 'best',
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download(['https://www.youtube.com/watch?v=...'])
