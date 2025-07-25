"""
Alert Rules System

Rule-based alert processing with conditions, actions, and evaluation engine
for automated alert management and response.
"""

import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import re
import json

from ...core.logging import get_logger
from .severity import AlertSeverity, AlertStatus

logger = get_logger(__name__)


class RuleConditionType(Enum):
    """Types of rule conditions."""
    
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    REGEX_MATCH = "regex_match"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    TIME_RANGE = "time_range"
    FREQUENCY = "frequency"


class RuleActionType(Enum):
    """Types of rule actions."""
    
    ESCALATE = "escalate"
    SUPPRESS = "suppress"
    NOTIFY = "notify"
    AUTO_RESOLVE = "auto_resolve"
    SET_PRIORITY = "set_priority"
    ADD_TAG = "add_tag"
    EXECUTE_WEBHOOK = "execute_webhook"
    CREATE_TICKET = "create_ticket"
    CUSTOM_FUNCTION = "custom_function"


@dataclass
class RuleCondition:
    """Individual rule condition."""
    
    field: str
    condition_type: RuleConditionType
    value: Any
    case_sensitive: bool = True
    
    def evaluate(self, alert_data: Dict[str, Any]) -> bool:
        """
        Evaluate condition against alert data.
        
        Args:
            alert_data: Alert data to evaluate
            
        Returns:
            True if condition matches
        """
        try:
            # Get field value from alert data
            field_value = self._get_field_value(alert_data, self.field)
            
            if field_value is None:
                return False
            
            # Apply case sensitivity
            if isinstance(field_value, str) and not self.case_sensitive:
                field_value = field_value.lower()
            
            if isinstance(self.value, str) and not self.case_sensitive:
                compare_value = self.value.lower()
            else:
                compare_value = self.value
            
            # Evaluate based on condition type
            if self.condition_type == RuleConditionType.EQUALS:
                return field_value == compare_value
            
            elif self.condition_type == RuleConditionType.NOT_EQUALS:
                return field_value != compare_value
            
            elif self.condition_type == RuleConditionType.CONTAINS:
                return str(compare_value) in str(field_value)
            
            elif self.condition_type == RuleConditionType.NOT_CONTAINS:
                return str(compare_value) not in str(field_value)
            
            elif self.condition_type == RuleConditionType.GREATER_THAN:
                return float(field_value) > float(compare_value)
            
            elif self.condition_type == RuleConditionType.LESS_THAN:
                return float(field_value) < float(compare_value)
            
            elif self.condition_type == RuleConditionType.GREATER_EQUAL:
                return float(field_value) >= float(compare_value)
            
            elif self.condition_type == RuleConditionType.LESS_EQUAL:
                return float(field_value) <= float(compare_value)
            
            elif self.condition_type == RuleConditionType.REGEX_MATCH:
                pattern = re.compile(str(compare_value))
                return bool(pattern.search(str(field_value)))
            
            elif self.condition_type == RuleConditionType.IN_LIST:
                return field_value in compare_value
            
            elif self.condition_type == RuleConditionType.NOT_IN_LIST:
                return field_value not in compare_value
            
            elif self.condition_type == RuleConditionType.TIME_RANGE:
                return self._evaluate_time_range(field_value, compare_value)
            
            elif self.condition_type == RuleConditionType.FREQUENCY:
                return self._evaluate_frequency(alert_data, compare_value)
            
            else:
                logger.warning(f"Unknown condition type: {self.condition_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def _get_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get field value from nested data using dot notation."""
        try:
            value = data
            for part in field_path.split('.'):
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value
        except Exception:
            return None
    
    def _evaluate_time_range(self, field_value: Any, time_range: Dict[str, Any]) -> bool:
        """Evaluate time range condition."""
        try:
            if isinstance(field_value, str):
                field_time = datetime.fromisoformat(field_value)
            elif isinstance(field_value, datetime):
                field_time = field_value
            else:
                return False
            
            now = datetime.now(timezone.utc)
            
            if 'hours_ago' in time_range:
                cutoff = now - timedelta(hours=time_range['hours_ago'])
                return field_time >= cutoff
            
            elif 'start' in time_range and 'end' in time_range:
                start_time = datetime.fromisoformat(time_range['start'])
                end_time = datetime.fromisoformat(time_range['end'])
                return start_time <= field_time <= end_time
            
            return False
            
        except Exception:
            return False
    
    def _evaluate_frequency(self, alert_data: Dict[str, Any], frequency_config: Dict[str, Any]) -> bool:
        """Evaluate frequency-based condition."""
        # This would require access to alert history
        # For now, return False as placeholder
        return False


@dataclass
class RuleAction:
    """Individual rule action."""
    
    action_type: RuleActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    async def execute(self, alert_data: Dict[str, Any], context: Dict[str, Any] = None) -> bool:
        """
        Execute the action.
        
        Args:
            alert_data: Alert data
            context: Additional execution context
            
        Returns:
            True if action executed successfully
        """
        try:
            if self.action_type == RuleActionType.ESCALATE:
                return await self._execute_escalate(alert_data)
            
            elif self.action_type == RuleActionType.SUPPRESS:
                return await self._execute_suppress(alert_data)
            
            elif self.action_type == RuleActionType.NOTIFY:
                return await self._execute_notify(alert_data)
            
            elif self.action_type == RuleActionType.AUTO_RESOLVE:
                return await self._execute_auto_resolve(alert_data)
            
            elif self.action_type == RuleActionType.SET_PRIORITY:
                return await self._execute_set_priority(alert_data)
            
            elif self.action_type == RuleActionType.ADD_TAG:
                return await self._execute_add_tag(alert_data)
            
            elif self.action_type == RuleActionType.EXECUTE_WEBHOOK:
                return await self._execute_webhook(alert_data)
            
            elif self.action_type == RuleActionType.CREATE_TICKET:
                return await self._execute_create_ticket(alert_data)
            
            elif self.action_type == RuleActionType.CUSTOM_FUNCTION:
                return await self._execute_custom_function(alert_data, context)
            
            else:
                logger.warning(f"Unknown action type: {self.action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing action {self.action_type}: {e}")
            return False
    
    async def _execute_escalate(self, alert_data: Dict[str, Any]) -> bool:
        """Execute escalation action."""
        # Increase severity or escalation level
        current_severity = alert_data.get('severity', AlertSeverity.MEDIUM)
        
        if current_severity == AlertSeverity.LOW:
            alert_data['severity'] = AlertSeverity.MEDIUM
        elif current_severity == AlertSeverity.MEDIUM:
            alert_data['severity'] = AlertSeverity.HIGH
        elif current_severity == AlertSeverity.HIGH:
            alert_data['severity'] = AlertSeverity.CRITICAL
        
        alert_data['escalated'] = True
        alert_data['escalation_level'] = alert_data.get('escalation_level', 0) + 1
        
        return True
    
    async def _execute_suppress(self, alert_data: Dict[str, Any]) -> bool:
        """Execute suppression action."""
        alert_data['suppressed'] = True
        alert_data['status'] = AlertStatus.SUPPRESSED
        return True
    
    async def _execute_notify(self, alert_data: Dict[str, Any]) -> bool:
        """Execute notification action."""
        # This would integrate with notification service
        notification_config = self.parameters.get('notification', {})
        logger.info(f"Sending rule-based notification: {notification_config}")
        return True
    
    async def _execute_auto_resolve(self, alert_data: Dict[str, Any]) -> bool:
        """Execute auto-resolution action."""
        alert_data['status'] = AlertStatus.RESOLVED
        alert_data['resolved_at'] = datetime.now(timezone.utc).isoformat()
        alert_data['resolved_by'] = 'auto-resolve-rule'
        return True
    
    async def _execute_set_priority(self, alert_data: Dict[str, Any]) -> bool:
        """Execute set priority action."""
        priority = self.parameters.get('priority')
        if priority:
            alert_data['priority'] = priority
        return True
    
    async def _execute_add_tag(self, alert_data: Dict[str, Any]) -> bool:
        """Execute add tag action."""
        tag = self.parameters.get('tag')
        if tag:
            tags = alert_data.get('metadata', {}).get('tags', [])
            if tag not in tags:
                tags.append(tag)
            alert_data.setdefault('metadata', {})['tags'] = tags
        return True
    
    async def _execute_webhook(self, alert_data: Dict[str, Any]) -> bool:
        """Execute webhook action."""
        webhook_url = self.parameters.get('url')
        if not webhook_url:
            return False
        
        try:
            import aiohttp
            
            payload = {
                'alert': alert_data,
                'action': 'rule_triggered',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    return response.status < 400
                    
        except Exception as e:
            logger.error(f"Webhook execution failed: {e}")
            return False
    
    async def _execute_create_ticket(self, alert_data: Dict[str, Any]) -> bool:
        """Execute create ticket action."""
        # This would integrate with ticketing system
        ticket_config = self.parameters.get('ticket', {})
        logger.info(f"Creating ticket for alert: {alert_data['id']}")
        return True
    
    async def _execute_custom_function(self, alert_data: Dict[str, Any], 
                                     context: Dict[str, Any] = None) -> bool:
        """Execute custom function action."""
        function_name = self.parameters.get('function')
        if not function_name:
            return False
        
        # This would execute a custom function
        logger.info(f"Executing custom function: {function_name}")
        return True


@dataclass
class AlertRule:
    """Complete alert rule with conditions and actions."""
    
    name: str
    description: str
    conditions: List[RuleCondition]
    actions: List[RuleAction]
    enabled: bool = True
    priority: int = 100
    condition_logic: str = "AND"  # "AND" or "OR"
    cooldown_minutes: int = 0
    max_executions: Optional[int] = None
    
    # Runtime state
    execution_count: int = field(default=0, init=False)
    last_executed: Optional[datetime] = field(default=None, init=False)
    
    def evaluate_conditions(self, alert_data: Dict[str, Any]) -> bool:
        """
        Evaluate all conditions against alert data.
        
        Args:
            alert_data: Alert data to evaluate
            
        Returns:
            True if conditions match
        """
        if not self.conditions:
            return True
        
        results = [condition.evaluate(alert_data) for condition in self.conditions]
        
        if self.condition_logic.upper() == "OR":
            return any(results)
        else:  # Default to AND
            return all(results)
    
    def can_execute(self) -> bool:
        """
        Check if rule can be executed based on cooldown and limits.
        
        Returns:
            True if rule can execute
        """
        if not self.enabled:
            return False
        
        # Check execution limit
        if self.max_executions and self.execution_count >= self.max_executions:
            return False
        
        # Check cooldown
        if self.cooldown_minutes > 0 and self.last_executed:
            cooldown_end = self.last_executed + timedelta(minutes=self.cooldown_minutes)
            if datetime.now(timezone.utc) < cooldown_end:
                return False
        
        return True
    
    async def execute_actions(self, alert_data: Dict[str, Any], 
                            context: Dict[str, Any] = None) -> List[bool]:
        """
        Execute all actions for this rule.
        
        Args:
            alert_data: Alert data
            context: Additional execution context
            
        Returns:
            List of action execution results
        """
        if not self.can_execute():
            return []
        
        results = []
        for action in self.actions:
            result = await action.execute(alert_data, context)
            results.append(result)
        
        # Update execution state
        self.execution_count += 1
        self.last_executed = datetime.now(timezone.utc)
        
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary representation."""
        return {
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled,
            'priority': self.priority,
            'condition_logic': self.condition_logic,
            'cooldown_minutes': self.cooldown_minutes,
            'max_executions': self.max_executions,
            'execution_count': self.execution_count,
            'last_executed': self.last_executed.isoformat() if self.last_executed else None,
            'conditions': [
                {
                    'field': c.field,
                    'condition_type': c.condition_type.value,
                    'value': c.value,
                    'case_sensitive': c.case_sensitive
                }
                for c in self.conditions
            ],
            'actions': [
                {
                    'action_type': a.action_type.value,
                    'parameters': a.parameters
                }
                for a in self.actions
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertRule':
        """Create rule from dictionary representation."""
        conditions = []
        for c_data in data.get('conditions', []):
            condition = RuleCondition(
                field=c_data['field'],
                condition_type=RuleConditionType(c_data['condition_type']),
                value=c_data['value'],
                case_sensitive=c_data.get('case_sensitive', True)
            )
            conditions.append(condition)
        
        actions = []
        for a_data in data.get('actions', []):
            action = RuleAction(
                action_type=RuleActionType(a_data['action_type']),
                parameters=a_data.get('parameters', {})
            )
            actions.append(action)
        
        rule = cls(
            name=data['name'],
            description=data['description'],
            conditions=conditions,
            actions=actions,
            enabled=data.get('enabled', True),
            priority=data.get('priority', 100),
            condition_logic=data.get('condition_logic', 'AND'),
            cooldown_minutes=data.get('cooldown_minutes', 0),
            max_executions=data.get('max_executions')
        )
        
        # Restore runtime state
        rule.execution_count = data.get('execution_count', 0)
        if data.get('last_executed'):
            rule.last_executed = datetime.fromisoformat(data['last_executed'])
        
        return rule


class AlertRuleEngine:
    """Engine for evaluating and executing alert rules."""
    
    def __init__(self):
        """Initialize rule engine."""
        self.rules = {}
        self.custom_functions = {}
        
        self.logger = get_logger(f"{__name__}.AlertRuleEngine")
    
    def add_rule(self, rule: AlertRule) -> str:
        """
        Add a rule to the engine.
        
        Args:
            rule: Alert rule to add
            
        Returns:
            Rule ID
        """
        import uuid
        rule_id = str(uuid.uuid4())
        self.rules[rule_id] = rule
        
        self.logger.info(f"Added alert rule: {rule_id} - {rule.name}")
        return rule_id
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a rule from the engine.
        
        Args:
            rule_id: Rule ID to remove
            
        Returns:
            True if removed successfully
        """
        if rule_id in self.rules:
            rule_name = self.rules[rule_id].name
            del self.rules[rule_id]
            self.logger.info(f"Removed alert rule: {rule_id} - {rule_name}")
            return True
        
        return False
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """
        Get a rule by ID.
        
        Args:
            rule_id: Rule ID
            
        Returns:
            Alert rule or None
        """
        return self.rules.get(rule_id)
    
    def list_rules(self, enabled_only: bool = False) -> List[AlertRule]:
        """
        List all rules.
        
        Args:
            enabled_only: Only return enabled rules
            
        Returns:
            List of alert rules
        """
        rules = list(self.rules.values())
        
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        
        # Sort by priority
        rules.sort(key=lambda r: r.priority)
        
        return rules
    
    async def evaluate_rule(self, rule: AlertRule, alert_data: Dict[str, Any]) -> bool:
        """
        Evaluate a single rule against alert data.
        
        Args:
            rule: Rule to evaluate
            alert_data: Alert data
            
        Returns:
            True if rule matches
        """
        try:
            return rule.evaluate_conditions(alert_data)
        except Exception as e:
            self.logger.error(f"Error evaluating rule {rule.name}: {e}")
            return False
    
    async def process_alert(self, alert_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process alert against all rules.
        
        Args:
            alert_data: Alert data to process
            
        Returns:
            List of rule execution results
        """
        results = []
        
        # Get enabled rules sorted by priority
        rules = self.list_rules(enabled_only=True)
        
        for rule in rules:
            try:
                if await self.evaluate_rule(rule, alert_data):
                    action_results = await rule.execute_actions(alert_data)
                    
                    result = {
                        'rule_name': rule.name,
                        'rule_id': id(rule),  # Use object id as temporary ID
                        'matched': True,
                        'actions_executed': len(action_results),
                        'actions_successful': sum(action_results),
                        'execution_time': datetime.now(timezone.utc).isoformat()
                    }
                    
                    results.append(result)
                    
                    self.logger.info(f"Rule executed: {rule.name} for alert {alert_data.get('id')}")
                
            except Exception as e:
                self.logger.error(f"Error processing rule {rule.name}: {e}")
                
                result = {
                    'rule_name': rule.name,
                    'rule_id': id(rule),
                    'matched': False,
                    'error': str(e),
                    'execution_time': datetime.now(timezone.utc).isoformat()
                }
                
                results.append(result)
        
        return results
    
    def register_custom_function(self, name: str, function: Callable) -> None:
        """
        Register a custom function for use in rules.
        
        Args:
            name: Function name
            function: Function to register
        """
        self.custom_functions[name] = function
        self.logger.info(f"Registered custom function: {name}")
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """
        Get rule engine statistics.
        
        Returns:
            Statistics dictionary
        """
        rules = list(self.rules.values())
        enabled_rules = [r for r in rules if r.enabled]
        
        total_executions = sum(r.execution_count for r in rules)
        
        return {
            'total_rules': len(rules),
            'enabled_rules': len(enabled_rules),
            'disabled_rules': len(rules) - len(enabled_rules),
            'total_executions': total_executions,
            'custom_functions': len(self.custom_functions),
            'rules_by_priority': {
                str(priority): len([r for r in rules if r.priority == priority])
                for priority in sorted(set(r.priority for r in rules))
            }
        }
