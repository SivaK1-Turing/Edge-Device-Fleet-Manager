"""
SNMP Discovery Protocol

This module implements device discovery using SNMP (Simple Network Management Protocol).
It can discover and identify network devices that support SNMP by querying standard
MIBs for device information.

Key Features:
- SNMP v1, v2c, and v3 support
- Standard MIB queries (system, interfaces, etc.)
- Device type identification
- Bulk operations for efficiency
- Configurable timeouts and retries
- Security credential management
"""

import asyncio
import ipaddress
import socket
from typing import Dict, List, Optional, Any, Tuple
import time

from ...core.logging import get_logger
from ..core import DiscoveryProtocol, DiscoveryResult, Device, DeviceType, DeviceStatus

# Try to import pysnmp, make it optional
try:
    from pysnmp.hlapi.asyncio import *
    from pysnmp.proto.rfc1902 import OctetString, Integer
    from pysnmp.error import PySnmpError
    SNMP_AVAILABLE = True
except ImportError:
    SNMP_AVAILABLE = False


class SNMPDiscovery(DiscoveryProtocol):
    """
    SNMP-based device discovery protocol.
    
    Discovers devices by scanning IP ranges and querying SNMP-enabled devices
    for system information and capabilities.
    """
    
    # Standard SNMP OIDs for device information
    SYSTEM_OID_MAP = {
        'sysDescr': '1.3.6.1.2.1.1.1.0',
        'sysObjectID': '1.3.6.1.2.1.1.2.0',
        'sysUpTime': '1.3.6.1.2.1.1.3.0',
        'sysContact': '1.3.6.1.2.1.1.4.0',
        'sysName': '1.3.6.1.2.1.1.5.0',
        'sysLocation': '1.3.6.1.2.1.1.6.0',
        'sysServices': '1.3.6.1.2.1.1.7.0'
    }
    
    # Interface table OIDs
    INTERFACE_OID_MAP = {
        'ifIndex': '1.3.6.1.2.1.2.2.1.1',
        'ifDescr': '1.3.6.1.2.1.2.2.1.2',
        'ifType': '1.3.6.1.2.1.2.2.1.3',
        'ifMtu': '1.3.6.1.2.1.2.2.1.4',
        'ifSpeed': '1.3.6.1.2.1.2.2.1.5',
        'ifPhysAddress': '1.3.6.1.2.1.2.2.1.6',
        'ifAdminStatus': '1.3.6.1.2.1.2.2.1.7',
        'ifOperStatus': '1.3.6.1.2.1.2.2.1.8'
    }
    
    # Device type identification based on sysObjectID patterns
    DEVICE_TYPE_PATTERNS = {
        '1.3.6.1.4.1.9': DeviceType.ROUTER,  # Cisco
        '1.3.6.1.4.1.11': DeviceType.SWITCH,  # HP
        '1.3.6.1.4.1.43': DeviceType.SWITCH,  # 3Com
        '1.3.6.1.4.1.2636': DeviceType.ROUTER,  # Juniper
        '1.3.6.1.4.1.1991': DeviceType.SWITCH,  # Foundry/Brocade
        '1.3.6.1.4.1.14179': DeviceType.ACCESS_POINT,  # Cisco Wireless
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("snmp")
        self.config = config or {}
        
        # SNMP configuration
        self.community = self.config.get('community', 'public')
        self.version = self.config.get('version', 2)  # SNMPv2c by default
        self.timeout = self.config.get('timeout', 5)
        self.retries = self.config.get('retries', 2)
        self.port = self.config.get('port', 161)
        
        # Discovery configuration
        self.ip_ranges = self.config.get('ip_ranges', ['192.168.1.0/24'])
        self.max_concurrent = self.config.get('max_concurrent', 50)
        self.include_interfaces = self.config.get('include_interfaces', True)
        
        # SNMPv3 configuration
        self.v3_username = self.config.get('v3_username')
        self.v3_auth_key = self.config.get('v3_auth_key')
        self.v3_priv_key = self.config.get('v3_priv_key')
        self.v3_auth_protocol = self.config.get('v3_auth_protocol', 'MD5')
        self.v3_priv_protocol = self.config.get('v3_priv_protocol', 'DES')
    
    async def is_available(self) -> bool:
        """Check if SNMP discovery is available."""
        return SNMP_AVAILABLE
    
    async def discover(self, **kwargs) -> DiscoveryResult:
        """
        Perform SNMP device discovery.
        
        Args:
            **kwargs: Discovery parameters
                - ip_ranges: List of IP ranges to scan
                - community: SNMP community string
                - timeout: SNMP timeout in seconds
                - max_concurrent: Maximum concurrent SNMP queries
        
        Returns:
            DiscoveryResult: Discovery results
        """
        if not SNMP_AVAILABLE:
            return DiscoveryResult(
                protocol="snmp",
                success=False,
                error="pysnmp library not available"
            )
        
        start_time = time.time()
        result = DiscoveryResult(protocol="snmp")
        
        # Override configuration with kwargs
        ip_ranges = kwargs.get('ip_ranges', self.ip_ranges)
        community = kwargs.get('community', self.community)
        timeout = kwargs.get('timeout', self.timeout)
        max_concurrent = kwargs.get('max_concurrent', self.max_concurrent)
        
        self.logger.info(
            "Starting SNMP discovery",
            ip_ranges=ip_ranges,
            community=community,
            timeout=timeout,
            max_concurrent=max_concurrent
        )
        
        try:
            # Generate IP addresses to scan
            ip_addresses = []
            for ip_range in ip_ranges:
                try:
                    network = ipaddress.ip_network(ip_range, strict=False)
                    ip_addresses.extend([str(ip) for ip in network.hosts()])
                except ValueError as e:
                    self.logger.warning("Invalid IP range", ip_range=ip_range, error=str(e))
                    continue
            
            if not ip_addresses:
                return DiscoveryResult(
                    protocol="snmp",
                    success=False,
                    error="No valid IP addresses to scan"
                )
            
            self.logger.info("Scanning IP addresses", count=len(ip_addresses))
            
            # Create semaphore to limit concurrent operations
            semaphore = asyncio.Semaphore(max_concurrent)
            
            # Create tasks for each IP address
            tasks = []
            for ip_address in ip_addresses:
                task = asyncio.create_task(
                    self._discover_device(ip_address, community, timeout, semaphore)
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            devices = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for device_result in devices:
                if isinstance(device_result, Device):
                    result.add_device(device_result)
                elif isinstance(device_result, Exception):
                    self.logger.debug("Device discovery failed", error=str(device_result))
            
            result.duration = time.time() - start_time
            result.success = True
            
            self.logger.info(
                "SNMP discovery completed",
                devices_found=len(result.devices),
                duration=result.duration,
                ip_addresses_scanned=len(ip_addresses)
            )
            
        except Exception as e:
            result.success = False
            result.error = str(e)
            result.duration = time.time() - start_time
            
            self.logger.error(
                "SNMP discovery failed",
                error=str(e),
                duration=result.duration,
                exc_info=e
            )
        
        return result
    
    async def _discover_device(
        self,
        ip_address: str,
        community: str,
        timeout: int,
        semaphore: asyncio.Semaphore
    ) -> Optional[Device]:
        """Discover a single device via SNMP."""
        async with semaphore:
            try:
                # Create SNMP engine and context
                if self.version == 3:
                    # SNMPv3 with authentication
                    auth_data = UsmUserData(
                        self.v3_username,
                        authKey=self.v3_auth_key,
                        privKey=self.v3_priv_key,
                        authProtocol=getattr(usmHMACMD5AuthProtocol, self.v3_auth_protocol, usmHMACMD5AuthProtocol),
                        privProtocol=getattr(usmDESPrivProtocol, self.v3_priv_protocol, usmDESPrivProtocol)
                    )
                else:
                    # SNMPv1/v2c with community string
                    auth_data = CommunityData(community, mpModel=self.version - 1)
                
                transport = UdpTransportTarget((ip_address, self.port), timeout=timeout, retries=self.retries)
                
                # Query system information
                system_info = await self._query_system_info(auth_data, transport)
                if not system_info:
                    return None
                
                # Create device object
                device = Device(
                    ip_address=ip_address,
                    discovery_protocol="snmp",
                    status=DeviceStatus.ONLINE
                )
                
                # Populate device information from SNMP data
                device.name = system_info.get('sysName', '').strip()
                device.hostname = device.name
                
                # Extract manufacturer and model from sysDescr
                sys_descr = system_info.get('sysDescr', '')
                if sys_descr:
                    device.metadata['system_description'] = sys_descr
                    # Try to extract manufacturer and model
                    manufacturer, model = self._parse_system_description(sys_descr)
                    if manufacturer:
                        device.manufacturer = manufacturer
                    if model:
                        device.model = model
                
                # Determine device type from sysObjectID
                sys_object_id = system_info.get('sysObjectID', '')
                if sys_object_id:
                    device.device_type = self._determine_device_type(sys_object_id)
                    device.metadata['system_object_id'] = sys_object_id
                
                # Add other system information
                if 'sysContact' in system_info:
                    device.metadata['contact'] = system_info['sysContact']
                if 'sysLocation' in system_info:
                    device.metadata['location'] = system_info['sysLocation']
                if 'sysUpTime' in system_info:
                    device.metadata['uptime'] = system_info['sysUpTime']
                if 'sysServices' in system_info:
                    device.metadata['services'] = system_info['sysServices']
                
                # Query interface information if enabled
                if self.include_interfaces:
                    interfaces = await self._query_interfaces(auth_data, transport)
                    if interfaces:
                        device.metadata['interfaces'] = interfaces
                        
                        # Extract MAC addresses from interfaces
                        mac_addresses = []
                        for interface in interfaces:
                            if 'physAddress' in interface and interface['physAddress']:
                                mac_addresses.append(interface['physAddress'])
                        
                        if mac_addresses:
                            device.mac_address = mac_addresses[0]  # Use first MAC as primary
                            device.metadata['mac_addresses'] = mac_addresses
                
                self.logger.debug(
                    "SNMP device discovered",
                    ip_address=ip_address,
                    name=device.name,
                    type=device.device_type.value,
                    manufacturer=device.manufacturer
                )
                
                return device
                
            except PySnmpError as e:
                self.logger.debug("SNMP query failed", ip_address=ip_address, error=str(e))
                return None
            except Exception as e:
                self.logger.debug("Device discovery error", ip_address=ip_address, error=str(e))
                return None
    
    async def _query_system_info(self, auth_data, transport) -> Optional[Dict[str, str]]:
        """Query system information via SNMP."""
        system_info = {}
        
        try:
            # Query all system OIDs
            for name, oid in self.SYSTEM_OID_MAP.items():
                iterator = getCmd(
                    SnmpEngine(),
                    auth_data,
                    transport,
                    ContextData(),
                    ObjectType(ObjectIdentity(oid))
                )
                
                errorIndication, errorStatus, errorIndex, varBinds = await iterator
                
                if errorIndication or errorStatus:
                    continue
                
                for varBind in varBinds:
                    value = varBind[1]
                    if isinstance(value, OctetString):
                        system_info[name] = str(value)
                    elif isinstance(value, Integer):
                        system_info[name] = int(value)
                    else:
                        system_info[name] = str(value)
            
            return system_info if system_info else None
            
        except Exception as e:
            self.logger.debug("System info query failed", error=str(e))
            return None
    
    async def _query_interfaces(self, auth_data, transport) -> Optional[List[Dict[str, Any]]]:
        """Query interface information via SNMP."""
        interfaces = []
        
        try:
            # Walk the interface table
            for name, base_oid in self.INTERFACE_OID_MAP.items():
                interface_data = {}
                
                iterator = nextCmd(
                    SnmpEngine(),
                    auth_data,
                    transport,
                    ContextData(),
                    ObjectType(ObjectIdentity(base_oid)),
                    lexicographicMode=False,
                    maxRows=100  # Limit to prevent excessive queries
                )
                
                async for errorIndication, errorStatus, errorIndex, varBinds in iterator:
                    if errorIndication or errorStatus:
                        break
                    
                    for varBind in varBinds:
                        oid_str = str(varBind[0])
                        if oid_str.startswith(base_oid):
                            # Extract interface index from OID
                            index = oid_str[len(base_oid):].lstrip('.')
                            if index not in interface_data:
                                interface_data[index] = {}
                            
                            value = varBind[1]
                            if isinstance(value, OctetString):
                                if name == 'ifPhysAddress' and len(value) == 6:
                                    # Format MAC address
                                    mac = ':'.join(f'{b:02x}' for b in value)
                                    interface_data[index][name] = mac
                                else:
                                    interface_data[index][name] = str(value)
                            elif isinstance(value, Integer):
                                interface_data[index][name] = int(value)
                            else:
                                interface_data[index][name] = str(value)
            
            # Convert to list format
            for index, data in interface_data.items():
                interface = {'index': index}
                interface.update(data)
                interfaces.append(interface)
            
            return interfaces if interfaces else None
            
        except Exception as e:
            self.logger.debug("Interface query failed", error=str(e))
            return None
    
    def _determine_device_type(self, sys_object_id: str) -> DeviceType:
        """Determine device type from sysObjectID."""
        for pattern, device_type in self.DEVICE_TYPE_PATTERNS.items():
            if sys_object_id.startswith(pattern):
                return device_type
        
        return DeviceType.UNKNOWN
    
    def _parse_system_description(self, sys_descr: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse manufacturer and model from system description."""
        sys_descr = sys_descr.lower()
        
        # Common manufacturer patterns
        manufacturers = {
            'cisco': 'Cisco',
            'juniper': 'Juniper',
            'hp': 'HP',
            'dell': 'Dell',
            'netgear': 'Netgear',
            'linksys': 'Linksys',
            'dlink': 'D-Link',
            'tplink': 'TP-Link',
            'ubiquiti': 'Ubiquiti',
            'mikrotik': 'MikroTik'
        }
        
        manufacturer = None
        for key, value in manufacturers.items():
            if key in sys_descr:
                manufacturer = value
                break
        
        # Try to extract model (this is very basic and would need enhancement)
        model = None
        if manufacturer:
            # Look for model patterns after manufacturer name
            words = sys_descr.split()
            for i, word in enumerate(words):
                if manufacturer.lower() in word.lower() and i + 1 < len(words):
                    # Next word might be the model
                    potential_model = words[i + 1]
                    if len(potential_model) > 2 and not potential_model.isdigit():
                        model = potential_model.upper()
                        break
        
        return manufacturer, model
