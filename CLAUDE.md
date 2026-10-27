## Available Tools

### YouTube Transcript Extraction
Use `youtube-transcript-api` to pull raw text transcripts from YouTube videos. Save transcripts to `raw/video_transcripts/`.

```python
from youtube_transcript_api import YouTubeTranscriptApi
api = YouTubeTranscriptApi()
transcript = api.fetch('VIDEO_ID', languages=['en'])
for s in transcript.snippets:
    print(f'{int(s.start//60)}:{int(s.start%60):02d} {s.text}')
```

### YouTube Frame Capture (shot-scraper)
Use `shot-scraper` to capture specific video frames at timestamps. Parse timestamps from transcripts to identify key slides/diagrams, then capture the frames as PNGs.

```bash
shot-scraper "https://www.youtube.com/watch?v=VIDEO_ID&t=SECONDS" \
  -o output.png --width 1280 --height 720 --wait 3000 \
  --selector "video" \
  --javascript "const btn=document.querySelector('.ytp-large-play-button'); if(btn) btn.click();"
```

Use these together: transcript gives you timestamps of key diagrams/slides, shot-scraper captures the actual frames as PNGs for presentations and wiki pages.
