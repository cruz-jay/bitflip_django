
from django.db import models
from django.conf import settings

class StockWatchlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watchlist')
    symbol = models.CharField(max_length=10)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.symbol}"
    
class SentimentAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sentiments')
    ticker = models.CharField(max_length=10)
    headlines = models.JSONField()  # Stores a list of 5 headlines
    sentiment_score = models.FloatField()
    sentiment_label = models.CharField(max_length=20)
    analyzed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.ticker} - {self.sentiment_label}"
