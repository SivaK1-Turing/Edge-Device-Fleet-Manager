"""
Alert Severity and Status Definitions

Defines alert severity levels, status types, and related utilities
for the alert management system.
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class AlertSeverity(Enum):
    """Alert severity levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    @classmethod
    def from_string(cls, severity_str: str) -> 'AlertSeverity':
        """Create AlertSeverity from string."""
        severity_map = {
            'low': cls.LOW,
            'medium': cls.MEDIUM,
            'high': cls.HIGH,
            'critical': cls.CRITICAL,
            'info': cls.LOW,
            'warning': cls.MEDIUM,
            'error': cls.HIGH,
            'fatal': cls.CRITICAL
        }
        
        return severity_map.get(severity_str.lower(), cls.MEDIUM)
    
    @property
    def priority(self) -> int:
        """Get numeric priority for sorting (lower = higher priority)."""
        priority_map = {
            self.CRITICAL: 0,
            self.HIGH: 1,
            self.MEDIUM: 2,
            self.LOW: 3
        }
        return priority_map[self]
    
    @property
    def color_code(self) -> str:
        """Get color code for UI display."""
        color_map = {
            self.CRITICAL: "#FF0000",  # Red
            self.HIGH: "#FF8C00",      # Dark Orange
            self.MEDIUM: "#FFD700",    # Gold
            self.LOW: "#32CD32"        # Lime Green
        }
        return color_map[self]
    
    @property
    def emoji(self) -> str:
        """Get emoji representation."""
        emoji_map = {
            self.CRITICAL: "🚨",
            self.HIGH: "⚠️",
            self.MEDIUM: "⚡",
            self.LOW: "ℹ️"
        }
        return emoji_map[self]
    
    def __lt__(self, other):
        """Compare severity levels for sorting."""
        if not isinstance(other, AlertSeverity):
            return NotImplemented
        return self.priority < other.priority
    
    def __le__(self, other):
        """Compare severity levels for sorting."""
        if not isinstance(other, AlertSeverity):
            return NotImplemented
        return self.priority <= other.priority
    
    def __gt__(self, other):
        """Compare severity levels for sorting."""
        if not isinstance(other, AlertSeverity):
            return NotImplemented
        return self.priority > other.priority
    
    def __ge__(self, other):
        """Compare severity levels for sorting."""
        if not isinstance(other, AlertSeverity):
            return NotImplemented
        return self.priority >= other.priority


class AlertStatus(Enum):
    """Alert status types."""
    
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    EXPIRED = "expired"
    
    @classmethod
    def from_string(cls, status_str: str) -> 'AlertStatus':
        """Create AlertStatus from string."""
        status_map = {
            'active': cls.ACTIVE,
            'acknowledged': cls.ACKNOWLEDGED,
            'resolved': cls.RESOLVED,
            'suppressed': cls.SUPPRESSED,
            'expired': cls.EXPIRED,
            'open': cls.ACTIVE,
            'closed': cls.RESOLVED,
            'ack': cls.ACKNOWLEDGED,
            'acked': cls.ACKNOWLEDGED
        }
        
        return status_map.get(status_str.lower(), cls.ACTIVE)
    
    @property
    def is_active(self) -> bool:
        """Check if status represents an active alert."""
        return self in [self.ACTIVE, self.ACKNOWLEDGED]
    
    @property
    def is_closed(self) -> bool:
        """Check if status represents a closed alert."""
        return self in [self.RESOLVED, self.EXPIRED]
    
    @property
    def color_code(self) -> str:
        """Get color code for UI display."""
        color_map = {
            self.ACTIVE: "#FF4444",      # Red
            self.ACKNOWLEDGED: "#FFA500", # Orange
            self.RESOLVED: "#32CD32",     # Green
            self.SUPPRESSED: "#808080",   # Gray
            self.EXPIRED: "#696969"       # Dim Gray
        }
        return color_map[self]
    
    @property
    def emoji(self) -> str:
        """Get emoji representation."""
        emoji_map = {
            self.ACTIVE: "🔴",
            self.ACKNOWLEDGED: "🟡",
            self.RESOLVED: "🟢",
            self.SUPPRESSED: "⚫",
            self.EXPIRED: "⚪"
        }
        return emoji_map[self]


class AlertCategory(Enum):
    """Alert category types."""
    
    SYSTEM = "system"
    DEVICE = "device"
    NETWORK = "network"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTENANCE = "maintenance"
    USER = "user"
    CUSTOM = "custom"
    
    @property
    def icon(self) -> str:
        """Get icon representation."""
        icon_map = {
            self.SYSTEM: "🖥️",
            self.DEVICE: "📱",
            self.NETWORK: "🌐",
            self.SECURITY: "🔒",
            self.PERFORMANCE: "📊",
            self.MAINTENANCE: "🔧",
            self.USER: "👤",
            self.CUSTOM: "⚙️"
        }
        return icon_map[self]


