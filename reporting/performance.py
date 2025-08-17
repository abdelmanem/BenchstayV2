from django.core.cache import cache
from django.db import connection
from django.conf import settings
import time
import logging
import re

# Configure logger
logger = logging.getLogger('benchstay.performance')

class QueryOptimizationMiddleware:
    """Middleware to detect and log slow database queries"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Define threshold for slow queries in seconds
        self.threshold = getattr(settings, 'SLOW_QUERY_THRESHOLD', 0.5)
    
    def __call__(self, request):
        # Reset query log
        connection.queries_log.clear()
        
        # Process the request
        response = self.get_response(request)
        
        # Only analyze queries in DEBUG mode
        if settings.DEBUG:
            self._analyze_queries(request)
            
        return response
    
    def _analyze_queries(self, request):
        """Analyze executed queries for performance issues"""
        total_time = 0
        slow_queries = []
        duplicate_patterns = {}
        
        for query in connection.queries:
            query_time = float(query.get('time', 0))
            total_time += query_time
            sql = query.get('sql', '')
            
            # Check for slow queries
            if query_time > self.threshold:
                slow_queries.append({
                    'sql': sql,
                    'time': query_time,
                })
            
            # Check for duplicate query patterns
            # Normalize the query by removing specific values
            normalized_sql = re.sub(r'\d+', 'N', sql)
            normalized_sql = re.sub(r"'[^']*'", "'X'", normalized_sql)
            
            if normalized_sql in duplicate_patterns:
                duplicate_patterns[normalized_sql]['count'] += 1
            else:
                duplicate_patterns[normalized_sql] = {
                    'count': 1,
                    'example': sql,
                    'time': query_time
                }
        
        # Log slow queries
        if slow_queries:
            logger.warning(f"Slow queries detected for {request.path}:")
            for query in slow_queries:
                logger.warning(f"Time: {query['time']:.4f}s SQL: {query['sql']}")
        
        # Log duplicate queries
        duplicates = {k: v for k, v in duplicate_patterns.items() if v['count'] > 3}
        if duplicates:
            logger.warning(f"Duplicate queries detected for {request.path}:")
            for pattern, data in duplicates.items():
                logger.warning(f"Count: {data['count']}, Time: {data['time']:.4f}s, Example: {data['example']}")
        
        # Log total query count and time
        logger.info(f"Path: {request.path}, Queries: {len(connection.queries)}, Total time: {total_time:.4f}s")


class CacheMiddleware:
    """Middleware to cache expensive views"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Define paths to cache and their timeout in seconds
        self.cache_paths = {
            r'^/reports/competitor-analytics/': 300,  # 5 minutes
            r'^/reports/competitor-charts/': 300,
            r'^/reports/dashboard/': 600,  # 10 minutes
        }
    
    def __call__(self, request):
        # Skip caching for non-GET requests or authenticated users
        if request.method != 'GET' or request.user.is_authenticated:
            return self.get_response(request)
        
        # Check if the path should be cached
        cache_timeout = None
        for path_pattern, timeout in self.cache_paths.items():
            if re.match(path_pattern, request.path):
                cache_timeout = timeout
                break
        
        if cache_timeout is None:
            return self.get_response(request)
        
        # Create a cache key based on the full URL
        cache_key = f"view_cache_{request.build_absolute_uri()}"
        
        # Try to get the response from cache
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            return cached_response
        
        # Generate the response
        response = self.get_response(request)
        
        # Cache the response if it's successful
        if response.status_code == 200:
            cache.set(cache_key, response, cache_timeout)
        
        return response