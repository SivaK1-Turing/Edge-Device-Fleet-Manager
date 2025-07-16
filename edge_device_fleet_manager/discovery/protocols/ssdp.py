"""
SSDP (Simple Service Discovery Protocol) implementation.

This module implements device discovery using SSDP, which is part of UPnP
and commonly used by media devices, routers, and smart home devices.
"""

import asyncio
import socket
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse
from ipaddress import IPv4Address, AddressValueError

import httpx

from ..core import Device, DeviceType, DeviceStatus, DiscoveryProtocol, DiscoveryResult
from ..exceptions import DiscoveryError, DiscoveryTimeoutError
from ...core.logging import get_logger

logger = get_logger(__name__)


class SSDPMessage:
    """SSDP message parser and builder."""
    
    @staticmethod
    def build_msearch(search_target: str = "upnp:rootdevice", mx: int = 3) -> str:
        """Build M-SEARCH request."""
        return (
            "M-SEARCH * HTTP/1.1\r\n"
            "HOST: 239.255.255.250:1900\r\n"
            f"MAN: \"ssdp:discover\"\r\n"
            f"ST: {search_target}\r\n"
            f"MX: {mx}\r\n"
            "\r\n"
        )
    
    @staticmethod
    def parse_response(data: str) -> Optional[Dict[str, str]]:
        """Parse SSDP response."""
        try:
            lines = data.strip().split('\r\n')
            if not lines or not lines[0].startswith('HTTP/1.1 200'):
                return None
            
            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().upper()] = value.strip()
            
            return headers
            
        except Exception as e:
            logger.debug("Failed to parse SSDP response", error=str(e))
            return None


