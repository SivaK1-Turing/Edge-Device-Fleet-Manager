"""
mDNS (Multicast DNS) discovery protocol implementation.

This module implements device discovery using multicast DNS (mDNS) protocol,
commonly used by IoT devices, printers, and other network services.
"""

import asyncio
import socket
import struct
import time
from typing import Dict, List, Optional, Set, Tuple
from ipaddress import IPv4Address, AddressValueError

from ..core import Device, DeviceType, DeviceStatus, DiscoveryProtocol, DiscoveryResult
from ..exceptions import DiscoveryError, DiscoveryTimeoutError
from ...core.logging import get_logger

logger = get_logger(__name__)


class MDNSQuery:
    """mDNS query packet builder."""
    
    @staticmethod
    def build_query(service_type: str, query_type: int = 12) -> bytes:
        """Build an mDNS query packet."""
        # Transaction ID (2 bytes)
        transaction_id = 0x0000
        
        # Flags (2 bytes) - Standard query
        flags = 0x0000
        
        # Questions count (2 bytes)
        questions = 0x0001
        
        # Answer RRs, Authority RRs, Additional RRs (6 bytes)
        answers = authority = additional = 0x0000
        
        # Build header
        header = struct.pack('!HHHHHH', 
                           transaction_id, flags, questions, 
                           answers, authority, additional)
        
        # Build question
        question = MDNSQuery._encode_domain_name(service_type)
        question += struct.pack('!HH', query_type, 0x0001)  # Type PTR, Class IN
        
        return header + question
    
    @staticmethod
    def _encode_domain_name(domain: str) -> bytes:
        """Encode domain name for DNS packet."""
        encoded = b''
        for part in domain.split('.'):
            if part:
                encoded += bytes([len(part)]) + part.encode('ascii')
        encoded += b'\x00'  # Null terminator
        return encoded


