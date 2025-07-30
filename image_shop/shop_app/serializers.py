from rest_framework import serializers
from .models import Artwork, Artist

class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ['id', 'name']

class ArtworkSerializer(serializers.ModelSerializer):
    artist = ArtistSerializer(read_only=True)
    artist_id = serializers.PrimaryKeyRelatedField(
        queryset=Artist.objects.all(),
        source='artist',
        write_only=True
    )
    
    class Meta:
        model = Artwork
        fields = ['id', 'title', 'artist', 'artist_id', 'view_count']
        read_only_fields = ['view_count']