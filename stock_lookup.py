import yfinance as yf
import re
from config import Config
from database import DatabaseManager
from region_manager import RegionManager

class StockLookup:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.region_manager = RegionManager()
        self.company_mappings = self.load_company_mappings()
        
    def search_stock(self, query):
        """Search for a stock symbol based on query (company name or symbol)"""
        if not query:
            return None
            
        query = query.upper().strip()
        
        # Get current region to filter results
        current_region = self.region_manager.get_current_region()
        
        # First, check if it's already a valid symbol and in current region
        if self.is_valid_symbol(query) and self.is_symbol_in_region(query, current_region):
            return query
            
        # Check company mappings (filtered by region)
        region_filtered_mappings = self.get_region_filtered_mappings(current_region)
        if query in region_filtered_mappings:
            return region_filtered_mappings[query]
            
        # Try partial matches in company names (filtered by region)
        for company_name, symbol in region_filtered_mappings.items():
            if (query in company_name or company_name in query):
                return symbol
                
        # If no mapping found, try to validate as a direct symbol (but check region)
        if self.is_valid_symbol(query) and self.is_symbol_in_region(query, current_region):
            return query
            
        return None
    
    def is_valid_symbol(self, symbol):
        """Check if a symbol is valid by trying to fetch data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Check if we got valid data
            if info and 'symbol' in info:
                return True
            
            # Try getting recent history as fallback
            hist = ticker.history(period="1d")
            return not hist.empty
            
        except Exception:
            return False
    
    def get_company_name(self, symbol):
        """Get the company name for a given symbol"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Try different fields for company name
            for field in ['longName', 'shortName', 'displayName']:
                if field in info and info[field]:
                    return info[field]
                    
            return symbol  # Return symbol if no name found
            
        except Exception:
            return symbol
    
    def get_stock_suggestions(self, query, limit=10):
        """Get stock suggestions based on partial query (filtered by current region)"""
        if not query:
            return []
            
        query = query.upper().strip()
        suggestions = []
        
        # Get current region to filter results
        current_region = self.region_manager.get_current_region()
        region_filtered_mappings = self.get_region_filtered_mappings(current_region)
        
        # Check exact matches first
        if query in region_filtered_mappings:
            symbol = region_filtered_mappings[query]
            company_name = self.get_company_name(symbol)
            suggestions.append({
                'symbol': symbol,
                'name': company_name,
                'match_type': 'exact'
            })
        
        # Check partial matches
        for company_name, symbol in region_filtered_mappings.items():
            if query in company_name and len(suggestions) < limit and self.is_symbol_in_region(symbol, current_region):
                full_name = self.get_company_name(symbol)
                suggestions.append({
                    'symbol': symbol,
                    'name': full_name,
                    'match_type': 'partial'
                })
        
        # Remove duplicates
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion['symbol'] not in seen:
                seen.add(suggestion['symbol'])
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:limit]
    
    def expand_company_mappings(self, text):
        """Expand company mappings by finding new companies in text"""
        # This could be enhanced to automatically detect new companies
        # For now, it uses the predefined mappings
        text = text.upper()
        found_symbols = []
        
        for company_name, symbol in self.company_mappings.items():
            if company_name in text:
                found_symbols.append(symbol)
        
        return found_symbols
    
    def load_company_mappings(self):
        """Load company mappings from database"""
        try:
            return self.db_manager.get_company_mappings()
        except Exception as e:
            print(f"Warning: Failed to load company mappings from database: {e}")
            return {}
    
    def refresh_mappings(self):
        """Refresh company mappings from database"""
        self.company_mappings = self.load_company_mappings()
    
    def is_symbol_in_region(self, symbol, region):
        """Check if a symbol belongs to the specified region"""
        if region == 'US':
            return not symbol.endswith('.NS')
        elif region == 'IN':
            return symbol.endswith('.NS')
        return False
    
    def get_region_filtered_mappings(self, region):
        """Get company mappings filtered by region"""
        filtered_mappings = {}
        for company_name, symbol in self.company_mappings.items():
            if self.is_symbol_in_region(symbol, region):
                filtered_mappings[company_name] = symbol
        return filtered_mappings

# Create a global instance
stock_lookup = StockLookup()