class MDNSResponse:
    """mDNS response packet parser."""
    
    def __init__(self, data: bytes, source_ip: str):
        self.data = data
        self.source_ip = source_ip
        self.services: List[Dict] = []
        self.devices: List[Device] = []
        
    def parse(self) -> List[Device]:
        """Parse mDNS response and extract device information."""
        try:
            if len(self.data) < 12:
                return []
            
            # Parse header
            header = struct.unpack('!HHHHHH', self.data[:12])
            transaction_id, flags, questions, answers, authority, additional = header
            
            # Skip questions section
            offset = 12
            for _ in range(questions):
                offset = self._skip_question(offset)
            
            # Parse answers
            for _ in range(answers + authority + additional):
                offset = self._parse_resource_record(offset)
                if offset is None:
                    break
            
            # Convert parsed services to devices
            self._create_devices()
            
            return self.devices
            
        except Exception as e:
            logger.debug("Failed to parse mDNS response", error=str(e), source_ip=self.source_ip)
            return []
    
    def _skip_question(self, offset: int) -> int:
        """Skip a question section."""
        # Skip domain name
        offset = self._skip_domain_name(offset)
        # Skip type and class (4 bytes)
        return offset + 4
    
    def _parse_resource_record(self, offset: int) -> Optional[int]:
        """Parse a resource record."""
        try:
            # Parse domain name
            name, offset = self._parse_domain_name(offset)
            
            if offset + 10 > len(self.data):
                return None
            
            # Parse type, class, TTL, and data length
            rr_type, rr_class, ttl, data_length = struct.unpack('!HHIH', self.data[offset:offset+10])
            offset += 10
            
            if offset + data_length > len(self.data):
                return None
            
            # Parse data based on type
            data = self.data[offset:offset+data_length]
            
            if rr_type == 12:  # PTR record
                service_name, _ = self._parse_domain_name_from_data(data, 0)
                self.services.append({
                    'type': 'PTR',
                    'name': name,
                    'service': service_name,
                    'ttl': ttl
                })
            elif rr_type == 16:  # TXT record
                txt_data = self._parse_txt_record(data)
                self.services.append({
                    'type': 'TXT',
                    'name': name,
                    'data': txt_data,
                    'ttl': ttl
                })
            elif rr_type == 33:  # SRV record
                if data_length >= 6:
                    priority, weight, port = struct.unpack('!HHH', data[:6])
                    target, _ = self._parse_domain_name_from_data(data, 6)
                    self.services.append({
                        'type': 'SRV',
                        'name': name,
                        'priority': priority,
                        'weight': weight,
                        'port': port,
                        'target': target,
                        'ttl': ttl
                    })
            elif rr_type == 1:  # A record
                if data_length == 4:
                    ip = socket.inet_ntoa(data)
                    self.services.append({
                        'type': 'A',
                        'name': name,
                        'ip': ip,
                        'ttl': ttl
                    })
            
            return offset + data_length
            
        except Exception as e:
            logger.debug("Failed to parse resource record", error=str(e))
            return None
    
    def _parse_domain_name(self, offset: int) -> Tuple[str, int]:
        """Parse domain name from DNS packet."""
        name_parts = []
        original_offset = offset
        jumped = False
        
        while offset < len(self.data):
            length = self.data[offset]
            
            if length == 0:
                offset += 1
                break
            elif length & 0xC0 == 0xC0:  # Compression pointer
                if not jumped:
                    original_offset = offset + 2
                    jumped = True
                pointer = ((length & 0x3F) << 8) | self.data[offset + 1]
                offset = pointer
            else:
                offset += 1
                if offset + length > len(self.data):
                    break
                name_parts.append(self.data[offset:offset+length].decode('ascii', errors='ignore'))
                offset += length
        
        return '.'.join(name_parts), original_offset if jumped else offset
    
    def _parse_domain_name_from_data(self, data: bytes, offset: int) -> Tuple[str, int]:
        """Parse domain name from data section."""
        name_parts = []
        
        while offset < len(data):
            length = data[offset]
            
            if length == 0:
                offset += 1
                break
            elif length & 0xC0 == 0xC0:  # Compression pointer not supported in data
                break
            else:
                offset += 1
                if offset + length > len(data):
                    break
                name_parts.append(data[offset:offset+length].decode('ascii', errors='ignore'))
                offset += length
        
        return '.'.join(name_parts), offset
    
    def _skip_domain_name(self, offset: int) -> int:
        """Skip domain name in DNS packet."""
        while offset < len(self.data):
            length = self.data[offset]
            
            if length == 0:
                return offset + 1
            elif length & 0xC0 == 0xC0:  # Compression pointer
                return offset + 2
            else:
                offset += 1 + length
        
        return offset
    
    def _parse_txt_record(self, data: bytes) -> Dict[str, str]:
        """Parse TXT record data."""
        txt_data = {}
        offset = 0
        
        while offset < len(data):
            length = data[offset]
            offset += 1
            
            if offset + length > len(data):
                break
            
            txt_string = data[offset:offset+length].decode('ascii', errors='ignore')
            offset += length
            
            if '=' in txt_string:
                key, value = txt_string.split('=', 1)
                txt_data[key] = value
            else:
                txt_data[txt_string] = ''
        
        return txt_data
    
    def _create_devices(self) -> None:
        """Create Device objects from parsed services."""
        # Group services by hostname/IP
        device_groups: Dict[str, Dict] = {}
        
        for service in self.services:
            if service['type'] == 'A':
                ip = service['ip']
                if ip not in device_groups:
                    device_groups[ip] = {'ip': ip, 'services': [], 'ports': set(), 'txt_data': {}}
                device_groups[ip]['hostname'] = service['name']
            
            elif service['type'] == 'SRV':
                target = service.get('target', '')
                port = service.get('port', 0)
                
                # Find corresponding A record
                for a_service in self.services:
                    if a_service['type'] == 'A' and a_service['name'] == target:
                        ip = a_service['ip']
                        if ip not in device_groups:
                            device_groups[ip] = {'ip': ip, 'services': [], 'ports': set(), 'txt_data': {}}
                        
                        device_groups[ip]['services'].append(service['name'])
                        if port > 0:
                            device_groups[ip]['ports'].add(port)
                        break
            
            elif service['type'] == 'TXT':
                # Associate TXT data with services
                for ip, group in device_groups.items():
                    if any(svc for svc in group['services'] if service['name'] in svc):
                        group['txt_data'].update(service['data'])
        
        # Create Device objects
        for ip, group in device_groups.items():
            try:
                # Validate IP address
                IPv4Address(ip)
                
                device = Device(
                    ip_address=ip,
                    hostname=group.get('hostname'),
                    ports=list(group['ports']),
                    services=group['services'],
                    discovery_protocol='mdns',
                    device_type=self._determine_device_type(group),
                    status=DeviceStatus.ONLINE,
                    capabilities=group['txt_data']
                )
                
                # Extract additional info from TXT data
                txt_data = group['txt_data']
                if 'model' in txt_data:
                    device.model = txt_data['model']
                if 'manufacturer' in txt_data or 'vendor' in txt_data:
                    device.manufacturer = txt_data.get('manufacturer', txt_data.get('vendor'))
                if 'version' in txt_data or 'fw' in txt_data:
                    device.firmware_version = txt_data.get('version', txt_data.get('fw'))
                if 'name' in txt_data or 'friendly_name' in txt_data:
                    device.name = txt_data.get('name', txt_data.get('friendly_name'))
                
                self.devices.append(device)
                
            except AddressValueError:
                logger.debug("Invalid IP address in mDNS response", ip=ip)
                continue
    
    def _determine_device_type(self, group: Dict) -> DeviceType:
        """Determine device type from services and TXT data."""
        services = [s.lower() for s in group['services']]
        txt_data = {k.lower(): v.lower() for k, v in group['txt_data'].items()}
        
        # Check for specific service types
        if any('_ipp' in s or '_printer' in s for s in services):
            return DeviceType.PRINTER
        elif any('_http' in s or '_https' in s for s in services):
            if any('camera' in v for v in txt_data.values()):
                return DeviceType.CAMERA
            elif any('media' in v or 'dlna' in v for v in txt_data.values()):
                return DeviceType.MEDIA_SERVER
            else:
                return DeviceType.IOT_GATEWAY
        elif any('_ssh' in s or '_telnet' in s for s in services):
            return DeviceType.IOT_GATEWAY
        elif any('_mqtt' in s or '_coap' in s for s in services):
            return DeviceType.IOT_SENSOR
        
        return DeviceType.UNKNOWN


