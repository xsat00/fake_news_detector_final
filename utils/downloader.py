import os
import yt_dlp

def download_video_from_youtube(url, save_dir="saved_videos"):
    """
    Download video (max 360p) + subtitles + thumbnail from YouTube.

    Args:
        url (str): YouTube video URL
        save_dir (str): Directory to save downloaded files

    Returns:
        tuple: (video_filepath, subtitle_filepath or None, thumbnail_filepath or None)
    """
    os.makedirs(save_dir, exist_ok=True)

    ydl_opts = {
        'format': 'bestvideo[height<=360]+bestaudio/best[height<=360]/best[height<=360]',
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join(save_dir, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'write_thumbnail': True,
        'postprocessors': [{'key': 'FFmpegMetadata'}],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        base_path = os.path.splitext(ydl.prepare_filename(info))[0]

        # Check subtitle path (prefer manual, fallback to automatic)
        subtitle_path = None
        for ext in [".en.vtt", ".en.srt"]:
            candidate = base_path + ext
            if os.path.exists(candidate):
                subtitle_path = candidate
                break

        # Check thumbnail path with common extensions
        thumbnail_path = None
        for ext in [".jpg", ".webp", ".png"]:
            candidate = base_path + ext
            if os.path.exists(candidate):
                thumbnail_path = candidate
                break

        return ydl.prepare_filename(info), subtitle_path, thumbnail_path


def download_audio_from_youtube(url, save_dir="saved_audios"):
    """
    Download audio from YouTube and convert to MP3.

    Args:
        url (str): YouTube video URL
        save_dir (str): Directory to save downloaded audio

    Returns:
        str or None: MP3 file path or None if failed
    """
    os.makedirs(save_dir, exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(save_dir, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        mp3_path = os.path.splitext(ydl.prepare_filename(info))[0] + ".mp3"
        if os.path.exists(mp3_path):
            return mp3_path
        return None