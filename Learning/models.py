from django.db import models
from django.contrib.auth.models import User
import re


def extract_youtube_video_id(url):
    """
    Extract YouTube video ID from various URL formats.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


class TrainingVideo(models.Model):
    title = models.CharField(max_length=255)
    youtube_url = models.URLField()  # Full YouTube URL
    youtube_video_id = models.CharField(max_length=50)  # Extracted ID for embedding
    rank = models.IntegerField(default=0, help_text="Lower rank numbers appear first. Default is 0.")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="training_videos_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="training_videos_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['rank', 'created_at']  # Order by rank first (ascending), then by creation date

    def save(self, *args, **kwargs):
        # Extract YouTube video ID from URL if not already set
        if self.youtube_url and not self.youtube_video_id:
            self.youtube_video_id = extract_youtube_video_id(self.youtube_url)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title}"
