from django.shortcuts import render
from rest_framework import viewsets, permissions
from .models import StockWatchlist, SentimentAnalysis
from .serializers import StockWatchlistSerializer, SentimentAnalysisSerializer
from rest_framework import status
import os
import requests
from datetime import datetime, timedelta, time
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
import pytz
import logging  
import csv
from rest_framework import viewsets, permissions
from .models import StockWatchlist
from .serializers import StockWatchlistSerializer
from rest_framework.permissions import IsAuthenticated


logger = logging.getLogger(__name__)

# Load tickers -> names once
companies = {}
with open("constituents.csv") as f:
    reader = csv.reader(f)
    for row in reader:
        ticker = row[0].strip()
        name = row[1].strip()
        if ticker and name:
            companies[ticker] = name



# ---------- CRUD Functions ----------

class StockWatchlistViewSet(viewsets.ModelViewSet):
    serializer_class = StockWatchlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filter to only show the current user's watchlist items
        return StockWatchlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Auto-set the user to the authenticated user
        serializer.save(user=self.request.user)



# ---------- Utility Functions ----------
def get_today():
    return datetime.today().strftime("%Y-%m-%d")


def get_yesterday():
    return (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")


def get_first_day_of_current_month():
    today = datetime.today()
    return today.replace(day=1).strftime("%Y-%m-%d")


def get_same_day_last_year():
    today = datetime.today()
    last_year = today.replace(year=today.year - 1)
    return last_year.strftime("%Y-%m-%d")


class StockWatchlistViewSet(viewsets.ModelViewSet):
    serializer_class = StockWatchlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StockWatchlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class SentimentAnalysisViewSet(viewsets.ModelViewSet):
    serializer_class = SentimentAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SentimentAnalysis.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ===========================================================================================================


class GSPCView(APIView):
    """Fetch S&P 500 (^GSPC) historical data from Yahoo Finance"""

    def get(self, request):
        time_range = request.query_params.get("range", "90d")
        period_map = {
            "7d": "7d",
            "30d": "1mo",
            "90d": "3mo",
        }
        period = period_map.get(time_range)
        if not period:
            return Response({"error": "Invalid time range"}, status=400)

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?range={period}&interval=1d"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }

        try:
            r = requests.get(url, headers=headers)
            r.raise_for_status()
            raw_data = r.json()

            if not raw_data.get("chart") or not raw_data["chart"].get("result"):
                return Response({"error": "No data received"}, status=500)

            yahoo_data = raw_data["chart"]["result"][0]
            timestamps = yahoo_data["timestamp"]
            closes = yahoo_data["indicators"]["quote"][0]["close"]

            formatted_data = [
                {
                    "date": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"),
                    "close": closes[i],
                }
                for i, ts in enumerate(timestamps)
                if closes[i] is not None
            ]

            return Response({"data": formatted_data, "success": True})
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=500)


class CompanyNewsView(APIView):
    """Fetch company news from Finnhub"""

    def get(self, request):
        symbol = request.query_params.get("symbol")
        from_date = request.query_params.get("from", get_yesterday())
        to_date = request.query_params.get("to", get_today())

        if not symbol:
            return Response(
                {"error": "Missing required query parameters: symbol, from, to"},
                status=400,
            )

        url = (
            f"https://finnhub.io/api/v1/company-news"
            f"?symbol={symbol}&from={from_date}&to={to_date}"
            f"&token={settings.FINNHUB_API_KEY}"
        )

        try:
            r = requests.get(url)
            r.raise_for_status()
            return Response(r.json())
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=500)


class InsiderSentimentView(APIView):
    """Fetch insider sentiment data from Finnhub"""

    def get(self, request):
        symbol = request.query_params.get("symbol")
        from_date = request.query_params.get("from", get_same_day_last_year())
        to_date = request.query_params.get("to", get_first_day_of_current_month())

        if not symbol:
            return Response({"error": "Missing symbol parameter"}, status=400)

        url = (
            f"https://finnhub.io/api/v1/stock/insider-sentiment"
            f"?symbol={symbol}&from={from_date}&to={to_date}"
            f"&token={settings.FINNHUB_API_KEY}"
        )

        try:
            r = requests.get(url)
            r.raise_for_status()
            return Response(r.json())
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=500)