class UPnPDeviceParser:
    """Parser for UPnP device descriptions."""
    
    @staticmethod
    async def fetch_device_description(location: str, timeout: int = 5) -> Optional[Dict]:
        """Fetch and parse UPnP device description."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(location)
                response.raise_for_status()
                
                return UPnPDeviceParser.parse_device_xml(response.text)
                
        except Exception as e:
            logger.debug("Failed to fetch device description", location=location, error=str(e))
            return None
    
    @staticmethod
    def parse_device_xml(xml_content: str) -> Dict:
        """Parse UPnP device XML description."""
        try:
            root = ET.fromstring(xml_content)
            
            # Handle namespaces
            namespaces = {
                'upnp': 'urn:schemas-upnp-org:device-1-0',
                'dlna': 'urn:schemas-dlna-org:device-1-0'
            }
            
            device_info = {}
            
            # Find device element
            device = root.find('.//upnp:device', namespaces)
            if device is None:
                device = root.find('.//device')  # Try without namespace
            
            if device is not None:
                # Extract basic device information
                for field in ['deviceType', 'friendlyName', 'manufacturer', 'manufacturerURL',
                             'modelDescription', 'modelName', 'modelNumber', 'modelURL',
                             'serialNumber', 'UDN', 'presentationURL']:
                    
                    elem = device.find(f'upnp:{field}', namespaces)
                    if elem is None:
                        elem = device.find(field)  # Try without namespace
                    
                    if elem is not None and elem.text:
                        device_info[field] = elem.text.strip()
                
                # Extract service information
                services = []
                service_list = device.find('.//upnp:serviceList', namespaces)
                if service_list is None:
                    service_list = device.find('.//serviceList')
                
                if service_list is not None:
                    for service in service_list.findall('.//upnp:service', namespaces):
                        if service is None:
                            service = service_list.findall('.//service')
                        
                        service_info = {}
                        for field in ['serviceType', 'serviceId', 'controlURL', 'eventSubURL', 'SCPDURL']:
                            elem = service.find(f'upnp:{field}', namespaces)
                            if elem is None:
                                elem = service.find(field)
                            
                            if elem is not None and elem.text:
                                service_info[field] = elem.text.strip()
                        
                        if service_info:
                            services.append(service_info)
                
                device_info['services'] = services
            
            return device_info
            
        except Exception as e:
            logger.debug("Failed to parse device XML", error=str(e))
            return {}


class SSDPDiscovery(DiscoveryProtocol):
    """SSDP discovery protocol implementation."""
    
    SSDP_ADDRESS = '239.255.255.250'
    SSDP_PORT = 1900
    
    # Common search targets
    SEARCH_TARGETS = [
        'upnp:rootdevice',
        'ssdp:all',
        'urn:schemas-upnp-org:device:MediaServer:1',
        'urn:schemas-upnp-org:device:MediaRenderer:1',
        'urn:schemas-upnp-org:device:InternetGatewayDevice:1',
        'urn:schemas-upnp-org:device:WANDevice:1',
        'urn:schemas-upnp-org:device:WANConnectionDevice:1',
        'urn:schemas-dlna-org:device:MediaServer:1',
        'urn:schemas-dlna-org:device:MediaRenderer:1',
    ]
    
    def __init__(self, config):
        super().__init__("ssdp")
        self.config = config
        self.timeout = config.discovery.ssdp_timeout
    
    async def discover(self, search_targets: Optional[List[str]] = None, **kwargs) -> DiscoveryResult:
        """Perform SSDP discovery."""
        start_time = time.time()
        result = DiscoveryResult(protocol=self.name)
        
        try:
            if not await self.is_available():
                result.success = False
                result.error = "SSDP not available"
                return result
            
            # Use provided search targets or defaults
            targets_to_search = search_targets or self.SEARCH_TARGETS
            
            # Collect responses from all search targets
            all_responses = []
            
            for target in targets_to_search:
                responses = await self._discover_target(target)
                all_responses.extend(responses)
            
            # Remove duplicates and fetch device descriptions
            unique_locations = set()
            devices = []
            
            for response in all_responses:
                location = response.get('LOCATION')
                if location and location not in unique_locations:
                    unique_locations.add(location)
                    device = await self._create_device_from_response(response)
                    if device:
                        devices.append(device)
            
            result.devices = devices
            
            self.logger.info(
                "SSDP discovery completed",
                devices_found=len(devices),
                search_targets=len(targets_to_search),
                total_responses=len(all_responses)
            )
            
        except Exception as e:
            result.success = False
            result.error = str(e)
            self.logger.error("SSDP discovery failed", error=str(e), exc_info=e)
        
        result.duration = time.time() - start_time
        return result
    
    async def _discover_target(self, search_target: str) -> List[Dict[str, str]]:
        """Discover devices for a specific search target."""
        responses = []
        
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(self.timeout)
            
            try:
                # Send M-SEARCH request
                message = SSDPMessage.build_msearch(search_target, self.timeout)
                sock.sendto(message.encode('utf-8'), (self.SSDP_ADDRESS, self.SSDP_PORT))
                
                # Collect responses
                end_time = time.time() + self.timeout
                
                while time.time() < end_time:
                    try:
                        remaining_time = end_time - time.time()
                        if remaining_time <= 0:
                            break
                        
                        sock.settimeout(min(remaining_time, 1.0))
                        data, addr = sock.recvfrom(4096)
                        
                        # Parse response
                        response = SSDPMessage.parse_response(data.decode('utf-8', errors='ignore'))
                        if response:
                            response['_source_ip'] = addr[0]
                            responses.append(response)
                        
                    except socket.timeout:
                        continue
                    except Exception as e:
                        logger.debug("Error receiving SSDP response", error=str(e))
                        continue
                
            finally:
                sock.close()
                
        except Exception as e:
            logger.debug("SSDP target discovery failed", target=search_target, error=str(e))
        
        return responses
    
    async def _create_device_from_response(self, response: Dict[str, str]) -> Optional[Device]:
        """Create Device object from SSDP response."""
        try:
            location = response.get('LOCATION')
            source_ip = response.get('_source_ip')
            
            if not location or not source_ip:
                return None
            
            # Validate IP address
            try:
                IPv4Address(source_ip)
            except AddressValueError:
                return None
            
            # Parse location URL to get potential port
            parsed_url = urlparse(location)
            port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
            
            # Create basic device
            device = Device(
                ip_address=source_ip,
                hostname=parsed_url.hostname,
                ports=[port] if port else [],
                discovery_protocol='ssdp',
                device_type=DeviceType.UNKNOWN,
                status=DeviceStatus.ONLINE,
                metadata={
                    'location': location,
                    'server': response.get('SERVER', ''),
                    'usn': response.get('USN', ''),
                    'st': response.get('ST', ''),
                    'cache_control': response.get('CACHE-CONTROL', ''),
                }
            )
            
            # Fetch detailed device description
            device_info = await UPnPDeviceParser.fetch_device_description(location, timeout=3)
            if device_info:
                # Update device with detailed information
                device.name = device_info.get('friendlyName')
                device.manufacturer = device_info.get('manufacturer')
                device.model = device_info.get('modelName')
                device.firmware_version = device_info.get('modelNumber')
                
                # Extract services
                services = device_info.get('services', [])
                device.services = [s.get('serviceType', '') for s in services if s.get('serviceType')]
                
                # Determine device type from UPnP device type
                device_type_str = device_info.get('deviceType', '').lower()
                device.device_type = self._determine_device_type(device_type_str, device.services)
                
                # Add additional capabilities
                device.capabilities.update({
                    'upnp_device_type': device_info.get('deviceType', ''),
                    'model_description': device_info.get('modelDescription', ''),
                    'serial_number': device_info.get('serialNumber', ''),
                    'udn': device_info.get('UDN', ''),
                    'presentation_url': device_info.get('presentationURL', ''),
                    'manufacturer_url': device_info.get('manufacturerURL', ''),
                    'model_url': device_info.get('modelURL', ''),
                })
            
            return device
            
        except Exception as e:
            logger.debug("Failed to create device from SSDP response", error=str(e))
            return None
    
    def _determine_device_type(self, device_type_str: str, services: List[str]) -> DeviceType:
        """Determine device type from UPnP device type and services."""
        device_type_str = device_type_str.lower()
        services_str = ' '.join(services).lower()
        
        if 'mediaserver' in device_type_str or 'mediaserver' in services_str:
            return DeviceType.MEDIA_SERVER
        elif 'mediarenderer' in device_type_str or 'mediarenderer' in services_str:
            return DeviceType.MEDIA_SERVER
        elif 'internetgatewaydevice' in device_type_str or 'wandevice' in device_type_str:
            return DeviceType.ROUTER
        elif 'printer' in device_type_str or 'print' in services_str:
            return DeviceType.PRINTER
        elif 'camera' in device_type_str or 'camera' in services_str:
            return DeviceType.CAMERA
        elif 'switch' in device_type_str:
            return DeviceType.SWITCH
        elif 'accesspoint' in device_type_str or 'wireless' in device_type_str:
            return DeviceType.ACCESS_POINT
        elif any(smart in device_type_str for smart in ['light', 'thermostat', 'sensor', 'switch']):
            return DeviceType.SMART_HOME
        
        return DeviceType.UNKNOWN
    
    async def is_available(self) -> bool:
        """Check if SSDP is available."""
        try:
            # Try to create a UDP socket and send to multicast address
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)
            
            # Test by sending a minimal M-SEARCH
            test_message = SSDPMessage.build_msearch("upnp:rootdevice", 1)
            sock.sendto(test_message.encode('utf-8'), (self.SSDP_ADDRESS, self.SSDP_PORT))
            
            sock.close()
            return True
            
        except Exception as e:
            logger.debug("SSDP not available", error=str(e))
            return False
