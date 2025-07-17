"""
Network scanning discovery protocol implementation.

This module implements device discovery through network range scanning,
port detection, and service identification with parallel execution.
"""

import asyncio
import socket
import time
import subprocess
import platform
from typing import Dict, List, Optional, Set, Tuple
from ipaddress import IPv4Network, IPv4Address, AddressValueError
from concurrent.futures import ThreadPoolExecutor

from ..core import Device, DeviceType, DeviceStatus, DiscoveryProtocol, DiscoveryResult
from ..exceptions import DiscoveryError, NetworkError
from ..rate_limiter import RateLimiter, RateLimitConfig
from ...core.logging import get_logger

logger = get_logger(__name__)


class PortScanner:
    """Async port scanner with rate limiting."""
    
    # Common ports to scan
    COMMON_PORTS = [
        22,    # SSH
        23,    # Telnet
        53,    # DNS
        80,    # HTTP
        135,   # RPC
        139,   # NetBIOS
        443,   # HTTPS
        445,   # SMB
        993,   # IMAPS
        995,   # POP3S
        1883,  # MQTT
        5353,  # mDNS
        8080,  # HTTP Alt
        8443,  # HTTPS Alt
        9000,  # Various services
    ]
    
    # IoT specific ports
    IOT_PORTS = [
        1883,  # MQTT
        8883,  # MQTT over SSL
        5683,  # CoAP
        5684,  # CoAP over DTLS
        1900,  # SSDP
        5353,  # mDNS
        6667,  # IRC (some IoT)
        8000,  # HTTP Alt
        8008,  # HTTP Alt
        8081,  # HTTP Alt
        8888,  # HTTP Alt
        9999,  # Various
    ]
    
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter
        self.logger = get_logger(__name__)
    
    async def scan_port(self, ip: str, port: int, timeout: float = 1.0) -> bool:
        """Scan a single port on a host."""
        try:
            if self.rate_limiter:
                await self.rate_limiter.acquire(ip, timeout=5.0)
            
            start_time = time.time()
            
            # Create connection
            future = asyncio.open_connection(ip, port)
            try:
                reader, writer = await asyncio.wait_for(future, timeout=timeout)
                writer.close()
                await writer.wait_closed()
                
                if self.rate_limiter:
                    response_time = time.time() - start_time
                    self.rate_limiter.record_success(ip, response_time)
                
                return True
                
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                if self.rate_limiter:
                    self.rate_limiter.record_failure(ip, "connection_failed")
                return False
                
        except Exception as e:
            if self.rate_limiter:
                self.rate_limiter.record_failure(ip, "scan_error")
            self.logger.debug("Port scan error", ip=ip, port=port, error=str(e))
            return False
    
    async def scan_host(self, ip: str, ports: List[int], timeout: float = 1.0, 
                       max_concurrent: int = 10) -> List[int]:
        """Scan multiple ports on a host."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scan_with_semaphore(port: int) -> Optional[int]:
            async with semaphore:
                if await self.scan_port(ip, port, timeout):
                    return port
                return None
        
        # Scan all ports concurrently
        tasks = [scan_with_semaphore(port) for port in ports]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful scans
        open_ports = [port for port in results if isinstance(port, int)]
        return open_ports


class ServiceIdentifier:
    """Service identification through banner grabbing and fingerprinting."""
    
    SERVICE_SIGNATURES = {
        22: {'name': 'SSH', 'banner_contains': ['SSH']},
        23: {'name': 'Telnet', 'banner_contains': ['telnet', 'login:']},
        25: {'name': 'SMTP', 'banner_contains': ['SMTP', '220']},
        53: {'name': 'DNS', 'protocol': 'udp'},
        80: {'name': 'HTTP', 'banner_contains': ['HTTP/', 'Server:']},
        110: {'name': 'POP3', 'banner_contains': ['POP3', '+OK']},
        135: {'name': 'RPC', 'banner_contains': []},
        139: {'name': 'NetBIOS', 'protocol': 'smb'},
        143: {'name': 'IMAP', 'banner_contains': ['IMAP', '* OK']},
        443: {'name': 'HTTPS', 'protocol': 'ssl'},
        445: {'name': 'SMB', 'protocol': 'smb'},
        993: {'name': 'IMAPS', 'protocol': 'ssl'},
        995: {'name': 'POP3S', 'protocol': 'ssl'},
        1883: {'name': 'MQTT', 'banner_contains': []},
        5353: {'name': 'mDNS', 'protocol': 'udp'},
        8080: {'name': 'HTTP-Alt', 'banner_contains': ['HTTP/', 'Server:']},
        8443: {'name': 'HTTPS-Alt', 'protocol': 'ssl'},
    }
    
    @staticmethod
    async def identify_service(ip: str, port: int, timeout: float = 2.0) -> Optional[Dict[str, str]]:
        """Identify service running on a port."""
        try:
            signature = ServiceIdentifier.SERVICE_SIGNATURES.get(port, {})
            service_name = signature.get('name', f'Unknown-{port}')
            
            # Try banner grabbing for TCP services
            if signature.get('protocol') != 'udp':
                banner = await ServiceIdentifier._grab_banner(ip, port, timeout)
                if banner:
                    # Check for known signatures
                    banner_lower = banner.lower()
                    for contains in signature.get('banner_contains', []):
                        if contains.lower() in banner_lower:
                            return {
                                'name': service_name,
                                'banner': banner,
                                'port': str(port),
                                'protocol': 'tcp'
                            }
                    
                    # Generic service detection
                    if 'http' in banner_lower:
                        service_name = 'HTTP'
                    elif 'ssh' in banner_lower:
                        service_name = 'SSH'
                    elif 'ftp' in banner_lower:
                        service_name = 'FTP'
                    
                    return {
                        'name': service_name,
                        'banner': banner,
                        'port': str(port),
                        'protocol': 'tcp'
                    }
            
            # Return basic service info
            return {
                'name': service_name,
                'port': str(port),
                'protocol': signature.get('protocol', 'tcp')
            }
            
        except Exception as e:
            logger.debug("Service identification failed", ip=ip, port=port, error=str(e))
            return None
    
    @staticmethod
    async def _grab_banner(ip: str, port: int, timeout: float = 2.0) -> Optional[str]:
        """Grab service banner."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), 
                timeout=timeout
            )
            
            try:
                # Send HTTP request for web services
                if port in [80, 8080, 8000, 8008, 8081, 8888]:
                    writer.write(b"GET / HTTP/1.0\r\n\r\n")
                    await writer.drain()
                
                # Read response
                data = await asyncio.wait_for(reader.read(1024), timeout=timeout)
                banner = data.decode('utf-8', errors='ignore').strip()
                
                return banner if banner else None
                
            finally:
                writer.close()
                await writer.wait_closed()
                
        except Exception:
            return None