class StocksView(APIView):
    """Fetch stock profile or list of US stocks"""

    def get(self, request):
        symbol = request.query_params.get("symbol")

        if symbol:
            url = (
                f"https://finnhub.io/api/v1/stock/profile2"
                f"?symbol={symbol}&token={settings.FINNHUB_API_KEY}"
            )
            try:
                r = requests.get(url)
                r.raise_for_status()
                return Response(r.json())
            except requests.RequestException as e:
                return Response({"error": str(e)}, status=500)

        url = (
            f"https://finnhub.io/api/v1/stock/symbol"
            f"?exchange=US&token={settings.FINNHUB_API_KEY}"
        )
        try:
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            valid_mics = ["XNYS", "XNAS", "XNMS", "XNGS", "XNCM"]
            filtered = [stock for stock in data if stock.get("mic") in valid_mics]
            return Response(filtered[:10])
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=500)


class YahooETFsView(APIView):
    """Fetch multiple ETF historical data from Yahoo Finance"""

    def get(self, request):
        etfs_param = request.query_params.get("etfs")
        range_param = request.query_params.get("range", "1mo")
        interval = request.query_params.get("interval", "1d")

        if not etfs_param:
            return Response({"error": "Missing 'etfs' parameter"}, status=400)

        etfs = etfs_param.split(",")
        all_data = {}
        dates = set()

        try:
            for etf in etfs:
                url = (
                    f"https://query1.finance.yahoo.com/v8/finance/chart/{etf}"
                    f"?interval={interval}&range={range_param}"
                )
                r = requests.get(url)
                r.raise_for_status()
                json_data = r.json()

                timestamps = json_data["chart"]["result"][0]["timestamp"]
                closes = json_data["chart"]["result"][0]["indicators"]["quote"][0]["close"]

                all_data[etf] = [
                    {
                        "date": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"),
                        "value": closes[i],
                    }
                    for i, ts in enumerate(timestamps)
                ]
                for ts in timestamps:
                    dates.add(datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"))

            aligned_data = []
            for date in sorted(dates):
                point = {"date": date}
                for etf in etfs:
                    etf_point = next(
                        (p for p in all_data[etf] if p["date"] == date), None
                    )
                    point[etf] = etf_point["value"] if etf_point else None
                aligned_data.append(point)

            return Response(aligned_data)
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=500)
        
        




