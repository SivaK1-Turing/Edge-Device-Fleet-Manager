"""
Data Adapter

Connects the persistence layer to the visualization engine,
providing data transformation and caching capabilities.
"""

import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

from ...core.logging import get_logger
from ...persistence.connection.manager import DatabaseManager
from ...persistence.repositories.device import DeviceRepository
from ...persistence.repositories.telemetry import TelemetryRepository
from ...persistence.repositories.analytics import AnalyticsRepository

logger = get_logger(__name__)


class DataAdapter:
    """
    Data adapter for connecting persistence layer to visualization engine.
    
    Provides data loading, transformation, caching, and real-time
    streaming capabilities for visualizations.
    """
    
    def __init__(self, database_manager: Optional[DatabaseManager] = None):
        """
        Initialize data adapter.
        
        Args:
            database_manager: Optional database manager instance
        """
        self.database_manager = database_manager
        self._cache = {}
        self._cache_ttl = {}
        self._transformers = {}
        self._real_time_streams = {}
        
        self.logger = get_logger(f"{__name__}.DataAdapter")
    
    async def initialize(self) -> None:
        """Initialize the data adapter."""
        self.logger.info("Data adapter initialized")
    
    async def load_data(self, data_source: Union[str, Dict[str, Any]]) -> Any:
        """
        Load data from various sources.
        
        Args:
            data_source: Data source specification
            
        Returns:
            Loaded and transformed data
        """
        try:
            if isinstance(data_source, str):
                # Handle string data sources (queries, file paths, etc.)
                return await self._load_from_string_source(data_source)
            elif isinstance(data_source, dict):
                # Handle dictionary data sources
                return await self._load_from_dict_source(data_source)
            else:
                # Return data as-is if it's already processed
                return data_source
                
        except Exception as e:
            self.logger.error(f"Failed to load data: {e}")
            raise
    
    async def _load_from_string_source(self, source: str) -> Any:
        """Load data from string source specification."""
        # Check cache first
        cached_data = self._get_cached_data(source)
        if cached_data is not None:
            return cached_data
        
        if source.startswith('query:'):
            # Database query
            query = source[6:]  # Remove 'query:' prefix
            data = await self._execute_query(query)
        elif source.startswith('devices:'):
            # Device data
            filter_spec = source[8:]  # Remove 'devices:' prefix
            data = await self._load_device_data(filter_spec)
        elif source.startswith('telemetry:'):
            # Telemetry data
            filter_spec = source[10:]  # Remove 'telemetry:' prefix
            data = await self._load_telemetry_data(filter_spec)
        elif source.startswith('analytics:'):
            # Analytics data
            filter_spec = source[10:]  # Remove 'analytics:' prefix
            data = await self._load_analytics_data(filter_spec)
        elif source.startswith('file:'):
            # File data
            file_path = source[5:]  # Remove 'file:' prefix
            data = await self._load_file_data(file_path)
        else:
            raise ValueError(f"Unknown string data source format: {source}")
        
        # Cache the data
        self._cache_data(source, data)
        
        return data
    
    async def _load_from_dict_source(self, source: Dict[str, Any]) -> Any:
        """Load data from dictionary source specification."""
        source_type = source.get('type', 'unknown')
        
        if source_type == 'devices':
            return await self._load_device_data_dict(source)
        elif source_type == 'telemetry':
            return await self._load_telemetry_data_dict(source)
        elif source_type == 'analytics':
            return await self._load_analytics_data_dict(source)
        elif source_type == 'query':
            return await self._execute_query(source.get('query', ''))
        elif source_type == 'static':
            return source.get('data', {})
        elif source_type == 'aggregated':
            return await self._load_aggregated_data(source)
        else:
            raise ValueError(f"Unknown dictionary data source type: {source_type}")
    
    async def _load_device_data(self, filter_spec: str) -> pd.DataFrame:
        """Load device data with filtering."""
        if not self.database_manager:
            raise ValueError("Database manager not available")
        
        async with self.database_manager.get_session() as session:
            device_repo = DeviceRepository(session)
            
            if filter_spec == 'all':
                devices = await device_repo.get_all()
            elif filter_spec == 'online':
                devices = await device_repo.get_online_devices()
            elif filter_spec.startswith('type:'):
                device_type = filter_spec[5:]
                devices = await device_repo.get_by_type(device_type)
            else:
                # Default to all devices
                devices = await device_repo.get_all()
            
            # Convert to DataFrame
            data = []
            for device in devices:
                data.append({
                    'id': str(device.id),
                    'name': device.name,
                    'type': device.device_type.value,
                    'status': device.status.value,
                    'health_score': device.health_score,
                    'battery_level': device.battery_level,
                    'last_seen': device.last_seen,
                    'created_at': device.created_at
                })
            
            return pd.DataFrame(data)
    
    async def _load_device_data_dict(self, source: Dict[str, Any]) -> pd.DataFrame:
        """Load device data from dictionary specification."""
        if not self.database_manager:
            raise ValueError("Database manager not available")
        
        async with self.database_manager.get_session() as session:
            device_repo = DeviceRepository(session)
            
            # Apply filters
            filters = source.get('filters', {})
            limit = source.get('limit', 100)
            
            devices = await device_repo.get_filtered(filters, limit=limit)
            
            # Convert to DataFrame
            data = []
            for device in devices:
                data.append({
                    'id': str(device.id),
                    'name': device.name,
                    'type': device.device_type.value,
                    'status': device.status.value,
                    'health_score': device.health_score,
                    'battery_level': device.battery_level,
                    'last_seen': device.last_seen,
                    'created_at': device.created_at
                })
            
            return pd.DataFrame(data)
    
    async def _load_telemetry_data(self, filter_spec: str) -> pd.DataFrame:
        """Load telemetry data with filtering."""
        if not self.database_manager:
            raise ValueError("Database manager not available")
        
        async with self.database_manager.get_session() as session:
            telemetry_repo = TelemetryRepository(session)
            
            # Parse filter specification
            if filter_spec == 'recent':
                # Last hour of data
                since = datetime.now(timezone.utc) - timedelta(hours=1)
                telemetry_events = await telemetry_repo.get_recent(since=since, limit=1000)
            elif filter_spec.startswith('device:'):
                device_id = filter_spec[7:]
                telemetry_events = await telemetry_repo.get_by_device(device_id, limit=1000)
            elif filter_spec.startswith('type:'):
                event_type = filter_spec[5:]
                telemetry_events = await telemetry_repo.get_by_type(event_type, limit=1000)
            else:
                # Default to recent data
                since = datetime.now(timezone.utc) - timedelta(hours=1)
                telemetry_events = await telemetry_repo.get_recent(since=since, limit=1000)
            
            # Convert to DataFrame
            data = []
            for event in telemetry_events:
                data.append({
                    'id': str(event.id),
                    'device_id': str(event.device_id),
                    'event_type': event.event_type.value,
                    'event_name': event.event_name,
                    'timestamp': event.timestamp,
                    'numeric_value': event.numeric_value,
                    'string_value': event.string_value,
                    'units': event.units,
                    'quality_score': event.quality_score,
                    'processed': event.processed
                })
            
            return pd.DataFrame(data)
    
    async def _load_telemetry_data_dict(self, source: Dict[str, Any]) -> pd.DataFrame:
        """Load telemetry data from dictionary specification."""
        if not self.database_manager:
            raise ValueError("Database manager not available")
        
        async with self.database_manager.get_session() as session:
            telemetry_repo = TelemetryRepository(session)
            
            # Apply filters
            device_id = source.get('device_id')
            event_type = source.get('event_type')
            start_time = source.get('start_time')
            end_time = source.get('end_time')
            limit = source.get('limit', 1000)
            
            # Build query parameters
            query_params = {}
            if device_id:
                query_params['device_id'] = device_id
            if event_type:
                query_params['event_type'] = event_type
            if start_time:
                query_params['start_time'] = start_time
            if end_time:
                query_params['end_time'] = end_time
            
            telemetry_events = await telemetry_repo.get_filtered(query_params, limit=limit)
            
            # Convert to DataFrame
            data = []
            for event in telemetry_events:
                data.append({
                    'id': str(event.id),
                    'device_id': str(event.device_id),
                    'event_type': event.event_type.value,
                    'event_name': event.event_name,
                    'timestamp': event.timestamp,
                    'numeric_value': event.numeric_value,
                    'string_value': event.string_value,
                    'units': event.units,
                    'quality_score': event.quality_score,
                    'processed': event.processed
                })
            
            return pd.DataFrame(data)
    
    async def _load_analytics_data(self, filter_spec: str) -> pd.DataFrame:
        """Load analytics data with filtering."""
        if not self.database_manager:
            raise ValueError("Database manager not available")
        
        async with self.database_manager.get_session() as session:
            analytics_repo = AnalyticsRepository(session)
            
            if filter_spec == 'recent':
                # Recent analytics
                since = datetime.now(timezone.utc) - timedelta(days=1)
                analytics = await analytics_repo.get_recent(since=since, limit=100)
            elif filter_spec.startswith('type:'):
                analytics_type = filter_spec[5:]
                analytics = await analytics_repo.get_by_type(analytics_type, limit=100)
            else:
                # Default to recent
                since = datetime.now(timezone.utc) - timedelta(days=1)
                analytics = await analytics_repo.get_recent(since=since, limit=100)
            
            # Convert to DataFrame
            data = []
            for analytic in analytics:
                data.append({
                    'id': str(analytic.id),
                    'analytics_type': analytic.analytics_type.value,
                    'metric_name': analytic.metric_name,
                    'metric_type': analytic.metric_type.value,
                    'period_start': analytic.period_start,
                    'period_end': analytic.period_end,
                    'numeric_value': analytic.numeric_value,
                    'granularity': analytic.granularity,
                    'scope': analytic.scope,
                    'created_at': analytic.created_at
                })
            
            return pd.DataFrame(data)
    
    async def _load_analytics_data_dict(self, source: Dict[str, Any]) -> pd.DataFrame:
        """Load analytics data from dictionary specification."""
        if not self.database_manager:
            raise ValueError("Database manager not available")
        
        async with self.database_manager.get_session() as session:
            analytics_repo = AnalyticsRepository(session)
            
            # Apply filters
            filters = source.get('filters', {})
            limit = source.get('limit', 100)
            
            analytics = await analytics_repo.get_filtered(filters, limit=limit)
            
            # Convert to DataFrame
            data = []
            for analytic in analytics:
                data.append({
                    'id': str(analytic.id),
                    'analytics_type': analytic.analytics_type.value,
                    'metric_name': analytic.metric_name,
                    'metric_type': analytic.metric_type.value,
                    'period_start': analytic.period_start,
                    'period_end': analytic.period_end,
                    'numeric_value': analytic.numeric_value,
                    'granularity': analytic.granularity,
                    'scope': analytic.scope,
                    'created_at': analytic.created_at
                })
            
            return pd.DataFrame(data)
    
    async def _load_aggregated_data(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """Load and aggregate data from multiple sources."""
        aggregation_type = source.get('aggregation', 'merge')
        sources = source.get('sources', [])
        
        if not sources:
            return {}
        
        # Load data from all sources
        datasets = []
        for sub_source in sources:
            data = await self.load_data(sub_source)
            datasets.append(data)
        
        # Aggregate based on type
        if aggregation_type == 'merge':
            # Merge DataFrames
            if all(isinstance(df, pd.DataFrame) for df in datasets):
                return pd.concat(datasets, ignore_index=True)
            else:
                # Merge dictionaries
                result = {}
                for dataset in datasets:
                    if isinstance(dataset, dict):
                        result.update(dataset)
                return result
        elif aggregation_type == 'join':
            # Join DataFrames on common columns
            if len(datasets) >= 2 and all(isinstance(df, pd.DataFrame) for df in datasets):
                result = datasets[0]
                for df in datasets[1:]:
                    # Find common columns for joining
                    common_cols = list(set(result.columns) & set(df.columns))
                    if common_cols:
                        result = result.merge(df, on=common_cols, how='outer')
                return result
        
        return datasets[0] if datasets else {}
    
    async def _execute_query(self, query: str) -> pd.DataFrame:
        """Execute raw SQL query and return DataFrame."""
        if not self.database_manager:
            raise ValueError("Database manager not available")
        
        async with self.database_manager.get_session() as session:
            result = await session.execute(query)
            rows = result.fetchall()
            columns = result.keys()
            
            return pd.DataFrame(rows, columns=columns)
    
    async def _load_file_data(self, file_path: str) -> Any:
        """Load data from file."""
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        elif file_path.endswith('.json'):
            import json
            with open(file_path, 'r') as f:
                return json.load(f)
        elif file_path.endswith('.xlsx'):
            return pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
    
    def _get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data if still valid."""
        if key not in self._cache:
            return None
        
        # Check TTL
        if key in self._cache_ttl:
            if datetime.now(timezone.utc) > self._cache_ttl[key]:
                del self._cache[key]
                del self._cache_ttl[key]
                return None
        
        return self._cache[key]
    
    def _cache_data(self, key: str, data: Any, ttl_seconds: int = 300) -> None:
        """Cache data with TTL."""
        self._cache[key] = data
        self._cache_ttl[key] = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._cache_ttl.clear()
        self.logger.info("Data cache cleared")
    
    async def shutdown(self) -> None:
        """Shutdown the data adapter."""
        self.clear_cache()
        self.logger.info("Data adapter shutdown complete")
