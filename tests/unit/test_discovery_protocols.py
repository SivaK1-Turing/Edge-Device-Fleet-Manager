"""
Unit tests for discovery protocol implementations.

Tests mDNS, SSDP, and network scanning discovery protocols.
"""

import asyncio
import pytest
import socket
import struct
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from edge_device_fleet_manager.discovery.protocols.mdns import (
    MDNSDiscovery, MDNSQuery, MDNSResponse
)
from edge_device_fleet_manager.discovery.protocols.ssdp import (
    SSDPDiscovery, SSDPMessage, UPnPDeviceParser
)
from edge_device_fleet_manager.discovery.protocols.network_scan import (
    NetworkScanDiscovery, PortScanner, ServiceIdentifier, NetworkDiscovery
)
from edge_device_fleet_manager.discovery.core import DeviceType, DeviceStatus


class TestMDNSQuery:
    """Test mDNS query building."""
    
    def test_build_query(self):
        """Test building mDNS query packet."""
        query = MDNSQuery.build_query("_http._tcp.local.")
        
        # Should be a valid DNS packet
        assert len(query) > 12  # At least header + question
        assert isinstance(query, bytes)
        
        # Check header format
        header = struct.unpack('!HHHHHH', query[:12])
        transaction_id, flags, questions, answers, authority, additional = header
        
        assert transaction_id == 0x0000
        assert flags == 0x0000
        assert questions == 0x0001
        assert answers == 0x0000
        assert authority == 0x0000
        assert additional == 0x0000
    
    def test_encode_domain_name(self):
        """Test domain name encoding."""
        encoded = MDNSQuery._encode_domain_name("_http._tcp.local.")
        
        # Should encode as length-prefixed labels
        assert encoded.startswith(b'\x05_http')  # 5 bytes + "_http"
        assert encoded.endswith(b'\x00')  # Null terminator


class TestMDNSResponse:
    """Test mDNS response parsing."""
    
    def test_parse_empty_response(self):
        """Test parsing empty response."""
        response = MDNSResponse(b'', '192.168.1.100')
        devices = response.parse()
        
        assert devices == []
    
    def test_parse_invalid_response(self):
        """Test parsing invalid response."""
        # Too short packet
        response = MDNSResponse(b'short', '192.168.1.100')
        devices = response.parse()
        
        assert devices == []
    
    @patch('socket.inet_ntoa')
    def test_parse_a_record(self, mock_inet_ntoa):
        """Test parsing A record."""
        mock_inet_ntoa.return_value = '192.168.1.100'
        
        # Create minimal valid mDNS response with A record
        header = struct.pack('!HHHHHH', 0, 0x8000, 0, 1, 0, 0)  # Response with 1 answer
        
        # Domain name: "test.local" (simplified)
        name = b'\x04test\x05local\x00'
        
        # A record: type=1, class=1, ttl=300, length=4, IP=192.168.1.100
        record = struct.pack('!HHIH', 1, 1, 300, 4) + b'\xc0\xa8\x01\x64'  # 192.168.1.100
        
        packet = header + name + record
        
        response = MDNSResponse(packet, '192.168.1.100')
        devices = response.parse()
        
        # Should create a device
        assert len(devices) == 1
        device = devices[0]
        assert device.ip_address == '192.168.1.100'
        assert device.discovery_protocol == 'mdns'
        assert device.status == DeviceStatus.ONLINE


