import yt_dlp
import os
from tqdm import tqdm

SEARCH_QUERY = 'Rhinecanthus aculeatus'
OUTPUT_DIR = '/Volumes/RFS/triggerfish_individual_id/Datasets/YouTube /raw_videos'  # change this
MAX_RESULTS = 20  
START_OFFSET = 20     
START_ID = 21  

os.makedirs(OUTPUT_DIR, exist_ok=True)

# first we collect video URLs from search
search_opts = {
    'quiet': True,
    'extract_flat': True,
    'extractor_args': {'youtube': {'js_runtimes': ['nodejs']}},
    'no_warnings': True,
}

with yt_dlp.YoutubeDL(search_opts) as ydl:
    result = ydl.extract_info(f'ytsearch{START_OFFSET + MAX_RESULTS}:{SEARCH_QUERY}', download=False)
    urls = [entry['url'] for entry in result['entries']][START_OFFSET:]

print(f"Found {len(urls)} videos\n")

# then we download each video with sequential ID
for i, url in enumerate(tqdm(urls, desc="Downloading videos"), start=START_ID):
    download_opts = {
        'outtmpl': os.path.join(OUTPUT_DIR, f'{i}.%(ext)s'),
        'format': 'bestvideo+bestaudio/best/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'extractor_args': {'youtube': {'js_runtimes': ['nodejs']}},
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(download_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        tqdm.write(f"Failed to download video {i} ({url}): {e}")

print("\nDone!")