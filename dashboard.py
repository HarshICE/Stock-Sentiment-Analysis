import dash
from dash import dcc, html, Input, Output, callback
import dash.dependencies
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import dash_bootstrap_components as dbc
from config import Config
from database import DatabaseManager, NewsArticle, SentimentAnalysis, StockPrice
from sqlalchemy import func, and_
import yfinance as yf
from stock_lookup import stock_lookup
from logger_config import get_logger, action_logger
from region_manager import RegionManager
import traceback
from deduplication_utils import NewsDeduplicator

class StockSentimentDashboard:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.region_manager = RegionManager()
        self.logger = get_logger('stock_sentiment_app.dashboard')
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.logger.info("Initializing Stock Sentiment Dashboard")
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Setup the dashboard layout"""
        self.app.layout = dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("Stock Sentiment Analysis Dashboard", 
                           className="text-center mb-4", 
                           style={'color': '#2c3e50'}),
                    html.Div(id="region-status", className="text-center mb-3")
                ])
            ]),
            
            # Search Bar Row
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Search Any Stock", className="card-title mb-3"),
                            html.Div(id="search-placeholder-text", className="mb-2"),
                            dbc.InputGroup([
                                dbc.Input(
                                    id="stock-search-input",
                                    placeholder="",
                                    value="",
                                    className="form-control"
                                ),
                                dbc.Button(
                                    "Search",
                                    id="search-button",
                                    color="primary",
                                    n_clicks=0
                                )
                            ], className="mb-3"),
                            html.Div(id="search-results", className="mb-3"),
                            html.Div(id="search-status", className="text-muted")
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Select Stock Symbol", className="card-title"),
                            dcc.Dropdown(
                                id='stock-dropdown',
                                options=self.get_default_stock_options(),
                                value=self.get_default_stock_symbol(),
                                className="mb-3"
                            ),
                            html.H4("Select Time Range", className="card-title"),
                            dcc.Dropdown(
                                id='time-range-dropdown',
                                options=[
                                    {'label': '1 Day', 'value': 1},
                                    {'label': '3 Days', 'value': 3},
                                    {'label': '1 Week', 'value': 7},
                                    {'label': '2 Weeks', 'value': 14},
                                    {'label': '1 Month', 'value': 30}
                                ],
                                value=7,
                                className="mb-3"
                            )
                        ])
                    ])
                ], width=3),
                
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Current Sentiment", className="card-title"),
                                    html.H2(id="current-sentiment-score", className="text-center"),
                                    html.P(id="current-sentiment-label", className="text-center")
                                ])
                            ])
                        ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Total Articles", className="card-title"),
                            html.H2(id="total-articles", className="text-center"),
                            html.P("News Articles", className="text-center")
                        ])
                    ])
                ], width=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Stock Price", className="card-title"),
                                    html.H2(id="current-stock-price", className="text-center"),
                                    html.P(id="price-change", className="text-center")
                                ])
                            ])
                        ], width=4)
                    ], className="mb-4")
                ], width=9)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Sentiment vs Stock Price", className="card-title"),
                            dcc.Graph(id='sentiment-stock-chart')
                        ])
                    ])
                ], width=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Sentiment Distribution", className="card-title"),
                            dcc.Graph(id='sentiment-distribution-chart')
                        ])
                    ])
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Sentiment Over Time", className="card-title"),
                            dcc.Graph(id='sentiment-timeline-chart')
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Recent News Articles", className="card-title"),
                            html.Div(id='recent-articles')
                        ])
                    ])
                ], width=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Sentiment Analysis Models", className="card-title"),
                            dcc.Graph(id='model-comparison-chart')
                        ])
                    ])
                ], width=6)
            ]),
            
            # Interval component for periodic updates
            dcc.Interval(
                id='interval-component',
                interval=5*1000,  # Update every 5 seconds
                n_intervals=0
            )
        ], fluid=True)
    
    def setup_callbacks(self):
        """Setup dashboard callbacks"""
        
        @self.app.callback(
            [Output('current-sentiment-score', 'children'),
             Output('current-sentiment-label', 'children'),
             Output('total-articles', 'children'),
             Output('current-stock-price', 'children'),
             Output('price-change', 'children'),
             Output('region-status', 'children'),
             Output('search-placeholder-text', 'children')],
            [Input('stock-dropdown', 'value'),
             Input('time-range-dropdown', 'value')]
        )
        def update_summary_cards(selected_stock, time_range):
            summary_data = self.get_summary_data(selected_stock, time_range)
            region_status = self.get_region_status()
            search_placeholder = self.get_search_placeholder()
            return summary_data + (region_status, search_placeholder)
        
        @self.app.callback(
            Output('sentiment-stock-chart', 'figure'),
            [Input('stock-dropdown', 'value'),
             Input('time-range-dropdown', 'value')]
        )
        def update_sentiment_stock_chart(selected_stock, time_range):
            return self.create_sentiment_stock_chart(selected_stock, time_range)
        
        @self.app.callback(
            Output('sentiment-distribution-chart', 'figure'),
            [Input('stock-dropdown', 'value'),
             Input('time-range-dropdown', 'value')]
        )
        def update_sentiment_distribution_chart(selected_stock, time_range):
            return self.create_sentiment_distribution_chart(selected_stock, time_range)
        
        @self.app.callback(
            Output('sentiment-timeline-chart', 'figure'),
            [Input('stock-dropdown', 'value'),
             Input('time-range-dropdown', 'value')]
        )
        def update_sentiment_timeline_chart(selected_stock, time_range):
            return self.create_sentiment_timeline_chart(selected_stock, time_range)
        
        @self.app.callback(
            Output('recent-articles', 'children'),
            [Input('stock-dropdown', 'value'),
             Input('time-range-dropdown', 'value')]
        )
        def update_recent_articles(selected_stock, time_range):
            return self.get_recent_articles(selected_stock, time_range)
        
        @self.app.callback(
            Output('model-comparison-chart', 'figure'),
            [Input('stock-dropdown', 'value'),
             Input('time-range-dropdown', 'value')]
        )
        def update_model_comparison_chart(selected_stock, time_range):
            return self.create_model_comparison_chart(selected_stock, time_range)
        
        # Search functionality callbacks
        @self.app.callback(
            [Output('search-results', 'children'),
             Output('search-status', 'children'),
             Output('stock-dropdown', 'options'),
             Output('stock-dropdown', 'value')],
            [Input('search-button', 'n_clicks'),
             Input('stock-search-input', 'n_submit')],
            [dash.dependencies.State('stock-search-input', 'value'),
             dash.dependencies.State('stock-dropdown', 'options'),
             dash.dependencies.State('stock-dropdown', 'value')]
        )
        def handle_stock_search(n_clicks, n_submit, search_query, current_options, current_value):
            return self.search_stock_handler(n_clicks, n_submit, search_query, current_options, current_value)
        
        # Callback to update dropdown options based on region (triggered by interval)
        @self.app.callback(
            [Output('stock-dropdown', 'options', allow_duplicate=True),
             Output('stock-dropdown', 'value', allow_duplicate=True)],
            [Input('interval-component', 'n_intervals')],
            [dash.dependencies.State('stock-dropdown', 'value')],
            prevent_initial_call=True
        )
        def update_dropdown_for_region(n_intervals, current_value):
            """Update dropdown options when region changes, preserving user selection"""
            new_options = self.get_default_stock_options()
            
            # Check if current value is still valid in new options
            if current_value:
                option_values = [option['value'] for option in new_options]
                if current_value in option_values:
                    # Keep the current selection if it's still valid
                    return new_options, current_value
            
            # Only change to default if current value is not available
            new_default = self.get_default_stock_symbol()
            return new_options, new_default
    
    def get_summary_data(self, stock_symbol, time_range):
        """Get summary data for the cards"""
        session = self.db_manager.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=time_range)
            
            # Get latest sentiment
            latest_sentiment = session.query(SentimentAnalysis).filter(
                SentimentAnalysis.symbol == stock_symbol,
                SentimentAnalysis.date >= cutoff_date
            ).order_by(SentimentAnalysis.date.desc()).first()
            
            if latest_sentiment:
                sentiment_score = f"{latest_sentiment.avg_sentiment:.3f}"
                if latest_sentiment.avg_sentiment > 0.1:
                    sentiment_label = "Positive 📈"
                elif latest_sentiment.avg_sentiment < -0.1:
                    sentiment_label = "Negative 📉"
                else:
                    sentiment_label = "Neutral ➡️"
                total_articles = latest_sentiment.sentiment_count
            else:
                sentiment_score = "N/A"
                sentiment_label = "No Data"
                total_articles = 0
            
            # Get current stock price
            try:
                ticker = yf.Ticker(stock_symbol)
                hist = ticker.history(period="2d")
                if not hist.empty:
                    # Determine currency symbol based on stock symbol
                    currency_symbol = "₹" if ".NS" in stock_symbol or ".BO" in stock_symbol else "$"
                    current_price = f"{currency_symbol}{hist['Close'].iloc[-1]:.2f}"
                    if len(hist) > 1:
                        price_change = hist['Close'].iloc[-1] - hist['Close'].iloc[-2]
                        price_change_pct = (price_change / hist['Close'].iloc[-2]) * 100
                        change_color = "success" if price_change > 0 else "danger"
                        price_change_text = f"{currency_symbol}{price_change:+.2f} ({price_change_pct:+.1f}%)"
                    else:
                        price_change_text = "N/A"
                        change_color = "secondary"
                else:
                    current_price = "N/A"
                    price_change_text = "N/A"
                    change_color = "secondary"
            except Exception as e:
                # Log the error for debugging
                self.logger.error(f"Error fetching stock price for {stock_symbol}: {e}")
                current_price = "N/A"
                price_change_text = "N/A"
                change_color = "secondary"
            
            return (
                sentiment_score,
                sentiment_label,
                str(total_articles),
                current_price,
                html.Span(price_change_text, className=f"text-{change_color}")
            )
        finally:
            self.db_manager.close_session(session)
    
    def create_sentiment_stock_chart(self, stock_symbol, time_range):
        """Create sentiment vs stock price chart"""
        session = self.db_manager.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=time_range)
            
            # Get sentiment data
            sentiment_data = session.query(SentimentAnalysis).filter(
                SentimentAnalysis.symbol == stock_symbol,
                SentimentAnalysis.date >= cutoff_date
            ).order_by(SentimentAnalysis.date).all()
            
            if not sentiment_data:
                self.logger.warning(f"No sentiment data available for {stock_symbol}")
                action_logger.log_chart_generation("sentiment_stock", stock_symbol, False, "No sentiment data available")
                return go.Figure().add_annotation(
                    text="No sentiment data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
            
            # Get stock price data
            try:
                ticker = yf.Ticker(stock_symbol)
                hist = ticker.history(period=f"{time_range}d")
                hist.reset_index(inplace=True)
            except Exception as e:
                self.logger.error(f"Error fetching stock price data for {stock_symbol}: {e}")
                hist = pd.DataFrame()
            
            # Create subplots
            fig = go.Figure()
            
            # Add sentiment line
            dates = [s.date for s in sentiment_data]
            sentiments = [s.avg_sentiment for s in sentiment_data]
            
            fig.add_trace(go.Scatter(
                x=dates,
                y=sentiments,
                mode='lines+markers',
                name='Sentiment Score',
                line=dict(color='blue', width=2),
                yaxis='y'
            ))
            
            # Add stock price line (if available)
            if not hist.empty:
                fig.add_trace(go.Scatter(
                    x=hist['Date'],
                    y=hist['Close'],
                    mode='lines',
                    name='Stock Price',
                    line=dict(color='red', width=2),
                    yaxis='y2'
                ))

            self.logger.info(f"Sentiment vs Stock Price chart created for {stock_symbol}")
            action_logger.log_chart_generation("sentiment_stock", stock_symbol, True)
            
            # Update layout
            # Determine currency symbol for y-axis title
            currency_symbol = "₹" if ".NS" in stock_symbol or ".BO" in stock_symbol else "$"
            
            fig.update_layout(
                title=f'{stock_symbol} - Sentiment vs Stock Price',
                xaxis_title='Date',
                yaxis=dict(
                    title='Sentiment Score',
                    title_font=dict(color='blue'),
                    tickfont=dict(color='blue')
                ),
                yaxis2=dict(
                    title=f'Stock Price ({currency_symbol})',
                    title_font=dict(color='red'),
                    tickfont=dict(color='red'),
                    overlaying='y',
                    side='right'
                ),
                height=400
            )
            
            return fig
        except Exception as e:
            self.logger.error(f"Failed to create sentiment vs stock price chart for {stock_symbol}: {e}", exc_info=True)
            action_logger.log_chart_generation("sentiment_stock", stock_symbol, False, str(e))
            return go.Figure().add_annotation(
                text="Error generating chart",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        finally:
            self.db_manager.close_session(session)
    
    def create_sentiment_distribution_chart(self, stock_symbol, time_range):
        """Create sentiment distribution pie chart"""
        session = self.db_manager.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=time_range)
            
            # Get sentiment counts
            sentiment_counts = session.query(
                func.sum(SentimentAnalysis.positive_count).label('positive'),
                func.sum(SentimentAnalysis.negative_count).label('negative'),
                func.sum(SentimentAnalysis.neutral_count).label('neutral')
            ).filter(
                SentimentAnalysis.symbol == stock_symbol,
                SentimentAnalysis.date >= cutoff_date
            ).first()
            
            if not sentiment_counts or not any([sentiment_counts.positive, sentiment_counts.negative, sentiment_counts.neutral]):
                return go.Figure().add_annotation(
                    text="No sentiment data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
            
            labels = ['Positive', 'Negative', 'Neutral']
            values = [
                sentiment_counts.positive or 0,
                sentiment_counts.negative or 0,
                sentiment_counts.neutral or 0
            ]
            colors = ['#2ecc71', '#e74c3c', '#95a5a6']
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=colors),
                textinfo='label+percent',
                textposition='auto'
            )])
            
            fig.update_layout(
                title=f'{stock_symbol} - Sentiment Distribution',
                height=400
            )
            
            return fig
        finally:
            self.db_manager.close_session(session)
    
    def create_sentiment_timeline_chart(self, stock_symbol, time_range):
        """Create sentiment timeline chart"""
        session = self.db_manager.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=time_range)
            
            # Get sentiment data
            sentiment_data = session.query(SentimentAnalysis).filter(
                SentimentAnalysis.symbol == stock_symbol,
                SentimentAnalysis.date >= cutoff_date
            ).order_by(SentimentAnalysis.date).all()
            
            if not sentiment_data:
                return go.Figure().add_annotation(
                    text="No sentiment data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
            
            dates = [s.date for s in sentiment_data]
            news_sentiment = [s.news_sentiment for s in sentiment_data]
            combined_sentiment = [s.avg_sentiment for s in sentiment_data]
            
            fig = go.Figure()
            
            # Add traces
            fig.add_trace(go.Scatter(
                x=dates,
                y=news_sentiment,
                mode='lines+markers',
                name='News Sentiment',
                line=dict(color='blue', width=2)
            ))
            
            fig.add_trace(go.Scatter(
                x=dates,
                y=combined_sentiment,
                mode='lines+markers',
                name='Overall Sentiment',
                line=dict(color='red', width=3)
            ))
            
            # Add horizontal lines for reference
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            fig.add_hline(y=0.1, line_dash="dash", line_color="green", opacity=0.3)
            fig.add_hline(y=-0.1, line_dash="dash", line_color="red", opacity=0.3)
            
            fig.update_layout(
                title=f'{stock_symbol} - Sentiment Timeline',
                xaxis_title='Date',
                yaxis_title='Sentiment Score',
                height=400
            )
            
            return fig
        finally:
            self.db_manager.close_session(session)
    
    def get_recent_articles(self, stock_symbol, time_range):
        """Get recent articles with duplicate filtering"""
        session = self.db_manager.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=time_range)
            
            # Get recent news articles
            all_articles = session.query(NewsArticle).filter(
                NewsArticle.stock_symbol == stock_symbol,
                NewsArticle.created_at >= cutoff_date
            ).order_by(NewsArticle.created_at.desc()).all()
            
            # Apply light duplicate filtering (only URL and exact title duplicates)
            # This is less aggressive than content-based filtering
            news_articles = self._filter_duplicate_articles(all_articles, limit=10)
            
            # If we still don't have enough articles, try without filtering
            if len(news_articles) < 5 and len(all_articles) > len(news_articles):
                print(f"Only {len(news_articles)} unique articles found, showing all {len(all_articles)} articles")
                news_articles = all_articles[:10]  # Just take the first 10 without filtering
            
            articles_html = []
            
            # Add news articles
            for article in news_articles:
                sentiment_color = self.get_sentiment_color(article.sentiment_score)
                articles_html.append(
                    dbc.Card([
                        dbc.CardBody([
                            html.H6(article.title, className="card-title"),
                            html.P(f"Source: {article.source}", className="card-text"),
                            html.P(f"Published: {article.published_date.strftime('%Y-%m-%d %H:%M') if article.published_date else 'N/A'}", className="card-text"),
                            dbc.Badge(f"Sentiment: {article.sentiment_score:.3f}" if article.sentiment_score else "Not analyzed", color=sentiment_color)
                        ])
                    ], className="mb-2")
                )
            
            return articles_html if articles_html else [html.P("No recent articles found.")]
        finally:
            self.db_manager.close_session(session)
    
    def _filter_duplicate_articles(self, articles, limit=None):
        """Filter duplicate articles using a less aggressive approach for dashboard display"""
        unique_articles = []
        seen_urls = set()
        seen_titles = set()
        
        for article in articles:
            is_duplicate = False
            
            # Check for exact URL duplicates (most reliable)
            if article.url and article.url in seen_urls:
                is_duplicate = True
            elif article.url:
                seen_urls.add(article.url)
            
            # Check for exact title duplicates (less aggressive than content hash)
            if not is_duplicate and article.title:
                title_normalized = article.title.lower().strip()
                if title_normalized in seen_titles:
                    is_duplicate = True
                else:
                    seen_titles.add(title_normalized)
            
            if not is_duplicate:
                unique_articles.append(article)
                if limit and len(unique_articles) >= limit:
                    break
        
        return unique_articles
    
    def get_sentiment_color(self, score):
        """Get color based on sentiment score"""
        if score is None:
            return "secondary"
        elif score > 0.1:
            return "success"
        elif score < -0.1:
            return "danger"
        else:
            return "secondary"
    
    def create_model_comparison_chart(self, stock_symbol, time_range):
        """Create model comparison chart"""
        session = self.db_manager.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=time_range)
            
            # Get average scores for each model from news articles
            news_scores = session.query(
                func.avg(NewsArticle.vader_score).label('vader'),
                func.avg(NewsArticle.textblob_score).label('textblob'),
                func.avg(NewsArticle.finbert_score).label('finbert')
            ).filter(
                NewsArticle.stock_symbol == stock_symbol,
                NewsArticle.created_at >= cutoff_date
            ).first()
            
            if not news_scores:
                return go.Figure().add_annotation(
                    text="No model comparison data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
            
            models = ['VADER', 'TextBlob', 'FinBERT']
            news_values = [
                news_scores.vader or 0,
                news_scores.textblob or 0,
                news_scores.finbert or 0
            ]
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=models,
                y=news_values,
                name='News Articles',
                marker_color='blue'
            ))
            
            fig.update_layout(
                title=f'{stock_symbol} - Model Comparison',
                xaxis_title='Model',
                yaxis_title='Average Sentiment Score',
                height=400,
                barmode='group'
            )
            
            return fig
        finally:
            self.db_manager.close_session(session)
    
    def search_stock_handler(self, n_clicks, n_submit, search_query, current_options, current_value):
        """Handle stock search and update dropdown options"""
        if not search_query:
            return "", "Enter a stock symbol or company name.", current_options, current_value
        
        # Find stock symbol
        symbol = stock_lookup.search_stock(search_query)
        if not symbol:
            suggestions = stock_lookup.get_stock_suggestions(search_query)
            if suggestions:
                results_html = html.Ul([
                    html.Li(f"{s['symbol']} - {s['name']} ({s['match_type']})") for s in suggestions
                ])
                return results_html, f"Found {len(suggestions)} suggestions. Please select from the list.", current_options, current_value
            return "", "No results found. Try a different search term.", current_options, current_value
        
        # Get company name for display
        company_name = stock_lookup.get_company_name(symbol)
        
        # Update options with new symbol if not present
        option_values = [option['value'] for option in current_options]
        if symbol not in option_values:
            current_options.append({'label': f"{symbol} - {company_name}", 'value': symbol})
        
        # Show search results
        results_html = dbc.Alert(
            [html.Strong(f"Found: {symbol}"), html.Br(), f"Company: {company_name}"],
            color="success"
        )
        
        return results_html, f"Stock {symbol} added to dropdown and selected.", current_options, symbol
    
    def get_default_stock_options(self):
        """Get default stock options for dropdown (filtered by current region)"""
        options = []
        try:
            # Get current region
            current_region = self.region_manager.get_current_region()
            
            # Get active stocks from database
            active_stocks = self.db_manager.get_active_stocks()
            
            # Filter stocks by region
            for symbol in active_stocks:
                if stock_lookup.is_symbol_in_region(symbol, current_region):
                    company_name = stock_lookup.get_company_name(symbol)
                    options.append({
                        'label': f"{symbol} - {company_name}",
                        'value': symbol
                    })
        except Exception as e:
            print(f"Warning: Failed to load active stocks from database: {e}")
            # Fallback to a basic list if database fails (region-aware)
            current_region = self.region_manager.get_current_region()
            if current_region == 'US':
                basic_stocks = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
            else:
                basic_stocks = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS']
            
            for symbol in basic_stocks:
                company_name = stock_lookup.get_company_name(symbol)
                options.append({
                    'label': f"{symbol} - {company_name}",
                    'value': symbol
                })
        return options
    
    def get_default_stock_symbol(self):
        """Get the default stock symbol to select (filtered by current region)"""
        try:
            # Get current region
            current_region = self.region_manager.get_current_region()
            
            # Get active stocks from database
            active_stocks = self.db_manager.get_active_stocks()
            
            # Filter stocks by region and return the first one
            for symbol in active_stocks:
                if stock_lookup.is_symbol_in_region(symbol, current_region):
                    return symbol
                    
        except Exception as e:
            print(f"Warning: Failed to load active stocks from database: {e}")
        
        # Fallback to a basic stock symbol based on region
        current_region = self.region_manager.get_current_region()
        if current_region == 'US':
            return 'AAPL'
        else:
            return 'RELIANCE.NS'
    
    def get_region_status(self):
        """Get current region status for display"""
        current_region = self.region_manager.get_current_region()
        regions = self.region_manager.list_regions()
        region_info = regions.get(current_region, {})
        
        return dbc.Alert([
            html.Strong(f"📍 Current Region: {region_info.get('name', current_region)}"),
            html.Br(),
            html.Small(f"Currency: {region_info.get('currency', 'N/A')} | "
                      f"Exchanges: {', '.join(region_info.get('exchanges', []))}"),
            html.Br(),
            html.Small(f"Search is limited to {region_info.get('name', current_region)} companies only. "
                      f"Switch regions using: python region_manager.py --switch {'IN' if current_region == 'US' else 'US'}")
        ], color="info", className="mb-3")
    
    def get_search_placeholder(self):
        """Get search placeholder text based on current region"""
        current_region = self.region_manager.get_current_region()
        
        if current_region == 'US':
            examples = "e.g., AAPL, Apple, MSFT, Microsoft"
        else:
            examples = "e.g., RELIANCE.NS, TCS.NS, HDFC Bank"
        
        return html.P(f"Enter {current_region} stock symbol or company name ({examples})", 
                     className="text-muted small")
    
    def run_server(self, debug=None):
        """Run the dashboard server"""
        import threading
        
        # Disable debug mode when running in a thread to avoid signal handler issues
        if debug is None:
            debug = Config.DASHBOARD_DEBUG and threading.current_thread() is threading.main_thread()
        
        self.app.run(
            debug=debug,
            host=Config.DASHBOARD_HOST,
            port=Config.DASHBOARD_PORT,
            use_reloader=False  # Disable reloader in threaded mode
        )

if __name__ == "__main__":
    dashboard = StockSentimentDashboard()
    dashboard.run_server()