class NetworkDiscovery:
    """Network discovery utilities."""
    
    @staticmethod
    async def ping_host(ip: str, timeout: int = 1) -> bool:
        """Ping a host to check if it's alive."""
        try:
            system = platform.system().lower()
            
            if system == "windows":
                cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), ip]
            else:
                cmd = ["ping", "-c", "1", "-W", str(timeout), ip]
            
            # Run ping in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                result = await loop.run_in_executor(
                    executor,
                    lambda: subprocess.run(cmd, capture_output=True, timeout=timeout + 1)
                )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.debug("Ping failed", ip=ip, error=str(e))
            return False
    
    @staticmethod
    def get_local_networks() -> List[str]:
        """Get local network ranges."""
        networks = []
        
        try:
            # Get local IP addresses
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            
            for ip in local_ips:
                if not ip.startswith('127.'):
                    try:
                        # Assume /24 subnet
                        network = IPv4Network(f"{ip}/24", strict=False)
                        networks.append(str(network))
                    except AddressValueError:
                        continue
            
            # Add common private networks if none found
            if not networks:
                networks = ['192.168.1.0/24', '192.168.0.0/24', '10.0.0.0/24']
            
        except Exception as e:
            logger.debug("Failed to get local networks", error=str(e))
            networks = ['192.168.1.0/24']
        
        return networks


