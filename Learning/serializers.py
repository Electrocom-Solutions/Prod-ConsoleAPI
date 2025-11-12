from rest_framework import serializers
from .models import TrainingVideo, extract_youtube_video_id


class TrainingVideoListSerializer(serializers.ModelSerializer):
    """Serializer for listing training videos"""
    
    class Meta:
        model = TrainingVideo
        fields = [
            'id', 'title', 'youtube_video_id', 'rank', 'created_at'
        ]
        read_only_fields = ['created_at']


class TrainingVideoDetailSerializer(serializers.ModelSerializer):
    """Serializer for training video details"""
    
    class Meta:
        model = TrainingVideo
        fields = [
            'id', 'title', 'youtube_url', 'youtube_video_id', 'rank',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']


class TrainingVideoCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating training videos"""
    
    class Meta:
        model = TrainingVideo
        fields = [
            'id', 'title', 'youtube_url', 'youtube_video_id', 'rank'
        ]
        read_only_fields = ['id', 'youtube_video_id']
    
    def validate_youtube_url(self, value):
        """Validate YouTube URL and extract video ID"""
        video_id = extract_youtube_video_id(value)
        if not video_id:
            raise serializers.ValidationError(
                "Invalid YouTube URL. Please provide a valid YouTube video URL."
            )
        return value
    
    def create(self, validated_data):
        """Create training video with extracted video ID"""
        youtube_url = validated_data.get('youtube_url')
        video_id = extract_youtube_video_id(youtube_url)
        validated_data['youtube_video_id'] = video_id
        
        user = self.context['request'].user
        validated_data['created_by'] = user if user.is_authenticated else None
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update training video with extracted video ID if URL changed"""
        youtube_url = validated_data.get('youtube_url', instance.youtube_url)
        if youtube_url != instance.youtube_url:
            video_id = extract_youtube_video_id(youtube_url)
            validated_data['youtube_video_id'] = video_id
        
        user = self.context['request'].user
        validated_data['updated_by'] = user if user.is_authenticated else None
        return super().update(instance, validated_data)