class AlertPriority(Enum):
    """Alert priority levels (different from severity)."""
    
    P1 = "p1"  # Critical - immediate response required
    P2 = "p2"  # High - response within 1 hour
    P3 = "p3"  # Medium - response within 4 hours
    P4 = "p4"  # Low - response within 24 hours
    P5 = "p5"  # Informational - no immediate response required
    
    @property
    def response_time_hours(self) -> int:
        """Get expected response time in hours."""
        response_map = {
            self.P1: 0,   # Immediate
            self.P2: 1,   # 1 hour
            self.P3: 4,   # 4 hours
            self.P4: 24,  # 24 hours
            self.P5: 168  # 1 week
        }
        return response_map[self]
    
    @classmethod
    def from_severity(cls, severity: AlertSeverity) -> 'AlertPriority':
        """Convert severity to priority."""
        severity_to_priority = {
            AlertSeverity.CRITICAL: cls.P1,
            AlertSeverity.HIGH: cls.P2,
            AlertSeverity.MEDIUM: cls.P3,
            AlertSeverity.LOW: cls.P4
        }
        return severity_to_priority.get(severity, cls.P3)


class AlertMetrics:
    """Alert metrics and statistics utilities."""
    
    @staticmethod
    def calculate_mttr(alerts: List[Dict[str, Any]]) -> float:
        """
        Calculate Mean Time To Resolution (MTTR) in hours.
        
        Args:
            alerts: List of resolved alerts
            
        Returns:
            MTTR in hours
        """
        resolved_alerts = [
            a for a in alerts 
            if a.get('status') == AlertStatus.RESOLVED and 
               a.get('resolved_at') and a.get('first_occurred')
        ]
        
        if not resolved_alerts:
            return 0.0
        
        total_resolution_time = 0.0
        
        for alert in resolved_alerts:
            first_occurred = datetime.fromisoformat(alert['first_occurred'])
            resolved_at = datetime.fromisoformat(alert['resolved_at'])
            resolution_time = (resolved_at - first_occurred).total_seconds() / 3600
            total_resolution_time += resolution_time
        
        return total_resolution_time / len(resolved_alerts)
    
    @staticmethod
    def calculate_mtta(alerts: List[Dict[str, Any]]) -> float:
        """
        Calculate Mean Time To Acknowledgment (MTTA) in minutes.
        
        Args:
            alerts: List of acknowledged alerts
            
        Returns:
            MTTA in minutes
        """
        acknowledged_alerts = [
            a for a in alerts 
            if a.get('acknowledged_at') and a.get('first_occurred')
        ]
        
        if not acknowledged_alerts:
            return 0.0
        
        total_ack_time = 0.0
        
        for alert in acknowledged_alerts:
            first_occurred = datetime.fromisoformat(alert['first_occurred'])
            acknowledged_at = datetime.fromisoformat(alert['acknowledged_at'])
            ack_time = (acknowledged_at - first_occurred).total_seconds() / 60
            total_ack_time += ack_time
        
        return total_ack_time / len(acknowledged_alerts)
    
    @staticmethod
    def calculate_alert_volume_trend(alerts: List[Dict[str, Any]], 
                                   days: int = 7) -> Dict[str, int]:
        """
        Calculate alert volume trend over specified days.
        
        Args:
            alerts: List of alerts
            days: Number of days to analyze
            
        Returns:
            Dictionary with daily alert counts
        """
        from collections import defaultdict
        
        daily_counts = defaultdict(int)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        for alert in alerts:
            alert_date = datetime.fromisoformat(alert['first_occurred'])
            if alert_date >= cutoff_date:
                date_key = alert_date.strftime('%Y-%m-%d')
                daily_counts[date_key] += 1
        
        return dict(daily_counts)
    
    @staticmethod
    def get_top_alert_sources(alerts: List[Dict[str, Any]], 
                            limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top alert sources by volume.
        
        Args:
            alerts: List of alerts
            limit: Maximum number of sources to return
            
        Returns:
            List of top alert sources with counts
        """
        from collections import Counter
        
        # Count by device_id and alert_type
        device_counts = Counter()
        type_counts = Counter()
        
        for alert in alerts:
            if alert.get('device_id'):
                device_counts[alert['device_id']] += 1
            
            alert_type = alert.get('alert_type', 'unknown')
            type_counts[alert_type] += 1
        
        # Combine results
        sources = []
        
        # Top devices
        for device_id, count in device_counts.most_common(limit // 2):
            sources.append({
                'source_type': 'device',
                'source_id': device_id,
                'alert_count': count
            })
        
        # Top alert types
        for alert_type, count in type_counts.most_common(limit // 2):
            sources.append({
                'source_type': 'alert_type',
                'source_id': alert_type,
                'alert_count': count
            })
        
        return sorted(sources, key=lambda x: x['alert_count'], reverse=True)[:limit]
    
    @staticmethod
    def calculate_escalation_rate(alerts: List[Dict[str, Any]]) -> float:
        """
        Calculate alert escalation rate as percentage.
        
        Args:
            alerts: List of alerts
            
        Returns:
            Escalation rate as percentage
        """
        if not alerts:
            return 0.0
        
        escalated_count = len([a for a in alerts if a.get('escalated', False)])
        return (escalated_count / len(alerts)) * 100
    
    @staticmethod
    def get_severity_distribution(alerts: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Get distribution of alerts by severity.
        
        Args:
            alerts: List of alerts
            
        Returns:
            Dictionary with severity counts
        """
        distribution = {severity.value: 0 for severity in AlertSeverity}
        
        for alert in alerts:
            severity = alert.get('severity')
            if isinstance(severity, AlertSeverity):
                distribution[severity.value] += 1
            elif isinstance(severity, str):
                distribution[severity] = distribution.get(severity, 0) + 1
        
        return distribution