class StockSnapShotView(APIView):
    """Fetch stock data from Alpaca"""
    
    def get(self, request, symbol=None):

        if not symbol:
            symbol = request.query_params.get('symbol')
        
        if not symbol:
            return Response(
                {"error": "Symbol parameter is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        symbol = symbol.upper().strip()
        if not symbol.isalpha():
            return Response(
                {"error": "Invalid symbol format"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        url = f"https://data.alpaca.markets/v2/stocks/{symbol}/snapshot"
        

        headers = {
            "APCA-API-KEY-ID": settings.ALPACA_API_KEY_ID,
            "APCA-API-SECRET-KEY": settings.ALPACA_API_SECRET_KEY
        }
        
        try:

            response = requests.get(url, headers=headers, timeout=30)
            

            if response.status_code == 200:
                data = response.json()
                return Response(data, status=status.HTTP_200_OK)
            
            elif response.status_code == 404:
                return Response(
                    {"error": f"Symbol '{symbol}' not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            elif response.status_code == 401:
                return Response(
                    {"error": "Invalid API credentials"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            elif response.status_code == 429:
                return Response(
                    {"error": "Rate limit exceeded. Please try again later."}, 
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            else:
                return Response(
                    {
                        "error": "Failed to fetch data from Alpaca", 
                        "status_code": response.status_code,
                        "message": response.text
                    }, 
                    status=status.HTTP_502_BAD_GATEWAY
                )
        
        except requests.exceptions.Timeout:
            return Response(
                {"error": "Request timeout. Alpaca API is not responding."}, 
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        
        except requests.exceptions.ConnectionError:
            return Response(
                {"error": "Connection error. Unable to reach Alpaca API."}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        except requests.exceptions.RequestException as e:
            return Response(
                {"error": f"Request failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        except Exception as e:
            return Response(
                {"error": f"Unexpected error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class StockChartView(APIView):
    """Fetch stock chart data from Alpaca"""

    def get(self, request):
        symbol = request.query_params.get("symbol")
        range_type = request.query_params.get("range")

        if not symbol or not range_type:
            return Response({"error": "Missing 'symbol' or 'range' parameter"}, status=400)

        now_ct = datetime.now(pytz.timezone('America/Chicago'))

        if range_type == "1D":
            start_dt = datetime.combine(now_ct.date(), time(8, 30), tzinfo=pytz.timezone('America/Chicago')) 
            timeframe = "1Min"
        elif range_type == "1W":
            start_dt = now_ct - timedelta(days=7)
            timeframe = "15Min"
        elif range_type == "1M":
            start_dt = now_ct - timedelta(days=30)
            timeframe = "1Day"
        elif range_type == "3M":
            start_dt = now_ct - timedelta(days=90)
            timeframe = "1Day"
        elif range_type == "YTD":
            start_dt = datetime(now_ct.year, 1, 1, tzinfo=pytz.timezone('America/Chicago'))
            timeframe = "1Day"
        elif range_type == "1Y":
            start_dt = now_ct - timedelta(days=365)
            timeframe = "1Day"
        elif range_type == "5Y":
            start_dt = now_ct - timedelta(days=365*5)
            timeframe = "1Week"
        else:
            return Response({"error": "Invalid range type"}, status=400)

        start_utc = start_dt.astimezone(pytz.UTC).isoformat()
        end_utc = now_ct.astimezone(pytz.UTC).isoformat()

        url = "https://data.alpaca.markets/v2/stocks/bars" 
        # url = "https://data.sandbox.alpaca.markets/v2/stocks/bars"  
        # url = "https://paper-api.alpaca.markets/v2"
        headers = {
            "APCA-API-KEY-ID": settings.ALPACA_API_KEY_ID,
            "APCA-API-SECRET-KEY": settings.ALPACA_API_SECRET_KEY
        }
        params = {
            "symbols": symbol,
            "timeframe": timeframe,
            "start": start_utc,
            "end": end_utc,
            "limit": 1000,
            "adjustment": "raw",
            "feed": "iex" 
        }

        try:

            logger.info(f"Requesting Alpaca: {url} with params {params}")
            
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()  
            data = resp.json()

            bars = data.get("bars", {}).get(symbol.upper(), [])
            if not bars:
                return Response({"error": "No data received from Alpaca"}, status=500)

            chart_data = [
                {
                    "t": bar["t"],  # ISO time
                    "o": bar["o"],  # open
                    "h": bar["h"],  # high
                    "l": bar["l"],  # low
                    "c": bar["c"],  # close
                    "v": bar["v"],  # volume
                }
                for bar in bars
            ]

            return Response({"symbol": symbol.upper(), "range": range_type, "data": chart_data})
        except requests.RequestException as e:
            error_details = resp.json() if 'resp' in locals() and resp.content else str(e)
            logger.error(f"Alpaca error details: {error_details}")
            return Response({"error": f"Alpaca API error: {str(e)}", "details": error_details}, status=500)


class CompanyNewsApiView(APIView):
    """Fetch company news from NewsAPI"""

    def get(self, request):
        symbol = request.query_params.get("symbol")
        if not symbol:
            return Response({"error": "Missing 'symbol' parameter"}, status=400)

        company_name = companies.get(symbol.upper())
        if not company_name:
            return Response({"error": "Ticker not found"}, status=404)

        # Keep 'from' fixed (e.g., 30 days ago) while 'to' is yesterday
        from_date = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        to_date = get_yesterday()

        BASE_URL = "https://newsapi.org/v2/everything"
        DOMAINS = ",".join([
            "reuters.com",
            "marketwatch.com",
            "wsj.com",
            "bloomberg.com",
            "fortune.com",
            "forbes.com",
            "businessinsider.com",
            "fool.com",
            "investing.com",
            "seekingalpha.com",
        ])

        params = {
            "q": f'"{company_name}"',
            "domains": DOMAINS,
            "from": from_date,
            "to": to_date,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 100,
            "apiKey": settings.NEWS_API_KEY,
        }

        try:
            # First request with searchIn=title
            params["searchIn"] = "title"
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            # If no results or less than 5, retry without searchIn
            if not data.get("articles") or len(data["articles"]) < 5:
                del params["searchIn"]
                response = requests.get(BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            return Response(data)
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=500)