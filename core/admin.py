from django.contrib import admin
from .models import StockWatchlist, SentimentAnalysis

@admin.register(StockWatchlist)
class StockWatchlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'symbol', 'added_at')
    list_filter = ('added_at', 'symbol')
    search_fields = ('user__username', 'symbol')
    readonly_fields = ('added_at',)

@admin.register(SentimentAnalysis)
class SentimentAnalysisAdmin(admin.ModelAdmin):
    list_display = ('user', 'ticker', 'sentiment_label', 'sentiment_score', 'analyzed_at')
    list_filter = ('sentiment_label', 'analyzed_at')
    search_fields = ('user__username', 'ticker')
    readonly_fields = ('analyzed_at',)
    list_display_links = ('user', 'ticker')