class TestMDNSDiscovery:
    """Test mDNS discovery protocol."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.discovery.mdns_timeout = 3
        return config
    
    @pytest.fixture
    def mdns_discovery(self, mock_config):
        """Create mDNS discovery instance."""
        return MDNSDiscovery(mock_config)
    
    async def test_is_available_success(self, mdns_discovery):
        """Test mDNS availability check success."""
        with patch('socket.socket') as mock_socket:
            mock_sock = Mock()
            mock_socket.return_value = mock_sock
            
            result = await mdns_discovery.is_available()
            
            assert result is True
            mock_sock.close.assert_called_once()
    
    async def test_is_available_failure(self, mdns_discovery):
        """Test mDNS availability check failure."""
        with patch('socket.socket', side_effect=Exception("No multicast")):
            result = await mdns_discovery.is_available()
            
            assert result is False
    
    async def test_discover_not_available(self, mdns_discovery):
        """Test discovery when mDNS not available."""
        with patch.object(mdns_discovery, 'is_available', return_value=False):
            result = await mdns_discovery.discover()
            
            assert result.success is False
            assert result.error == "mDNS not available"
    
    @patch('socket.socket')
    async def test_discover_success(self, mock_socket, mdns_discovery):
        """Test successful mDNS discovery."""
        # Mock socket
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        # Mock socket operations
        mock_sock.recvfrom.side_effect = [
            (b'mock_response', ('192.168.1.100', 5353)),
            socket.timeout()  # End the loop
        ]
        
        with patch.object(mdns_discovery, 'is_available', return_value=True):
            with patch.object(mdns_discovery, '_collect_responses', return_value=[]):
                result = await mdns_discovery.discover()
                
                assert result.success is True
                assert result.protocol == "mdns"
                assert isinstance(result.devices, list)


class TestSSDPMessage:
    """Test SSDP message handling."""
    
    def test_build_msearch(self):
        """Test building M-SEARCH request."""
        message = SSDPMessage.build_msearch("upnp:rootdevice", 3)
        
        assert "M-SEARCH * HTTP/1.1" in message
        assert "HOST: 239.255.255.250:1900" in message
        assert "ST: upnp:rootdevice" in message
        assert "MX: 3" in message
    
    def test_parse_response_success(self):
        """Test parsing valid SSDP response."""
        response_data = (
            "HTTP/1.1 200 OK\r\n"
            "LOCATION: http://192.168.1.100:8080/description.xml\r\n"
            "SERVER: Linux/3.14 UPnP/1.0 Device/1.0\r\n"
            "USN: uuid:12345678-1234-1234-1234-123456789012\r\n"
            "\r\n"
        )
        
        headers = SSDPMessage.parse_response(response_data)
        
        assert headers is not None
        assert headers["LOCATION"] == "http://192.168.1.100:8080/description.xml"
        assert headers["SERVER"] == "Linux/3.14 UPnP/1.0 Device/1.0"
        assert headers["USN"] == "uuid:12345678-1234-1234-1234-123456789012"
    
    def test_parse_response_invalid(self):
        """Test parsing invalid SSDP response."""
        invalid_responses = [
            "HTTP/1.1 404 Not Found\r\n\r\n",  # Not 200 OK
            "Invalid response",  # Not HTTP
            "",  # Empty
        ]
        
        for response in invalid_responses:
            headers = SSDPMessage.parse_response(response)
            assert headers is None


class TestUPnPDeviceParser:
    """Test UPnP device description parsing."""
    
    def test_parse_device_xml(self):
        """Test parsing UPnP device XML."""
        xml_content = """<?xml version="1.0"?>
        <root xmlns="urn:schemas-upnp-org:device-1-0">
            <device>
                <deviceType>urn:schemas-upnp-org:device:MediaServer:1</deviceType>
                <friendlyName>Test Media Server</friendlyName>
                <manufacturer>Test Manufacturer</manufacturer>
                <modelName>Test Model</modelName>
                <serialNumber>12345</serialNumber>
                <serviceList>
                    <service>
                        <serviceType>urn:schemas-upnp-org:service:ContentDirectory:1</serviceType>
                        <serviceId>urn:upnp-org:serviceId:ContentDirectory</serviceId>
                    </service>
                </serviceList>
            </device>
        </root>"""
        
        device_info = UPnPDeviceParser.parse_device_xml(xml_content)
        
        assert device_info["deviceType"] == "urn:schemas-upnp-org:device:MediaServer:1"
        assert device_info["friendlyName"] == "Test Media Server"
        assert device_info["manufacturer"] == "Test Manufacturer"
        assert device_info["modelName"] == "Test Model"
        assert device_info["serialNumber"] == "12345"
        assert len(device_info["services"]) == 1
        assert device_info["services"][0]["serviceType"] == "urn:schemas-upnp-org:service:ContentDirectory:1"
    
    def test_parse_invalid_xml(self):
        """Test parsing invalid XML."""
        invalid_xml = "<invalid>xml</broken>"
        
        device_info = UPnPDeviceParser.parse_device_xml(invalid_xml)
        
        assert device_info == {}


class TestSSDPDiscovery:
    """Test SSDP discovery protocol."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.discovery.ssdp_timeout = 3
        return config
    
    @pytest.fixture
    def ssdp_discovery(self, mock_config):
        """Create SSDP discovery instance."""
        return SSDPDiscovery(mock_config)
    
    async def test_is_available_success(self, ssdp_discovery):
        """Test SSDP availability check."""
        with patch('socket.socket') as mock_socket:
            mock_sock = Mock()
            mock_socket.return_value = mock_sock
            
            result = await ssdp_discovery.is_available()
            
            assert result is True
            mock_sock.close.assert_called_once()
    
    async def test_discover_not_available(self, ssdp_discovery):
        """Test discovery when SSDP not available."""
        with patch.object(ssdp_discovery, 'is_available', return_value=False):
            result = await ssdp_discovery.discover()
            
            assert result.success is False
            assert result.error == "SSDP not available"
    
    def test_determine_device_type(self, ssdp_discovery):
        """Test device type determination."""
        test_cases = [
            ("urn:schemas-upnp-org:device:MediaServer:1", [], DeviceType.MEDIA_SERVER),
            ("urn:schemas-upnp-org:device:InternetGatewayDevice:1", [], DeviceType.ROUTER),
            ("unknown", ["urn:schemas-upnp-org:service:PrintBasic:1"], DeviceType.PRINTER),
            ("unknown", [], DeviceType.UNKNOWN),
        ]
        
        for device_type_str, services, expected in test_cases:
            result = ssdp_discovery._determine_device_type(device_type_str, services)
            assert result == expected