class MDNSDiscovery(DiscoveryProtocol):
    """mDNS discovery protocol implementation."""
    
    MDNS_ADDRESS = '224.0.0.251'
    MDNS_PORT = 5353
    
    # Common service types to query
    SERVICE_TYPES = [
        '_services._dns-sd._udp.local.',
        '_http._tcp.local.',
        '_https._tcp.local.',
        '_ipp._tcp.local.',
        '_printer._tcp.local.',
        '_ssh._tcp.local.',
        '_telnet._tcp.local.',
        '_mqtt._tcp.local.',
        '_coap._udp.local.',
        '_airplay._tcp.local.',
        '_homekit._tcp.local.',
        '_hap._tcp.local.',
    ]
    
    def __init__(self, config):
        super().__init__("mdns")
        self.config = config
        self.timeout = config.discovery.mdns_timeout
    
    async def discover(self, service_types: Optional[List[str]] = None, **kwargs) -> DiscoveryResult:
        """Perform mDNS discovery."""
        start_time = time.time()
        result = DiscoveryResult(protocol=self.name)
        
        try:
            if not await self.is_available():
                result.success = False
                result.error = "mDNS not available"
                return result
            
            # Use provided service types or defaults
            types_to_query = service_types or self.SERVICE_TYPES
            
            # Create UDP socket for multicast
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(self.timeout)
            
            # Enable multicast
            mreq = struct.pack('4sl', socket.inet_aton(self.MDNS_ADDRESS), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            
            try:
                # Bind to multicast address
                sock.bind(('', self.MDNS_PORT))
                
                # Send queries for each service type
                for service_type in types_to_query:
                    query = MDNSQuery.build_query(service_type)
                    sock.sendto(query, (self.MDNS_ADDRESS, self.MDNS_PORT))
                
                # Collect responses
                devices = await self._collect_responses(sock)
                result.devices = devices
                
                self.logger.info(
                    "mDNS discovery completed",
                    devices_found=len(devices),
                    service_types=len(types_to_query)
                )
                
            finally:
                sock.close()
                
        except Exception as e:
            result.success = False
            result.error = str(e)
            self.logger.error("mDNS discovery failed", error=str(e), exc_info=e)
        
        result.duration = time.time() - start_time
        return result
    
    async def _collect_responses(self, sock: socket.socket) -> List[Device]:
        """Collect mDNS responses."""
        devices: Dict[str, Device] = {}
        end_time = time.time() + self.timeout
        
        while time.time() < end_time:
            try:
                remaining_time = end_time - time.time()
                if remaining_time <= 0:
                    break
                
                sock.settimeout(min(remaining_time, 1.0))
                data, addr = sock.recvfrom(4096)
                
                # Parse response
                response = MDNSResponse(data, addr[0])
                response_devices = response.parse()
                
                # Merge devices (avoid duplicates by IP)
                for device in response_devices:
                    if device.ip_address not in devices:
                        devices[device.ip_address] = device
                    else:
                        # Merge information
                        existing = devices[device.ip_address]
                        existing.services = list(set(existing.services + device.services))
                        existing.ports = list(set(existing.ports + device.ports))
                        existing.capabilities.update(device.capabilities)
                        
                        # Update other fields if not set
                        if not existing.name and device.name:
                            existing.name = device.name
                        if not existing.hostname and device.hostname:
                            existing.hostname = device.hostname
                        if not existing.manufacturer and device.manufacturer:
                            existing.manufacturer = device.manufacturer
                        if not existing.model and device.model:
                            existing.model = device.model
                
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.debug("Error receiving mDNS response", error=str(e))
                continue
        
        return list(devices.values())
    
    async def is_available(self) -> bool:
        """Check if mDNS is available."""
        try:
            # Try to create a multicast socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Test multicast capability
            mreq = struct.pack('4sl', socket.inet_aton(self.MDNS_ADDRESS), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            
            sock.close()
            return True
            
        except Exception as e:
            self.logger.debug("mDNS not available", error=str(e))
            return False
