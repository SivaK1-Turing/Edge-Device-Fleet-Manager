"""
Audit Log Retention Manager

Manages audit log retention policies, archival, compression,
and compliance with data retention requirements.
"""

import asyncio
import gzip
import json
import shutil
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from pathlib import Path
from enum import Enum
import uuid

from ...core.logging import get_logger
from ...persistence.connection.manager import DatabaseManager

logger = get_logger(__name__)


class RetentionPolicy(Enum):
    """Audit log retention policy types."""
    
    IMMEDIATE = "immediate"  # Delete immediately after processing
    SHORT_TERM = "short_term"  # 30 days
    MEDIUM_TERM = "medium_term"  # 90 days
    LONG_TERM = "long_term"  # 1 year
    PERMANENT = "permanent"  # Never delete
    COMPLIANCE = "compliance"  # Based on compliance requirements
    CUSTOM = "custom"  # Custom retention period


class ArchiveFormat(Enum):
    """Archive format types."""
    
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    COMPRESSED_JSON = "json.gz"
    COMPRESSED_CSV = "csv.gz"


class AuditRetentionManager:
    """
    Audit log retention and archival manager.
    
    Manages retention policies, archival processes, compression,
    and compliance with data retention requirements.
    """
    
    def __init__(self, database_manager: Optional[DatabaseManager] = None):
        """
        Initialize audit retention manager.
        
        Args:
            database_manager: Optional database manager for data access
        """
        self.database_manager = database_manager
        self.retention_policies = {}
        self.archive_configs = {}
        self.retention_jobs = {}
        
        # Default configuration
        self.archive_directory = Path("data/archives")
        self.temp_directory = Path("data/temp")
        self.max_archive_size_mb = 100
        self.compression_enabled = True
        
        # Retention periods (in days)
        self.default_retention_periods = {
            RetentionPolicy.IMMEDIATE: 0,
            RetentionPolicy.SHORT_TERM: 30,
            RetentionPolicy.MEDIUM_TERM: 90,
            RetentionPolicy.LONG_TERM: 365,
            RetentionPolicy.PERMANENT: -1,  # Never delete
            RetentionPolicy.COMPLIANCE: 2555,  # 7 years for compliance
        }
        
        self.logger = get_logger(f"{__name__}.AuditRetentionManager")
    
    async def initialize(self) -> None:
        """Initialize audit retention manager."""
        try:
            # Create directories
            self.archive_directory.mkdir(parents=True, exist_ok=True)
            self.temp_directory.mkdir(parents=True, exist_ok=True)
            
            # Load retention policies
            await self._load_retention_policies()
            
            # Load archive configurations
            await self._load_archive_configurations()
            
            # Schedule retention jobs
            await self._schedule_retention_jobs()
            
            self.logger.info("Audit retention manager initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize audit retention manager: {e}")
            raise
    
    async def configure_policy(self, policy_name: str, policy_config: Dict[str, Any]) -> str:
        """
        Configure a retention policy.
        
        Args:
            policy_name: Name of the policy
            policy_config: Policy configuration
            
        Returns:
            Policy ID
        """
        try:
            policy_id = str(uuid.uuid4())
            
            # Validate policy configuration
            validated_config = self._validate_policy_config(policy_config)
            
            # Store policy
            self.retention_policies[policy_id] = {
                'id': policy_id,
                'name': policy_name,
                'config': validated_config,
                'created_at': datetime.now(timezone.utc),
                'enabled': True
            }
            
            # Persist policy if database available
            if self.database_manager:
                await self._persist_retention_policy(policy_id, self.retention_policies[policy_id])
            
            self.logger.info(f"Retention policy configured: {policy_name} ({policy_id})")
            
            return policy_id
            
        except Exception as e:
            self.logger.error(f"Failed to configure retention policy: {e}")
            raise
    
    def _validate_policy_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate retention policy configuration."""
        validated = {}
        
        # Retention period
        retention_type = config.get('retention_type', RetentionPolicy.MEDIUM_TERM)
        if isinstance(retention_type, str):
            retention_type = RetentionPolicy(retention_type)
        
        validated['retention_type'] = retention_type
        
        # Custom retention period (in days)
        if retention_type == RetentionPolicy.CUSTOM:
            retention_days = config.get('retention_days')
            if not isinstance(retention_days, int) or retention_days < 0:
                raise ValueError("Custom retention policy requires valid retention_days")
            validated['retention_days'] = retention_days
        else:
            validated['retention_days'] = self.default_retention_periods[retention_type]
        
        # Archive configuration
        validated['archive_enabled'] = config.get('archive_enabled', True)
        validated['archive_format'] = ArchiveFormat(config.get('archive_format', ArchiveFormat.COMPRESSED_JSON))
        validated['compression_enabled'] = config.get('compression_enabled', True)
        
        # Data types to retain
        validated['data_types'] = config.get('data_types', ['audit_logs', 'alerts', 'telemetry'])
        
        # Compliance settings
        validated['compliance_mode'] = config.get('compliance_mode', False)
        validated['encryption_required'] = config.get('encryption_required', False)
        
        # Schedule
        validated['schedule_enabled'] = config.get('schedule_enabled', True)
        validated['schedule_interval_hours'] = config.get('schedule_interval_hours', 24)
        
        return validated
    
    async def apply_retention_policy(self, policy_id: str, data_type: str = 'audit_logs') -> Dict[str, Any]:
        """
        Apply retention policy to data.
        
        Args:
            policy_id: Retention policy ID
            data_type: Type of data to process
            
        Returns:
            Retention operation result
        """
        try:
            if policy_id not in self.retention_policies:
                raise ValueError(f"Retention policy not found: {policy_id}")
            
            policy = self.retention_policies[policy_id]
            config = policy['config']
            
            start_time = datetime.now(timezone.utc)
            
            # Calculate cutoff date
            retention_days = config['retention_days']
            if retention_days == -1:  # Permanent retention
                self.logger.info(f"Permanent retention policy - no data will be deleted")
                return {
                    'policy_id': policy_id,
                    'data_type': data_type,
                    'records_processed': 0,
                    'records_archived': 0,
                    'records_deleted': 0,
                    'duration_seconds': 0,
                    'status': 'skipped_permanent'
                }
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Get data to process
            data_to_process = await self._get_data_for_retention(data_type, cutoff_date)
            
            records_archived = 0
            records_deleted = 0
            
            if data_to_process:
                # Archive data if enabled
                if config['archive_enabled']:
                    archive_result = await self._archive_data(data_to_process, config, data_type)
                    records_archived = archive_result.get('records_archived', 0)
                
                # Delete old data
                delete_result = await self._delete_old_data(data_to_process, data_type)
                records_deleted = delete_result.get('records_deleted', 0)
            
            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            result = {
                'policy_id': policy_id,
                'policy_name': policy['name'],
                'data_type': data_type,
                'cutoff_date': cutoff_date.isoformat(),
                'records_processed': len(data_to_process),
                'records_archived': records_archived,
                'records_deleted': records_deleted,
                'duration_seconds': duration,
                'status': 'completed'
            }
            
            self.logger.info(f"Retention policy applied: {policy['name']} - {records_processed} processed, {records_archived} archived, {records_deleted} deleted")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to apply retention policy {policy_id}: {e}")
            raise
    
    async def _get_data_for_retention(self, data_type: str, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """Get data that needs retention processing."""
        if not self.database_manager:
            return []
        
        try:
            async with self.database_manager.get_session() as session:
                if data_type == 'audit_logs':
                    from ...persistence.repositories.audit_log import AuditLogRepository
                    repo = AuditLogRepository(session)
                    logs = await repo.get_older_than(cutoff_date)
                    return [self._audit_log_to_dict(log) for log in logs]
                
                elif data_type == 'alerts':
                    from ...persistence.repositories.alert import AlertRepository
                    repo = AlertRepository(session)
                    alerts = await repo.get_older_than(cutoff_date)
                    return [self._alert_to_dict(alert) for alert in alerts]
                
                elif data_type == 'telemetry':
                    from ...persistence.repositories.telemetry import TelemetryRepository
                    repo = TelemetryRepository(session)
                    events = await repo.get_older_than(cutoff_date)
                    return [self._telemetry_to_dict(event) for event in events]
                
                else:
                    self.logger.warning(f"Unknown data type for retention: {data_type}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Failed to get data for retention: {e}")
            return []
    
    async def _archive_data(self, data: List[Dict[str, Any]], config: Dict[str, Any], 
                          data_type: str) -> Dict[str, Any]:
        """Archive data to storage."""
        try:
            if not data:
                return {'records_archived': 0}
            
            # Create archive filename
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            archive_format = config['archive_format']
            filename = f"{data_type}_{timestamp}.{archive_format.value}"
            archive_path = self.archive_directory / filename
            
            # Write data based on format
            if archive_format in [ArchiveFormat.JSON, ArchiveFormat.COMPRESSED_JSON]:
                await self._write_json_archive(data, archive_path, config['compression_enabled'])
            
            elif archive_format in [ArchiveFormat.CSV, ArchiveFormat.COMPRESSED_CSV]:
                await self._write_csv_archive(data, archive_path, config['compression_enabled'])
            
            elif archive_format == ArchiveFormat.PARQUET:
                await self._write_parquet_archive(data, archive_path)
            
            # Encrypt if required
            if config.get('encryption_required', False):
                await self._encrypt_archive(archive_path)
            
            # Verify archive
            archive_size = archive_path.stat().st_size
            
            self.logger.info(f"Data archived: {filename} ({archive_size} bytes, {len(data)} records)")
            
            return {
                'records_archived': len(data),
                'archive_path': str(archive_path),
                'archive_size_bytes': archive_size
            }
            
        except Exception as e:
            self.logger.error(f"Failed to archive data: {e}")
            return {'records_archived': 0, 'error': str(e)}
    
    async def _write_json_archive(self, data: List[Dict[str, Any]], archive_path: Path, 
                                compress: bool) -> None:
        """Write JSON archive."""
        if compress:
            with gzip.open(archive_path, 'wt', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        else:
            with open(archive_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
    
    async def _write_csv_archive(self, data: List[Dict[str, Any]], archive_path: Path, 
                               compress: bool) -> None:
        """Write CSV archive."""
        try:
            import pandas as pd
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            if compress:
                df.to_csv(archive_path, index=False, compression='gzip')
            else:
                df.to_csv(archive_path, index=False)
                
        except ImportError:
            # Fallback to basic CSV writing
            import csv
            
            if not data:
                return
            
            fieldnames = data[0].keys()
            
            if compress:
                with gzip.open(archive_path, 'wt', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
            else:
                with open(archive_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
    
    async def _write_parquet_archive(self, data: List[Dict[str, Any]], archive_path: Path) -> None:
        """Write Parquet archive."""
        try:
            import pandas as pd
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Write Parquet file
            df.to_parquet(archive_path, index=False)
            
        except ImportError:
            raise ImportError("pandas and pyarrow required for Parquet format")
    
    async def _encrypt_archive(self, archive_path: Path) -> None:
        """Encrypt archive file."""
        # Placeholder for encryption implementation
        # In a real implementation, this would use cryptography library
        self.logger.info(f"Archive encryption not implemented: {archive_path}")
    
    async def _delete_old_data(self, data: List[Dict[str, Any]], data_type: str) -> Dict[str, Any]:
        """Delete old data from database."""
        if not self.database_manager or not data:
            return {'records_deleted': 0}
        
        try:
            record_ids = [record['id'] for record in data if 'id' in record]
            
            async with self.database_manager.get_session() as session:
                if data_type == 'audit_logs':
                    from ...persistence.repositories.audit_log import AuditLogRepository
                    repo = AuditLogRepository(session)
                    deleted_count = await repo.delete_by_ids(record_ids)
                
                elif data_type == 'alerts':
                    from ...persistence.repositories.alert import AlertRepository
                    repo = AlertRepository(session)
                    deleted_count = await repo.delete_by_ids(record_ids)
                
                elif data_type == 'telemetry':
                    from ...persistence.repositories.telemetry import TelemetryRepository
                    repo = TelemetryRepository(session)
                    deleted_count = await repo.delete_by_ids(record_ids)
                
                else:
                    deleted_count = 0
                
                await session.commit()
                
                return {'records_deleted': deleted_count}
                
        except Exception as e:
            self.logger.error(f"Failed to delete old data: {e}")
            return {'records_deleted': 0, 'error': str(e)}
    
    def _audit_log_to_dict(self, log) -> Dict[str, Any]:
        """Convert audit log model to dictionary."""
        return {
            'id': str(log.id),
            'action': log.action.value,
            'resource_type': log.resource_type.value,
            'resource_id': log.resource_id,
            'user_id': str(log.user_id) if log.user_id else None,
            'description': log.description,
            'success': log.success,
            'timestamp': log.timestamp.isoformat(),
            'ip_address': log.ip_address,
            'user_agent': log.user_agent
        }
    
    def _alert_to_dict(self, alert) -> Dict[str, Any]:
        """Convert alert model to dictionary."""
        return {
            'id': str(alert.id),
            'title': alert.title,
            'description': alert.description,
            'alert_type': alert.alert_type,
            'severity': alert.severity.value,
            'status': alert.status.value,
            'device_id': str(alert.device_id) if alert.device_id else None,
            'first_occurred': alert.first_occurred.isoformat(),
            'last_occurred': alert.last_occurred.isoformat() if alert.last_occurred else None,
            'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
        }
    
    def _telemetry_to_dict(self, event) -> Dict[str, Any]:
        """Convert telemetry event to dictionary."""
        return {
            'id': str(event.id),
            'device_id': str(event.device_id),
            'event_type': event.event_type.value,
            'event_name': event.event_name,
            'timestamp': event.timestamp.isoformat(),
            'numeric_value': event.numeric_value,
            'string_value': event.string_value,
            'units': event.units,
            'quality_score': event.quality_score,
            'processed': event.processed
        }
    
    async def _load_retention_policies(self) -> None:
        """Load retention policies from database."""
        # Placeholder for loading from database
        pass
    
    async def _load_archive_configurations(self) -> None:
        """Load archive configurations."""
        # Placeholder for loading archive configurations
        pass
    
    async def _schedule_retention_jobs(self) -> None:
        """Schedule automatic retention jobs."""
        # Placeholder for scheduling retention jobs
        pass
    
    async def _persist_retention_policy(self, policy_id: str, policy: Dict[str, Any]) -> None:
        """Persist retention policy to database."""
        # Placeholder for database persistence
        pass
    
    def get_retention_statistics(self) -> Dict[str, Any]:
        """Get retention statistics."""
        policies = list(self.retention_policies.values())
        
        return {
            'total_policies': len(policies),
            'enabled_policies': len([p for p in policies if p.get('enabled', True)]),
            'archive_directory': str(self.archive_directory),
            'archive_directory_size_mb': self._get_directory_size_mb(self.archive_directory),
            'policies': [
                {
                    'id': p['id'],
                    'name': p['name'],
                    'retention_type': p['config']['retention_type'].value,
                    'retention_days': p['config']['retention_days'],
                    'enabled': p.get('enabled', True)
                }
                for p in policies
            ]
        }
    
    def _get_directory_size_mb(self, directory: Path) -> float:
        """Get directory size in MB."""
        try:
            total_size = sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
            return total_size / (1024 * 1024)
        except Exception:
            return 0.0
    
    async def shutdown(self) -> None:
        """Shutdown audit retention manager."""
        # Cancel any running retention jobs
        for job in self.retention_jobs.values():
            if hasattr(job, 'cancel'):
                job.cancel()
        
        self.logger.info("Audit retention manager shutdown complete")
