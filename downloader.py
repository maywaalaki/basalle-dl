#!/usr/bin/env python3
"""
Media downloader module using yt-dlp.
Supports YouTube, TikTok, Instagram, Facebook, X/Twitter.
"""

import yt_dlp
import logging
import os
import uuid

logger = logging.getLogger(__name__)


def _sanitize_filename(title: str) -> str:
    """Create a safe filename from title."""
    safe = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
    return safe[:100].strip() or str(uuid.uuid4())[:8]


def download_media(url: str, download_type: str, output_path: str) -> str | None:
    """
    Download media from URL as video or audio.

    Args:
        url: Media URL
        download_type: 'video', 'video_small', or 'audio'
        output_path: Directory to save file

    Returns:
        Path to downloaded file or None on error
    """
    logger.info(f"Downloading {download_type} from {url}")

    # Generate unique filename to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    outtmpl = os.path.join(output_path, f'%(title).80s_{unique_id}.%(ext)s')

    # Common options
    ydl_opts = {
        'outtmpl': outtmpl,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 3,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        'postprocessors': [],
    }

    if download_type == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        })
    elif download_type == 'video_small':
        # Smaller video for when full quality exceeds 50MB
        ydl_opts['format'] = (
            'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/'
            'best[height<=480][ext=mp4]/'
            'bestvideo[height<=480]+bestaudio/'
            'best[height<=480]/'
            'best'
        )
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        })
    else:  # video
        ydl_opts['format'] = (
            'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/'
            'best[height<=720][ext=mp4]/'
            'bestvideo[height<=720]+bestaudio/'
            'best[height<=720]/'
            'best'
        )
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            if info_dict is None:
                logger.error(f"No info extracted for {url}")
                return None

            filename = ydl.prepare_filename(info_dict)

            if download_type == 'audio':
                # Find the actual mp3 file
                base, _ = os.path.splitext(filename)
                mp3_path = base + '.mp3'
                if os.path.exists(mp3_path):
                    return mp3_path

                # Search for any matching audio file
                base_name = os.path.basename(base)
                for f in os.listdir(output_path):
                    if unique_id in f and (f.endswith('.mp3') or f.endswith('.m4a') or f.endswith('.opus')):
                        return os.path.join(output_path, f)

                logger.error(f"Audio file not found for {url}")
                return None
            else:
                # For video, check mp4 conversion
                base, ext = os.path.splitext(filename)
                mp4_path = base + '.mp4'
                if os.path.exists(mp4_path):
                    return mp4_path
                if os.path.exists(filename):
                    return filename

                # Search for any matching video file
                for f in os.listdir(output_path):
                    if unique_id in f and (f.endswith('.mp4') or f.endswith('.mkv') or f.endswith('.webm')):
                        return os.path.join(output_path, f)

                logger.error(f"Video file not found for {url}")
                return None

    except yt_dlp.DownloadError as e:
        logger.error(f"Download error for {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {e}", exc_info=True)
        return None
