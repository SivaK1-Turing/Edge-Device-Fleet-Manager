"""
Unit Tests for Alert Manager

Tests the core alert management functionality including alert creation,
lifecycle management, and statistics.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from edge_device_fleet_manager.reports.core.alert_manager import AlertManager
from edge_device_fleet_manager.reports.alerts.severity import AlertSeverity, AlertStatus
from edge_device_fleet_manager.reports.alerts.alert_rules import AlertRule, AlertRuleEngine


class TestAlertManager:
    """Test cases for AlertManager."""
    
    @pytest.fixture
    def alert_manager(self):
        """Create alert manager instance."""
        return AlertManager()
    
    @pytest.fixture
    async def initialized_alert_manager(self):
        """Create and initialize alert manager."""
        manager = AlertManager()
        await manager.initialize()
        return manager
    
    def test_alert_manager_initialization(self, alert_manager):
        """Test alert manager initialization."""
        assert alert_manager is not None
        assert hasattr(alert_manager, 'active_alerts')
        assert hasattr(alert_manager, 'alert_rules')
        assert hasattr(alert_manager, 'alert_history')
        assert hasattr(alert_manager, 'suppression_rules')
        assert hasattr(alert_manager, 'rule_engine')
        
        # Check initial state
        assert len(alert_manager.active_alerts) == 0
        assert len(alert_manager.alert_rules) == 0
        assert len(alert_manager.alert_history) == 0
        assert isinstance(alert_manager.rule_engine, AlertRuleEngine)
    
    @pytest.mark.asyncio
    async def test_create_alert_basic(self, initialized_alert_manager):
        """Test basic alert creation."""
        alert_id = await initialized_alert_manager.create_alert(
            title="Test Alert",
            description="This is a test alert",
            severity=AlertSeverity.MEDIUM,
            alert_type="test"
        )
        
        assert alert_id is not None
        assert alert_id in initialized_alert_manager.active_alerts
        
        alert = initialized_alert_manager.active_alerts[alert_id]
        assert alert['title'] == "Test Alert"
        assert alert['description'] == "This is a test alert"
        assert alert['severity'] == AlertSeverity.MEDIUM
        assert alert['alert_type'] == "test"
        assert alert['status'] == AlertStatus.ACTIVE
        assert alert['occurrence_count'] == 1
    
    @pytest.mark.asyncio
    async def test_create_alert_with_device(self, initialized_alert_manager):
        """Test alert creation with device ID."""
        alert_id = await initialized_alert_manager.create_alert(
            title="Device Alert",
            description="Device-specific alert",
            severity=AlertSeverity.HIGH,
            alert_type="device",
            device_id="device-123"
        )
        
        alert = initialized_alert_manager.active_alerts[alert_id]
        assert alert['device_id'] == "device-123"
    
    @pytest.mark.asyncio
    async def test_create_alert_with_metadata(self, initialized_alert_manager):
        """Test alert creation with metadata."""
        metadata = {"source": "test", "priority": "high"}
        
        alert_id = await initialized_alert_manager.create_alert(
            title="Metadata Alert",
            description="Alert with metadata",
            severity=AlertSeverity.LOW,
            metadata=metadata
        )
        
        alert = initialized_alert_manager.active_alerts[alert_id]
        assert alert['metadata'] == metadata
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, initialized_alert_manager):
        """Test alert acknowledgment."""
        # Create alert
        alert_id = await initialized_alert_manager.create_alert(
            title="Test Alert",
            description="Test alert for acknowledgment",
            severity=AlertSeverity.MEDIUM
        )
        
        # Acknowledge alert
        result = await initialized_alert_manager.acknowledge_alert(
            alert_id=alert_id,
            acknowledged_by="test_user",
            notes="Test acknowledgment"
        )
        
        assert result is True
        
        alert = initialized_alert_manager.active_alerts[alert_id]
        assert alert['status'] == AlertStatus.ACKNOWLEDGED
        assert alert['acknowledged_by'] == "test_user"
        assert alert['acknowledged_at'] is not None
        assert alert['metadata']['acknowledgment_notes'] == "Test acknowledgment"
    
    @pytest.mark.asyncio
    async def test_acknowledge_nonexistent_alert(self, initialized_alert_manager):
        """Test acknowledging non-existent alert."""
        result = await initialized_alert_manager.acknowledge_alert(
            alert_id="nonexistent",
            acknowledged_by="test_user"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_acknowledge_already_acknowledged_alert(self, initialized_alert_manager):
        """Test acknowledging already acknowledged alert."""
        # Create and acknowledge alert
        alert_id = await initialized_alert_manager.create_alert(
            title="Test Alert",
            description="Test alert",
            severity=AlertSeverity.MEDIUM
        )
        
        await initialized_alert_manager.acknowledge_alert(
            alert_id=alert_id,
            acknowledged_by="user1"
        )
        
        # Try to acknowledge again
        result = await initialized_alert_manager.acknowledge_alert(
            alert_id=alert_id,
            acknowledged_by="user2"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_resolve_alert(self, initialized_alert_manager):
        """Test alert resolution."""
        # Create alert
        alert_id = await initialized_alert_manager.create_alert(
            title="Test Alert",
            description="Test alert for resolution",
            severity=AlertSeverity.HIGH
        )
        
        # Resolve alert
        result = await initialized_alert_manager.resolve_alert(
            alert_id=alert_id,
            resolved_by="test_user",
            resolution_notes="Test resolution"
        )
        
        assert result is True
        assert alert_id not in initialized_alert_manager.active_alerts
        
        # Check in history
        assert alert_id in initialized_alert_manager.alert_history
        resolved_alert = initialized_alert_manager.alert_history[alert_id]
        assert resolved_alert['status'] == AlertStatus.RESOLVED
        assert resolved_alert['resolved_by'] == "test_user"
        assert resolved_alert['resolved_at'] is not None
        assert resolved_alert['metadata']['resolution_notes'] == "Test resolution"
    
    @pytest.mark.asyncio
    async def test_resolve_nonexistent_alert(self, initialized_alert_manager):
        """Test resolving non-existent alert."""
        result = await initialized_alert_manager.resolve_alert(
            alert_id="nonexistent",
            resolved_by="test_user"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_escalate_alert(self, initialized_alert_manager):
        """Test alert escalation."""
        # Create alert
        alert_id = await initialized_alert_manager.create_alert(
            title="Test Alert",
            description="Test alert for escalation",
            severity=AlertSeverity.LOW
        )
        
        # Escalate alert
        result = await initialized_alert_manager.escalate_alert(
            alert_id=alert_id,
            escalation_reason="timeout"
        )
        
        assert result is True
        
        alert = initialized_alert_manager.active_alerts[alert_id]
        assert alert['escalated'] is True
        assert alert['escalation_level'] == 1
        assert alert['severity'] == AlertSeverity.MEDIUM  # Should be escalated from LOW
        assert alert['metadata']['escalation_reason'] == "timeout"
    
    @pytest.mark.asyncio
    async def test_escalate_critical_alert(self, initialized_alert_manager):
        """Test escalating already critical alert."""
        # Create critical alert
        alert_id = await initialized_alert_manager.create_alert(
            title="Critical Alert",
            description="Already critical alert",
            severity=AlertSeverity.CRITICAL
        )
        
        # Escalate alert
        result = await initialized_alert_manager.escalate_alert(
            alert_id=alert_id,
            escalation_reason="timeout"
        )
        
        assert result is True
        
        alert = initialized_alert_manager.active_alerts[alert_id]
        assert alert['escalated'] is True
        assert alert['escalation_level'] == 1
        assert alert['severity'] == AlertSeverity.CRITICAL  # Should remain critical
    
    def test_get_active_alerts_empty(self, alert_manager):
        """Test getting active alerts when none exist."""
        alerts = alert_manager.get_active_alerts()
        assert len(alerts) == 0
    
    @pytest.mark.asyncio
    async def test_get_active_alerts_with_data(self, initialized_alert_manager):
        """Test getting active alerts with data."""
        # Create multiple alerts
        alert_ids = []
        for i in range(3):
            alert_id = await initialized_alert_manager.create_alert(
                title=f"Alert {i+1}",
                description=f"Test alert {i+1}",
                severity=AlertSeverity.MEDIUM
            )
            alert_ids.append(alert_id)
        
        alerts = initialized_alert_manager.get_active_alerts()
        assert len(alerts) == 3
        
        # Check sorting (by severity then time)
        for alert in alerts:
            assert alert['severity'] == AlertSeverity.MEDIUM
    
    @pytest.mark.asyncio
    async def test_get_active_alerts_with_filters(self, initialized_alert_manager):
        """Test getting active alerts with filters."""
        # Create alerts with different severities
        await initialized_alert_manager.create_alert(
            title="Critical Alert",
            description="Critical test alert",
            severity=AlertSeverity.CRITICAL,
            alert_type="critical_test"
        )
        
        await initialized_alert_manager.create_alert(
            title="Medium Alert",
            description="Medium test alert",
            severity=AlertSeverity.MEDIUM,
            alert_type="medium_test"
        )
        
        # Filter by severity
        critical_alerts = initialized_alert_manager.get_active_alerts(severity=AlertSeverity.CRITICAL)
        assert len(critical_alerts) == 1
        assert critical_alerts[0]['severity'] == AlertSeverity.CRITICAL
        
        # Filter by type
        critical_type_alerts = initialized_alert_manager.get_active_alerts(alert_type="critical_test")
        assert len(critical_type_alerts) == 1
        assert critical_type_alerts[0]['alert_type'] == "critical_test"
    
    def test_get_alert_statistics_empty(self, alert_manager):
        """Test getting alert statistics when no alerts exist."""
        stats = alert_manager.get_alert_statistics()
        
        assert stats['active_alerts'] == 0
        assert stats['total_alerts_today'] == 0
        assert stats['escalated_alerts'] == 0
        assert stats['suppressed_alerts'] == 0
        assert stats['alert_rules'] == 0
        
        # Check severity distribution
        for severity in AlertSeverity:
            assert stats['severity_distribution'][severity.value] == 0
        
        # Check status distribution
        for status in AlertStatus:
            assert stats['status_distribution'][status.value] == 0
    
    @pytest.mark.asyncio
    async def test_get_alert_statistics_with_data(self, initialized_alert_manager):
        """Test getting alert statistics with data."""
        # Create alerts with different severities
        await initialized_alert_manager.create_alert(
            title="Critical Alert",
            description="Critical alert",
            severity=AlertSeverity.CRITICAL
        )
        
        await initialized_alert_manager.create_alert(
            title="High Alert",
            description="High alert",
            severity=AlertSeverity.HIGH
        )
        
        await initialized_alert_manager.create_alert(
            title="Medium Alert",
            description="Medium alert",
            severity=AlertSeverity.MEDIUM
        )
        
        stats = initialized_alert_manager.get_alert_statistics()
        
        assert stats['active_alerts'] == 3
        assert stats['severity_distribution']['critical'] == 1
        assert stats['severity_distribution']['high'] == 1
        assert stats['severity_distribution']['medium'] == 1
        assert stats['status_distribution']['active'] == 3
    
    @pytest.mark.asyncio
    async def test_find_similar_alert(self, initialized_alert_manager):
        """Test finding similar alerts."""
        # Create first alert
        alert_id1 = await initialized_alert_manager.create_alert(
            title="Duplicate Alert",
            description="First instance",
            severity=AlertSeverity.MEDIUM,
            alert_type="duplicate_test",
            device_id="device-123"
        )
        
        # Create similar alert data
        similar_alert_data = {
            'title': "Duplicate Alert",
            'description': "Second instance",
            'severity': AlertSeverity.MEDIUM,
            'alert_type': "duplicate_test",
            'device_id': "device-123",
            'status': AlertStatus.ACTIVE
        }
        
        # Find similar alert
        similar = await initialized_alert_manager._find_similar_alert(similar_alert_data)
        
        assert similar is not None
        assert similar['id'] == alert_id1
    
    @pytest.mark.asyncio
    async def test_update_existing_alert(self, initialized_alert_manager):
        """Test updating existing similar alert."""
        # Create first alert
        alert_id = await initialized_alert_manager.create_alert(
            title="Duplicate Alert",
            description="First instance",
            severity=AlertSeverity.MEDIUM,
            alert_type="duplicate_test"
        )
        
        original_count = initialized_alert_manager.active_alerts[alert_id]['occurrence_count']
        
        # Create similar alert data
        new_alert_data = {
            'title': "Duplicate Alert",
            'description': "Second instance",
            'severity': AlertSeverity.MEDIUM,
            'alert_type': "duplicate_test",
            'first_occurred': datetime.now(timezone.utc),
            'metadata': {'new_info': 'value'}
        }
        
        # Update existing alert
        updated_id = await initialized_alert_manager._update_existing_alert(alert_id, new_alert_data)
        
        assert updated_id == alert_id
        
        updated_alert = initialized_alert_manager.active_alerts[alert_id]
        assert updated_alert['occurrence_count'] == original_count + 1
        assert updated_alert['description'] == "Second instance"
        assert 'new_info' in updated_alert['metadata']
    
    @pytest.mark.asyncio
    async def test_add_alert_rule(self, initialized_alert_manager):
        """Test adding alert rule."""
        # Create mock rule
        rule = Mock(spec=AlertRule)
        rule.name = "Test Rule"
        
        rule_id = await initialized_alert_manager.add_alert_rule(rule)
        
        assert rule_id is not None
        assert rule_id in initialized_alert_manager.alert_rules
        assert initialized_alert_manager.alert_rules[rule_id] == rule
    
    @pytest.mark.asyncio
    async def test_remove_alert_rule(self, initialized_alert_manager):
        """Test removing alert rule."""
        # Add rule first
        rule = Mock(spec=AlertRule)
        rule.name = "Test Rule"
        rule_id = await initialized_alert_manager.add_alert_rule(rule)
        
        # Remove rule
        result = await initialized_alert_manager.remove_alert_rule(rule_id)
        
        assert result is True
        assert rule_id not in initialized_alert_manager.alert_rules
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_rule(self, initialized_alert_manager):
        """Test removing non-existent rule."""
        result = await initialized_alert_manager.remove_alert_rule("nonexistent")
        assert result is False
    
    def test_add_to_history(self, alert_manager):
        """Test adding alert to history."""
        alert_data = {
            'id': 'test-alert',
            'title': 'Test Alert',
            'first_occurred': datetime.now(timezone.utc).isoformat()
        }
        
        alert_manager._add_to_history(alert_data)
        
        assert 'test-alert' in alert_manager.alert_history
        assert alert_manager.alert_history['test-alert'] == alert_data
    
    def test_add_to_history_limit(self, alert_manager):
        """Test history size limit."""
        # Set small limit for testing
        alert_manager.max_history_entries = 5
        
        # Add more alerts than limit
        for i in range(10):
            alert_data = {
                'id': f'alert-{i}',
                'title': f'Alert {i}',
                'first_occurred': datetime.now(timezone.utc).isoformat()
            }
            alert_manager._add_to_history(alert_data)
        
        # Should only keep the limit
        assert len(alert_manager.alert_history) <= alert_manager.max_history_entries


@pytest.mark.asyncio
async def test_alert_manager_integration():
    """Integration test for alert manager."""
    manager = AlertManager()
    await manager.initialize()
    
    # Create alert
    alert_id = await manager.create_alert(
        title="Integration Test Alert",
        description="Testing full alert lifecycle",
        severity=AlertSeverity.HIGH,
        alert_type="integration_test",
        device_id="device-integration"
    )
    
    # Verify creation
    assert alert_id in manager.active_alerts
    alert = manager.active_alerts[alert_id]
    assert alert['title'] == "Integration Test Alert"
    assert alert['status'] == AlertStatus.ACTIVE
    
    # Acknowledge
    ack_result = await manager.acknowledge_alert(alert_id, "integration_user")
    assert ack_result is True
    assert manager.active_alerts[alert_id]['status'] == AlertStatus.ACKNOWLEDGED
    
    # Resolve
    resolve_result = await manager.resolve_alert(alert_id, "integration_user")
    assert resolve_result is True
    assert alert_id not in manager.active_alerts
    assert alert_id in manager.alert_history
    
    # Check statistics
    stats = manager.get_alert_statistics()
    assert stats['total_alerts_today'] >= 1
