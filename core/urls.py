from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StockWatchlistViewSet, SentimentAnalysisViewSet
from .views import (
    GSPCView,
    CompanyNewsView,
    InsiderSentimentView,
    StocksView,
    YahooETFsView,
    StockChartView,
    CompanyNewsApiView,
    StockSnapShotView,
)


router = DefaultRouter()
router.register(r'watchlist', StockWatchlistViewSet, basename='watchlist')
router.register(r'sentiments', SentimentAnalysisViewSet, basename='sentiments')

urlpatterns = [
    path('', include(router.urls)),
    path("gspc/", GSPCView.as_view()),
    path("company-news/", CompanyNewsView.as_view()),
    path("insider-sentiment/", InsiderSentimentView.as_view()),
    path("stocks/", StocksView.as_view()),
    path("yahoo-etfs/", YahooETFsView.as_view()),
    path("chart/", StockChartView.as_view()),
    path("company-news-two/", CompanyNewsApiView.as_view()),
    path("snapshot/", StockSnapShotView.as_view())
 
]