class TestPortScanner:
    """Test port scanning functionality."""
    
    @pytest.fixture
    def port_scanner(self):
        """Create port scanner."""
        return PortScanner()
    
    async def test_scan_port_success(self, port_scanner):
        """Test successful port scan."""
        with patch('asyncio.open_connection') as mock_connect:
            mock_reader = Mock()
            mock_writer = Mock()
            mock_writer.wait_closed = AsyncMock()
            mock_connect.return_value = (mock_reader, mock_writer)
            
            result = await port_scanner.scan_port("127.0.0.1", 80, timeout=1.0)
            
            assert result is True
            mock_writer.close.assert_called_once()
    
    async def test_scan_port_failure(self, port_scanner):
        """Test failed port scan."""
        with patch('asyncio.open_connection', side_effect=ConnectionRefusedError()):
            result = await port_scanner.scan_port("127.0.0.1", 80, timeout=1.0)
            
            assert result is False
    
    async def test_scan_host(self, port_scanner):
        """Test scanning multiple ports on a host."""
        with patch.object(port_scanner, 'scan_port') as mock_scan:
            # Mock some ports as open
            mock_scan.side_effect = lambda ip, port, timeout: port in [80, 443]
            
            open_ports = await port_scanner.scan_host("127.0.0.1", [22, 80, 443, 8080])
            
            assert set(open_ports) == {80, 443}


class TestServiceIdentifier:
    """Test service identification."""
    
    async def test_identify_service_http(self):
        """Test HTTP service identification."""
        with patch('asyncio.open_connection') as mock_connect:
            mock_reader = Mock()
            mock_writer = Mock()
            mock_writer.wait_closed = AsyncMock()
            mock_reader.read = AsyncMock(return_value=b"HTTP/1.1 200 OK\r\nServer: nginx\r\n")
            mock_connect.return_value = (mock_reader, mock_writer)
            
            service = await ServiceIdentifier.identify_service("127.0.0.1", 80)
            
            assert service is not None
            assert service["name"] == "HTTP"
            assert service["port"] == "80"
            assert "HTTP" in service["banner"]
    
    async def test_identify_service_unknown(self):
        """Test unknown service identification."""
        service = await ServiceIdentifier.identify_service("127.0.0.1", 9999)
        
        assert service is not None
        assert service["name"] == "Unknown-9999"
        assert service["port"] == "9999"
    
    async def test_grab_banner_failure(self):
        """Test banner grabbing failure."""
        with patch('asyncio.open_connection', side_effect=ConnectionRefusedError()):
            banner = await ServiceIdentifier._grab_banner("127.0.0.1", 80)
            
            assert banner is None


class TestNetworkDiscovery:
    """Test network discovery utilities."""
    
    async def test_ping_host_success(self):
        """Test successful ping."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = await NetworkDiscovery.ping_host("127.0.0.1")
            
            assert result is True
    
    async def test_ping_host_failure(self):
        """Test failed ping."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_run.return_value = mock_result
            
            result = await NetworkDiscovery.ping_host("192.168.1.999")
            
            assert result is False
    
    def test_get_local_networks(self):
        """Test getting local networks."""
        with patch('socket.gethostname', return_value='test-host'):
            with patch('socket.gethostbyname_ex', return_value=('test-host', [], ['192.168.1.100'])):
                networks = NetworkDiscovery.get_local_networks()
                
                assert len(networks) > 0
                assert any('192.168.1.0/24' in net for net in networks)


class TestNetworkScanDiscovery:
    """Test network scanning discovery protocol."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.discovery.rate_limit_per_host = 2.0
        config.discovery.rate_limit_global = 100.0
        return config
    
    @pytest.fixture
    def network_scan(self, mock_config):
        """Create network scan discovery instance."""
        return NetworkScanDiscovery(mock_config)
    
    async def test_is_available(self, network_scan):
        """Test network scan availability."""
        with patch('socket.socket'):
            with patch.object(NetworkDiscovery, 'ping_host', return_value=True):
                result = await network_scan.is_available()
                
                assert result is True
    
    def test_determine_device_type(self, network_scan):
        """Test device type determination from ports."""
        test_cases = [
            ([80, 443, 22], ["HTTP", "HTTPS", "SSH"], DeviceType.ROUTER),
            ([631], ["Printer"], DeviceType.PRINTER),
            ([1883], ["MQTT"], DeviceType.IOT_GATEWAY),
            ([554, 8000], ["HTTP"], DeviceType.CAMERA),
            ([9999], ["Unknown"], DeviceType.UNKNOWN),
        ]
        
        for ports, services, expected in test_cases:
            result = network_scan._determine_device_type(ports, services)
            assert result == expected
    
    async def test_discover_no_networks(self, network_scan):
        """Test discovery with no valid networks."""
        with patch.object(network_scan, 'is_available', return_value=True):
            with patch.object(NetworkDiscovery, 'get_local_networks', return_value=[]):
                result = await network_scan.discover()
                
                assert result.success is False
                assert "No valid networks to scan" in result.error
