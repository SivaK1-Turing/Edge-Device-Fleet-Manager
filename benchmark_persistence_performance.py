#!/usr/bin/env python3
"""
Performance Benchmark for Feature 5: Robust Persistence & Migrations

Benchmarks 1M-row bulk inserts via Core vs. ORM, exports results to CSV,
and provides visualization data for the visualization module.
"""

import asyncio
import sys
import time
import uuid
import csv
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig
from edge_device_fleet_manager.persistence.connection.manager import DatabaseManager
from edge_device_fleet_manager.persistence.models.telemetry import TelemetryEvent, TelemetryType
from edge_device_fleet_manager.persistence.repositories.telemetry import TelemetryRepository
from sqlalchemy import text, insert
from sqlalchemy.ext.asyncio import AsyncSession


class PerformanceBenchmark:
    """Performance benchmark for persistence operations."""
    
    def __init__(self, database_url: str = "sqlite+aiosqlite:///benchmark.db"):
        """Initialize benchmark with database configuration."""
        self.config = DatabaseConfig(
            database_url=database_url,
            pool_size=10,
            max_overflow=20,
            enable_health_checks=False  # Disable for performance
        )
        self.manager = None
        self.results = []
    
    async def setup(self):
        """Setup database and tables."""
        print("🔧 Setting up benchmark environment...")
        
        self.manager = DatabaseManager(self.config)
        await self.manager.initialize()
        
        # Create tables
        from edge_device_fleet_manager.persistence.models.base import Base
        async with self.manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Benchmark environment ready")
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.manager:
            await self.manager.shutdown()
    
    def generate_test_data(self, count: int) -> List[Dict[str, Any]]:
        """Generate test telemetry data."""
        print(f"📊 Generating {count:,} test records...")
        
        base_time = datetime.now(timezone.utc)
        device_ids = [uuid.uuid4() for _ in range(100)]  # 100 different devices
        
        data = []
        for i in range(count):
            data.append({
                'id': uuid.uuid4(),
                'device_id': device_ids[i % len(device_ids)],
                'event_type': TelemetryType.SENSOR_DATA,
                'event_name': f'sensor_reading_{i % 10}',
                'numeric_value': 20.0 + (i % 100) * 0.1,
                'units': 'celsius',
                'timestamp': base_time + timedelta(seconds=i),
                'received_at': base_time + timedelta(seconds=i, milliseconds=50),
                'processed': False,
                'quality_score': 0.95,
                'confidence_level': 0.98,
                'data': {'sensor_id': f'sensor_{i % 50}', 'location': f'room_{i % 20}'}
            })
        
        print(f"✅ Generated {len(data):,} test records")
        return data
    
    async def benchmark_orm_insert(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Benchmark ORM-based bulk insert."""
        print(f"🔍 Benchmarking ORM bulk insert ({len(data):,} records)...")
        
        start_time = time.time()
        memory_start = self._get_memory_usage()
        
        async with self.manager.get_transaction() as session:
            repo = TelemetryRepository(session)
            
            # Use repository bulk_create method
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                await repo.bulk_create(batch)
                total_inserted += len(batch)
                
                if total_inserted % 10000 == 0:
                    print(f"  📈 Inserted {total_inserted:,} records...")
        
        end_time = time.time()
        memory_end = self._get_memory_usage()
        
        duration = end_time - start_time
        records_per_second = len(data) / duration
        memory_used = memory_end - memory_start
        
        result = {
            'method': 'ORM',
            'records': len(data),
            'duration_seconds': duration,
            'records_per_second': records_per_second,
            'memory_mb': memory_used,
            'batch_size': batch_size
        }
        
        print(f"✅ ORM Insert: {len(data):,} records in {duration:.2f}s ({records_per_second:.0f} rec/s)")
        return result
    
    async def benchmark_core_insert(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Benchmark Core SQL bulk insert."""
        print(f"🔍 Benchmarking Core SQL bulk insert ({len(data):,} records)...")
        
        start_time = time.time()
        memory_start = self._get_memory_usage()
        
        async with self.manager.get_transaction() as session:
            # Use Core SQL with bulk insert
            batch_size = 5000  # Larger batches for Core SQL
            total_inserted = 0
            
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                
                # Convert to format suitable for Core SQL
                insert_data = []
                for record in batch:
                    insert_data.append({
                        'id': str(record['id']),
                        'device_id': str(record['device_id']),
                        'event_type': record['event_type'].value,
                        'event_name': record['event_name'],
                        'numeric_value': record['numeric_value'],
                        'units': record['units'],
                        'timestamp': record['timestamp'],
                        'received_at': record['received_at'],
                        'processed': record['processed'],
                        'quality_score': record['quality_score'],
                        'confidence_level': record['confidence_level'],
                        'data': json.dumps(record['data'])
                    })
                
                # Use Core SQL insert
                stmt = insert(TelemetryEvent.__table__).values(insert_data)
                await session.execute(stmt)
                
                total_inserted += len(batch)
                
                if total_inserted % 10000 == 0:
                    print(f"  📈 Inserted {total_inserted:,} records...")
        
        end_time = time.time()
        memory_end = self._get_memory_usage()
        
        duration = end_time - start_time
        records_per_second = len(data) / duration
        memory_used = memory_end - memory_start
        
        result = {
            'method': 'Core SQL',
            'records': len(data),
            'duration_seconds': duration,
            'records_per_second': records_per_second,
            'memory_mb': memory_used,
            'batch_size': batch_size
        }
        
        print(f"✅ Core SQL Insert: {len(data):,} records in {duration:.2f}s ({records_per_second:.0f} rec/s)")
        return result
    
    async def benchmark_query_performance(self) -> Dict[str, Any]:
        """Benchmark query performance after bulk insert."""
        print("🔍 Benchmarking query performance...")
        
        queries = [
            ("Count all records", "SELECT COUNT(*) FROM telemetry_events"),
            ("Count by event type", "SELECT event_type, COUNT(*) FROM telemetry_events GROUP BY event_type"),
            ("Average numeric value", "SELECT AVG(numeric_value) FROM telemetry_events WHERE numeric_value IS NOT NULL"),
            ("Recent records", "SELECT COUNT(*) FROM telemetry_events WHERE timestamp > datetime('now', '-1 hour')"),
            ("Device statistics", "SELECT device_id, COUNT(*), AVG(numeric_value) FROM telemetry_events GROUP BY device_id LIMIT 10")
        ]
        
        query_results = []
        
        async with self.manager.get_session() as session:
            for query_name, query_sql in queries:
                start_time = time.time()
                
                result = await session.execute(text(query_sql))
                rows = result.fetchall()
                
                end_time = time.time()
                duration = end_time - start_time
                
                query_results.append({
                    'query': query_name,
                    'duration_seconds': duration,
                    'rows_returned': len(rows)
                })
                
                print(f"  📊 {query_name}: {duration:.3f}s ({len(rows)} rows)")
        
        return {'queries': query_results}
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0  # psutil not available
    
    def export_results_to_csv(self, filename: str = "benchmark_results.csv"):
        """Export benchmark results to CSV."""
        print(f"📄 Exporting results to {filename}...")
        
        with open(filename, 'w', newline='') as csvfile:
            if not self.results:
                print("❌ No results to export")
                return
            
            fieldnames = self.results[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.results:
                writer.writerow(result)
        
        print(f"✅ Results exported to {filename}")
    
    def generate_visualization_data(self) -> Dict[str, Any]:
        """Generate data for visualization module."""
        if not self.results:
            return {}
        
        # Prepare data for charts
        methods = [r['method'] for r in self.results if 'method' in r]
        durations = [r['duration_seconds'] for r in self.results if 'duration_seconds' in r]
        throughputs = [r['records_per_second'] for r in self.results if 'records_per_second' in r]
        
        visualization_data = {
            'benchmark_summary': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_records_tested': max([r.get('records', 0) for r in self.results]),
                'methods_compared': len(methods)
            },
            'performance_comparison': {
                'methods': methods,
                'durations_seconds': durations,
                'throughput_records_per_second': throughputs
            },
            'charts': {
                'duration_comparison': {
                    'type': 'bar',
                    'title': 'Insert Duration Comparison',
                    'x_axis': methods,
                    'y_axis': durations,
                    'y_label': 'Duration (seconds)'
                },
                'throughput_comparison': {
                    'type': 'bar',
                    'title': 'Throughput Comparison',
                    'x_axis': methods,
                    'y_axis': throughputs,
                    'y_label': 'Records per Second'
                }
            }
        }
        
        # Save visualization data
        with open('benchmark_visualization_data.json', 'w') as f:
            json.dump(visualization_data, f, indent=2)
        
        print("📊 Visualization data saved to benchmark_visualization_data.json")
        return visualization_data
    
    async def run_full_benchmark(self, record_counts: List[int] = None):
        """Run complete benchmark suite."""
        if record_counts is None:
            record_counts = [1000, 10000, 100000]  # Start smaller for testing
        
        print("🚀 Starting Performance Benchmark Suite")
        print("=" * 60)
        
        await self.setup()
        
        try:
            for count in record_counts:
                print(f"\n📊 Benchmarking with {count:,} records")
                print("-" * 40)
                
                # Generate test data
                test_data = self.generate_test_data(count)
                
                # Clear existing data
                async with self.manager.get_transaction() as session:
                    await session.execute(text("DELETE FROM telemetry_events"))
                
                # Benchmark ORM insert
                orm_result = await self.benchmark_orm_insert(test_data)
                self.results.append(orm_result)
                
                # Clear data for next test
                async with self.manager.get_transaction() as session:
                    await session.execute(text("DELETE FROM telemetry_events"))
                
                # Benchmark Core SQL insert
                core_result = await self.benchmark_core_insert(test_data)
                self.results.append(core_result)
                
                # Query performance test (using Core SQL data)
                query_result = await self.benchmark_query_performance()
                
                print(f"\n📈 Results for {count:,} records:")
                print(f"  ORM: {orm_result['duration_seconds']:.2f}s ({orm_result['records_per_second']:.0f} rec/s)")
                print(f"  Core SQL: {core_result['duration_seconds']:.2f}s ({core_result['records_per_second']:.0f} rec/s)")
                
                speedup = orm_result['duration_seconds'] / core_result['duration_seconds']
                print(f"  Core SQL is {speedup:.1f}x faster than ORM")
            
            # Export results
            self.export_results_to_csv()
            
            # Generate visualization data
            viz_data = self.generate_visualization_data()
            
            print("\n" + "=" * 60)
            print("🎉 Benchmark Complete!")
            print(f"📄 Results exported to: benchmark_results.csv")
            print(f"📊 Visualization data: benchmark_visualization_data.json")
            
            return viz_data
            
        finally:
            await self.cleanup()


async def main():
    """Main benchmark execution."""
    benchmark = PerformanceBenchmark()
    
    # For the 1M record test mentioned in the prompt, use:
    # record_counts = [1000000]  # 1M records
    
    # For testing, start with smaller counts:
    record_counts = [1000, 10000, 100000]
    
    await benchmark.run_full_benchmark(record_counts)


if __name__ == "__main__":
    asyncio.run(main())
