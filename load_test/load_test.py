
import asyncio
import time
import statistics
import json
import uuid
from typing import List, Dict, Any
import httpx


class LoadTestConfig:
    """Configuration for load test."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        num_requests: int = 3000,
        concurrent_requests: int = 100,
        num_users: int = 100
    ):
        self.base_url = base_url
        self.num_requests = num_requests
        self.concurrent_requests = concurrent_requests
        self.num_users = num_users
        self.target_rps = 300  # Target requests per second


class LoadTestResults:
    """Containner for load test results."""
    
    def __init__(self):
        self.latencies: List[float] = []
        self.errors: int = 0
        self.total_requests: int = 0
        self.start_time: float = 0
        self.end_time: float = 0
    
    def add_latency(self, latency: float):
        """Add a latency measurement."""
        self.latencies.append(latency)
    
    def add_error(self):
        """Increment error count."""
        self.errors += 1
    
    def increment_total(self):
        """Increment total request count."""
        self.total_requests += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from results."""
        if not self.latencies:
            return {
                "total_requests": self.total_requests,
                "successful_requests": 0,
                "errors": self.errors,
                "error_rate": 1.0 if self.total_requests > 0 else 0,
                "duration_seconds": self.end_time - self.start_time,
                "rps": 0,
                "min_latency_ms": 0,
                "max_latency_ms": 0,
                "mean_latency_ms": 0,
                "p50_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0
            }
        
        latencies_ms = [l * 1000 for l in self.latencies]
        duration = self.end_time - self.start_time
        
        latencies_ms.sort()
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": len(self.latencies),
            "errors": self.errors,
            "error_rate": self.errors / self.total_requests if self.total_requests > 0 else 0,
            "duration_seconds": duration,
            "rps": len(self.latencies) / duration if duration > 0 else 0,
            "min_latency_ms": min(latencies_ms),
            "max_latency_ms": max(latencies_ms),
            "mean_latency_ms": statistics.mean(latencies_ms),
            "median_latency_ms": statistics.median(latencies_ms),
            "p95_latency_ms": self._percentile(latencies_ms, 95),
            "p99_latency_ms": self._percentile(latencies_ms, 99),
        }
    
    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile from sorted data."""
        if not data:
            return 0
        index = int((percentile / 100) * len(data))
        return data[min(index, len(data) - 1)]


class LoadTester:
    """Load test executor."""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.results = LoadTestResults()
    
    async def run(self):
        """Run the load test."""
        print(f"Starting load test...")
        print(f"  Base URL: {self.config.base_url}")
        print(f"  Total requests: {self.config.num_requests}")
        print(f"  Concurrent requests: {self.config.concurrent_requests}")
        print(f"  Target RPS: {self.config.target_rps}")
        print()
        
        self.results.start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create batches of requests
            tasks = []
            for i in range(self.config.num_requests):
                if len(tasks) >= self.config.concurrent_requests:
                    # Execute batch
                    await asyncio.gather(*tasks)
                    tasks = []
                
                task = self._make_request(client, i)
                tasks.append(task)
            
            # Execute remaining tasks
            if tasks:
                await asyncio.gather(*tasks)
        
        self.results.end_time = time.time()
        self._print_results()
    
    async def _make_request(self, client: httpx.AsyncClient, request_id: int):
        """Make a single request."""
        try:
            user_id = f"user_{request_id % self.config.num_users}"
            merchant_id = f"merchant_{request_id % 50}"
            amount = 100 + (request_id % 900)
            
            payload = {
                "txn_id": str(uuid.uuid4()),
                "user_id": user_id,
                "merchant_id": merchant_id,
                "amount": float(amount),
                "txn_type": "purchase",
                "ts": int(time.time())
            }
            
            start = time.time()
            response = await client.post(
                f"{self.config.base_url}/reward/decide",
                json=payload
            )
            latency = time.time() - start
            
            self.results.increment_total()
            
            if response.status_code == 200:
                self.results.add_latency(latency)
            else:
                self.results.add_error()
                print(f"Error: {response.status_code} - {response.text}")
        
        except Exception as e:
            self.results.increment_total()
            self.results.add_error()
            print(f"Request failed: {e}")
    
    def _print_results(self):
        """Print test results."""
        stats = self.results.get_stats()
        
        print("\n" + "="*60)
        print("LOAD TEST RESULTS")
        print("="*60)
        print(f"Total Requests:       {stats['total_requests']}")
        print(f"Successful Requests:  {stats['successful_requests']}")
        print(f"Failed Requests:      {stats['errors']}")
        print(f"Error Rate:           {stats['error_rate']*100:.2f}%")
        print(f"Duration:             {stats['duration_seconds']:.2f}s")
        print(f"Throughput (RPS):     {stats['rps']:.2f} req/s")
        print(f"Target RPS:           {self.config.target_rps} req/s")
        print("-"*60)
        print(f"Min Latency:          {stats['min_latency_ms']:.2f}ms")
        print(f"Max Latency:          {stats['max_latency_ms']:.2f}ms")
        print(f"Mean Latency:         {stats['mean_latency_ms']:.2f}ms")
        print(f"Median Latency:       {stats['median_latency_ms']:.2f}ms")
        print(f"P95 Latency:          {stats['p95_latency_ms']:.2f}ms")
        print(f"P99 Latency:          {stats['p99_latency_ms']:.2f}ms")
        print("="*60)
        
        # Assessment
        print("\nPerformance Assessment:")
        if stats['rps'] >= self.config.target_rps * 0.95:
            print("✓ Throughput target MET (≥95% of target)")
        else:
            print(f"✗ Throughput target NOT MET ({stats['rps']:.2f} < {self.config.target_rps})")
        
        if stats['p95_latency_ms'] < 100:
            print("✓ P95 Latency is good (<100ms)")
        elif stats['p95_latency_ms'] < 200:
            print("◐ P95 Latency is acceptable (<200ms)")
        else:
            print("✗ P95 Latency is high (>200ms)")
        
        if stats['p99_latency_ms'] < 200:
            print("✓ P99 Latency is good (<200ms)")
        elif stats['p99_latency_ms'] < 500:
            print("◐ P99 Latency is acceptable (<500ms)")
        else:
            print("✗ P99 Latency is high (>500ms)")
        
        if stats['error_rate'] < 0.01:
            print("✓ Error rate is excellent (<1%)")
        elif stats['error_rate'] < 0.05:
            print("◐ Error rate is acceptable (<5%)")
        else:
            print("✗ Error rate is high (>5%)")
        
        print("\nBottleneck Analysis:")
        if stats['p99_latency_ms'] > 500:
            print("  - High tail latency suggests possible cache misses or GC pauses")
            print("  - Consider optimizing cache layer or increasing memory")
        
        if stats['rps'] < self.config.target_rps * 0.8:
            print("  - Low throughput suggests CPU or I/O bottleneck")
            print("  - Consider profiling the application")
            print("  - Check if background jobs are consuming resources")
        
        # Save results to file
        with open("load_test_results.json", "w") as f:
            json.dump(stats, f, indent=2)
        print("\nResults saved to load_test_results.json")


async def main():
    """Main entry point."""
    # Configure test parameters
    config = LoadTestConfig(
        base_url="http://localhost:8000",
        num_requests=3000,
        concurrent_requests=100,
        num_users=100
    )
    
    tester = LoadTester(config)
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
