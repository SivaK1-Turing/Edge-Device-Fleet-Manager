"""
Unit tests for the CLI system.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from edge_device_fleet_manager.cli.main import cli
from edge_device_fleet_manager.cli.types import DeviceIDType, IPAddressType, SubnetType


@pytest.mark.unit
class TestCLI:
    """Test cases for the main CLI."""
    
    def test_cli_help(self, cli_runner):
        """Test CLI help command."""
        result = cli_runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "Edge Device Fleet Manager" in result.output
        assert "Production-grade IoT device management" in result.output
    
    @patch('edge_device_fleet_manager.cli.main.get_config')
    @patch('edge_device_fleet_manager.cli.main.setup_logging')
    @patch('edge_device_fleet_manager.cli.main.initialize_plugin_system')
    def test_cli_initialization(self, mock_init_plugins, mock_setup_logging, mock_get_config, cli_runner, test_config):
        """Test CLI initialization process."""
        mock_get_config.return_value = test_config
        mock_plugin_loader = AsyncMock()
        mock_plugin_loader.get_loaded_plugins.return_value = {}
        mock_init_plugins.return_value = mock_plugin_loader
        
        result = cli_runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        mock_get_config.assert_called_once()
        mock_setup_logging.assert_called_once_with(test_config)
    
    @patch('edge_device_fleet_manager.cli.main.get_config')
    def test_config_command_table_format(self, mock_get_config, cli_runner, test_config):
        """Test config command with table format."""
        mock_get_config.return_value = test_config
        
        with patch('edge_device_fleet_manager.cli.main.initialize_plugin_system'):
            result = cli_runner.invoke(cli, ['config', '--format', 'table'])
        
        assert result.exit_code == 0
        assert "Edge Fleet Manager Configuration" in result.output
    
    @patch('edge_device_fleet_manager.cli.main.get_config')
    def test_config_command_json_format(self, mock_get_config, cli_runner, test_config):
        """Test config command with JSON format."""
        mock_get_config.return_value = test_config
        
        with patch('edge_device_fleet_manager.cli.main.initialize_plugin_system'):
            result = cli_runner.invoke(cli, ['config', '--format', 'json'])
        
        assert result.exit_code == 0
        # Should be valid JSON
        json.loads(result.output)
    
    @patch('edge_device_fleet_manager.cli.main.get_config')
    def test_plugins_command_no_plugins(self, mock_get_config, cli_runner, test_config):
        """Test plugins command when no plugins are loaded."""
        mock_get_config.return_value = test_config
        
        with patch('edge_device_fleet_manager.cli.main.initialize_plugin_system') as mock_init:
            mock_plugin_loader = MagicMock()
            mock_plugin_loader.get_loaded_plugins.return_value = {}
            mock_init.return_value = mock_plugin_loader
            
            result = cli_runner.invoke(cli, ['plugins'])
        
        assert result.exit_code == 0
        assert "No plugins loaded" in result.output
    
    @patch('edge_device_fleet_manager.cli.main.get_config')
    def test_plugins_command_with_plugins(self, mock_get_config, cli_runner, test_config):
        """Test plugins command when plugins are loaded."""
        mock_get_config.return_value = test_config
        
        # Create mock plugin
        mock_plugin = MagicMock()
        mock_plugin.metadata.name = "test_plugin"
        mock_plugin.metadata.version = "1.0.0"
        mock_plugin.metadata.description = "Test plugin"
        mock_plugin.get_commands.return_value = []
        
        with patch('edge_device_fleet_manager.cli.main.initialize_plugin_system') as mock_init:
            mock_plugin_loader = MagicMock()
            mock_plugin_loader.get_loaded_plugins.return_value = {"test": mock_plugin}
            mock_init.return_value = mock_plugin_loader
            
            result = cli_runner.invoke(cli, ['plugins'])
        
        assert result.exit_code == 0
        assert "Loaded Plugins" in result.output
        assert "test_plugin" in result.output
    
    @patch('edge_device_fleet_manager.cli.main.get_config')
    def test_reload_plugin_command(self, mock_get_config, cli_runner, test_config):
        """Test reload-plugin command."""
        mock_get_config.return_value = test_config
        
        with patch('edge_device_fleet_manager.cli.main.initialize_plugin_system') as mock_init:
            mock_plugin_loader = AsyncMock()
            mock_plugin_loader.plugin_files = {"test_plugin": "/path/to/plugin.py"}
            mock_result = MagicMock()
            mock_result.success = True
            mock_plugin_loader.reload_plugin_from_file.return_value = mock_result
            mock_init.return_value = mock_plugin_loader
            
            result = cli_runner.invoke(cli, ['reload-plugin', '--name', 'test_plugin'])
        
        assert result.exit_code == 0
        assert "reloaded successfully" in result.output
    
    @patch('edge_device_fleet_manager.cli.main.get_config')
    @patch('IPython.start_ipython')
    def test_debug_repl_command(self, mock_ipython, mock_get_config, cli_runner, test_config):
        """Test debug-repl command."""
        mock_get_config.return_value = test_config
        
        with patch('edge_device_fleet_manager.cli.main.initialize_plugin_system'):
            result = cli_runner.invoke(cli, ['debug-repl'])
        
        assert result.exit_code == 0
        mock_ipython.assert_called_once()
    
    def test_cli_error_handling(self, cli_runner):
        """Test CLI error handling."""
        with patch('edge_device_fleet_manager.cli.main.get_config', side_effect=Exception("Test error")):
            result = cli_runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 1
        assert "Error initializing CLI" in result.output


@pytest.mark.unit
class TestCustomClickTypes:
    """Test cases for custom Click parameter types."""
    
    def test_device_id_type_valid(self):
        """Test DeviceIDType with valid device IDs."""
        device_type = DeviceIDType(
            pattern=r'^[a-zA-Z0-9][a-zA-Z0-9\-_]*[a-zA-Z0-9]$',
            min_length=3,
            max_length=64
        )
        
        # Test valid device IDs
        valid_ids = [
            "device-001",
            "sensor_temp_01",
            "gateway123",
            "abc"
        ]
        
        for device_id in valid_ids:
            result = device_type.convert(device_id, None, None)
            assert result == device_id
    
    def test_device_id_type_invalid_length(self):
        """Test DeviceIDType with invalid lengths."""
        device_type = DeviceIDType(min_length=3, max_length=10)
        
        # Test too short
        with pytest.raises(Exception):  # Click will raise an exception
            device_type.convert("ab", None, None)
        
        # Test too long
        with pytest.raises(Exception):
            device_type.convert("a" * 20, None, None)
    
    def test_device_id_type_invalid_pattern(self):
        """Test DeviceIDType with invalid patterns."""
        device_type = DeviceIDType(
            pattern=r'^[a-zA-Z0-9][a-zA-Z0-9\-_]*[a-zA-Z0-9]$'
        )
        
        # Test invalid patterns
        invalid_ids = [
            "-invalid",  # Starts with dash
            "invalid-",  # Ends with dash
            "inv@lid",   # Contains invalid character
            "inv..alid"  # Contains consecutive dots
        ]
        
        for device_id in invalid_ids:
            with pytest.raises(Exception):
                device_type.convert(device_id, None, None)
    
    @patch('httpx.Client')
    def test_device_id_type_schema_validation(self, mock_httpx_client):
        """Test DeviceIDType with schema validation."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "type": "string",
            "pattern": "^[a-zA-Z0-9][a-zA-Z0-9\\-_]*[a-zA-Z0-9]$",
            "minLength": 3,
            "maxLength": 64
        }
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client
        
        device_type = DeviceIDType(
            schema_url="https://api.example.com/schema.json"
        )
        
        # Should successfully validate
        result = device_type.convert("valid-device-id", None, None)
        assert result == "valid-device-id"
    
    def test_device_id_type_autocompletion(self):
        """Test DeviceIDType shell autocompletion."""
        device_type = DeviceIDType()
        
        # Mock the _get_device_ids method
        with patch.object(device_type, '_get_device_ids', return_value=[
            "device-001", "device-002", "sensor-temp-01"
        ]):
            completions = device_type.shell_complete(None, None, "device")
            
            # Should return matching completions
            completion_values = [c.value for c in completions]
            assert "device-001" in completion_values
            assert "device-002" in completion_values
            assert "sensor-temp-01" not in completion_values  # Doesn't start with "device"
    
    def test_ip_address_type_valid_ipv4(self):
        """Test IPAddressType with valid IPv4 addresses."""
        ip_type = IPAddressType()
        
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "127.0.0.1",
            "255.255.255.255"
        ]
        
        for ip in valid_ips:
            result = ip_type.convert(ip, None, None)
            assert result == ip
    
    def test_ip_address_type_invalid_ipv4(self):
        """Test IPAddressType with invalid IPv4 addresses."""
        ip_type = IPAddressType()
        
        invalid_ips = [
            "256.1.1.1",      # Invalid octet
            "192.168.1",      # Incomplete
            "192.168.1.1.1",  # Too many octets
            "not.an.ip.addr", # Non-numeric
            "192.168.01.1"    # Leading zeros (depending on implementation)
        ]
        
        for ip in invalid_ips:
            with pytest.raises(Exception):
                ip_type.convert(ip, None, None)
    
    def test_ip_address_type_ipv6_allowed(self):
        """Test IPAddressType with IPv6 when allowed."""
        ip_type = IPAddressType(allow_ipv6=True)
        
        valid_ipv6 = [
            "::1",
            "::",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        ]
        
        for ip in valid_ipv6:
            result = ip_type.convert(ip, None, None)
            assert result == ip
    
    def test_ip_address_type_ipv6_disallowed(self):
        """Test IPAddressType with IPv6 when not allowed."""
        ip_type = IPAddressType(allow_ipv6=False)
        
        ipv6_addresses = [
            "::1",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        ]
        
        for ip in ipv6_addresses:
            with pytest.raises(Exception):
                ip_type.convert(ip, None, None)
    
    def test_subnet_type_valid(self):
        """Test SubnetType with valid CIDR notation."""
        subnet_type = SubnetType()
        
        valid_subnets = [
            "192.168.1.0/24",
            "10.0.0.0/8",
            "172.16.0.0/16",
            "192.168.1.0/32",
            "0.0.0.0/0"
        ]
        
        for subnet in valid_subnets:
            result = subnet_type.convert(subnet, None, None)
            assert result == subnet
    
    def test_subnet_type_invalid(self):
        """Test SubnetType with invalid CIDR notation."""
        subnet_type = SubnetType()
        
        invalid_subnets = [
            "192.168.1.0",     # Missing prefix
            "192.168.1.0/33",  # Invalid prefix length
            "256.1.1.0/24",    # Invalid IP
            "192.168.1.0/-1",  # Negative prefix
            "not.a.subnet/24"  # Invalid format
        ]
        
        for subnet in invalid_subnets:
            with pytest.raises(Exception):
                subnet_type.convert(subnet, None, None)
