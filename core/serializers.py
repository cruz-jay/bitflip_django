from rest_framework import serializers
from .models import StockWatchlist, SentimentAnalysis

class StockWatchlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockWatchlist
        fields = ['id', 'user', 'symbol', 'added_at']
        read_only_fields = ['id', 'user', 'added_at']

class SentimentAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = SentimentAnalysis
        fields = ['id', 'user', 'ticker', 'headlines', 'sentiment_score', 'sentiment_label', 'analyzed_at']
        read_only_fields = ['id', 'user', 'analyzed_at']