class NetworkScanDiscovery(DiscoveryProtocol):
    """Network scanning discovery protocol implementation."""
    
    def __init__(self, config=None):
        super().__init__("network_scan")
        self.config = config
        if config:
            self.rate_limiter = RateLimiter(RateLimitConfig(
                per_host_limit=config.discovery.rate_limit_per_host,
                global_limit=config.discovery.rate_limit_global
            ))
        else:
            self.rate_limiter = RateLimiter(RateLimitConfig(
                per_host_limit=10,
                global_limit=100
            ))
        self.port_scanner = PortScanner(self.rate_limiter)
        self.max_concurrent_hosts = 50
        self.max_concurrent_ports = 10
    
    async def discover(self, networks: Optional[List[str]] = None, 
                      ports: Optional[List[int]] = None,
                      ping_first: bool = True,
                      **kwargs) -> DiscoveryResult:
        """Perform network scanning discovery."""
        start_time = time.time()
        result = DiscoveryResult(protocol=self.name)
        
        try:
            if not await self.is_available():
                result.success = False
                result.error = "Network scanning not available"
                return result
            
            # Use provided networks or auto-detect
            scan_networks = networks or NetworkDiscovery.get_local_networks()
            
            # Use provided ports or defaults
            scan_ports = ports or (PortScanner.COMMON_PORTS + PortScanner.IOT_PORTS)
            
            # Generate list of IPs to scan
            ips_to_scan = []
            for network_str in scan_networks:
                try:
                    network = IPv4Network(network_str)
                    # Limit to reasonable size
                    if network.num_addresses > 1024:
                        logger.warning("Network too large, skipping", network=network_str)
                        continue
                    
                    ips_to_scan.extend([str(ip) for ip in network.hosts()])
                except AddressValueError as e:
                    logger.warning("Invalid network", network=network_str, error=str(e))
                    continue
            
            if not ips_to_scan:
                result.success = False
                result.error = "No valid networks to scan"
                return result
            
            self.logger.info(
                "Starting network scan",
                networks=len(scan_networks),
                ips=len(ips_to_scan),
                ports=len(scan_ports)
            )
            
            # Scan hosts
            devices = await self._scan_hosts(ips_to_scan, scan_ports, ping_first)
            result.devices = devices
            
            self.logger.info(
                "Network scan completed",
                devices_found=len(devices),
                ips_scanned=len(ips_to_scan)
            )
            
        except Exception as e:
            result.success = False
            result.error = str(e)
            self.logger.error("Network scan failed", error=str(e), exc_info=e)
        
        result.duration = time.time() - start_time
        return result
    
    async def _scan_hosts(self, ips: List[str], ports: List[int], ping_first: bool) -> List[Device]:
        """Scan multiple hosts concurrently."""
        semaphore = asyncio.Semaphore(self.max_concurrent_hosts)
        
        async def scan_host_with_semaphore(ip: str) -> Optional[Device]:
            async with semaphore:
                return await self._scan_single_host(ip, ports, ping_first)
        
        # Scan all hosts concurrently
        tasks = [scan_host_with_semaphore(ip) for ip in ips]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful scans
        devices = [device for device in results if isinstance(device, Device)]
        return devices
    
    async def _scan_single_host(self, ip: str, ports: List[int], ping_first: bool) -> Optional[Device]:
        """Scan a single host."""
        try:
            # Ping first if requested
            if ping_first:
                if not await NetworkDiscovery.ping_host(ip, timeout=1):
                    return None
            
            # Scan ports
            open_ports = await self.port_scanner.scan_host(
                ip, ports, timeout=1.0, max_concurrent=self.max_concurrent_ports
            )
            
            if not open_ports:
                return None
            
            # Create device
            device = Device(
                ip_address=ip,
                ports=open_ports,
                discovery_protocol='network_scan',
                device_type=DeviceType.UNKNOWN,
                status=DeviceStatus.ONLINE
            )
            
            # Identify services
            services = []
            for port in open_ports[:5]:  # Limit service identification
                service_info = await ServiceIdentifier.identify_service(ip, port, timeout=2.0)
                if service_info:
                    services.append(service_info['name'])
                    device.capabilities[f'port_{port}'] = service_info
            
            device.services = services
            
            # Determine device type from ports and services
            device.device_type = self._determine_device_type(open_ports, services)
            
            # Try to get hostname
            try:
                hostname = socket.gethostbyaddr(ip)[0]
                device.hostname = hostname
            except (socket.herror, socket.gaierror):
                pass
            
            return device
            
        except Exception as e:
            self.logger.debug("Host scan failed", ip=ip, error=str(e))
            return None
    
    def _determine_device_type(self, ports: List[int], services: List[str]) -> DeviceType:
        """Determine device type from open ports and services."""
        ports_set = set(ports)
        services_str = ' '.join(services).lower()
        
        # Router/Gateway indicators
        if 80 in ports_set and 443 in ports_set and (22 in ports_set or 23 in ports_set):
            return DeviceType.ROUTER
        
        # Printer indicators
        if any(port in ports_set for port in [631, 9100, 515]) or 'printer' in services_str:
            return DeviceType.PRINTER
        
        # Media server indicators
        if any(port in ports_set for port in [8080, 8200, 32400]) or 'media' in services_str:
            return DeviceType.MEDIA_SERVER
        
        # IoT indicators
        if 1883 in ports_set or 'mqtt' in services_str:
            return DeviceType.IOT_GATEWAY
        
        # Camera indicators
        if any(port in ports_set for port in [554, 8000, 8080]) and 'http' in services_str:
            return DeviceType.CAMERA
        
        # Switch/Network device indicators
        if 161 in ports_set or (22 in ports_set and 80 in ports_set):
            return DeviceType.SWITCH
        
        # Generic IoT if has common IoT ports
        if any(port in ports_set for port in [5683, 8883, 5353]):
            return DeviceType.IOT_SENSOR
        
        return DeviceType.UNKNOWN
    
    async def is_available(self) -> bool:
        """Check if network scanning is available."""
        try:
            # Test basic socket operations
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(1)
            test_socket.close()
            
            # Test ping capability
            return await NetworkDiscovery.ping_host('127.0.0.1', timeout=1)
            
        except Exception as e:
            self.logger.debug("Network scanning not available", error=str(e))
            return False
