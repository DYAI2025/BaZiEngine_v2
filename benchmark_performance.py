#!/usr/bin/env python3
"""
Performance Benchmark for BaZi Engine

Tests actual throughput and response times under various loads.

Prerequisites:
    pip install -e .

Usage:
    python benchmark_performance.py

Alternative (Docker):
    docker build -t bazi-engine .
    docker run --rm bazi-engine python benchmark_performance.py
"""

import time
import statistics
from datetime import datetime
from bazi_engine import compute_bazi, BaziInput


def benchmark_single_request():
    """Measure single request performance."""
    inp = BaziInput(
        birth_local="2024-02-10T14:30:00",
        timezone="Europe/Berlin",
        longitude_deg=13.4050,
        latitude_deg=52.52,
        time_standard="CIVIL",
        day_boundary="midnight",
    )

    start = time.perf_counter()
    result = compute_bazi(inp)
    end = time.perf_counter()

    return (end - start) * 1000  # Convert to milliseconds


def benchmark_sequential(num_requests=100):
    """Measure sequential throughput."""
    times = []

    print(f"\n🔍 Sequential Benchmark ({num_requests} requests)...")

    start_total = time.perf_counter()

    for i in range(num_requests):
        t = benchmark_single_request()
        times.append(t)

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{num_requests}")

    end_total = time.perf_counter()
    total_time = end_total - start_total

    return times, total_time


def print_statistics(times, total_time, num_requests):
    """Print performance statistics."""
    mean = statistics.mean(times)
    median = statistics.median(times)
    stdev = statistics.stdev(times) if len(times) > 1 else 0
    min_time = min(times)
    max_time = max(times)

    # Percentiles
    sorted_times = sorted(times)
    p95 = sorted_times[int(len(sorted_times) * 0.95)]
    p99 = sorted_times[int(len(sorted_times) * 0.99)]

    throughput = num_requests / total_time

    print("\n" + "="*60)
    print("📊 PERFORMANCE STATISTICS")
    print("="*60)
    print(f"\nTotal Requests:     {num_requests}")
    print(f"Total Time:         {total_time:.2f}s")
    print(f"\n--- Response Times ---")
    print(f"Mean:               {mean:.2f}ms")
    print(f"Median:             {median:.2f}ms")
    print(f"Std Dev:            {stdev:.2f}ms")
    print(f"Min:                {min_time:.2f}ms")
    print(f"Max:                {max_time:.2f}ms")
    print(f"P95:                {p95:.2f}ms")
    print(f"P99:                {p99:.2f}ms")
    print(f"\n--- Throughput ---")
    print(f"Requests/Second:    {throughput:.2f}")
    print(f"Requests/Minute:    {throughput * 60:.2f}")
    print(f"Requests/Hour:      {throughput * 3600:.2f}")
    print("="*60)


def estimate_capacity(throughput):
    """Estimate user capacity based on throughput."""
    print("\n" + "="*60)
    print("👥 ESTIMATED USER CAPACITY")
    print("="*60)

    # Assumptions
    avg_requests_per_user = 1.5  # User might calculate 1-2 charts per session

    users_per_minute = (throughput * 60) / avg_requests_per_user
    users_per_hour = users_per_minute * 60
    users_per_day = users_per_hour * 24

    print(f"\nAssuming {avg_requests_per_user} requests per user:")
    print(f"  Users/Minute:     ~{int(users_per_minute)}")
    print(f"  Users/Hour:       ~{int(users_per_hour)}")
    print(f"  Users/Day:        ~{int(users_per_day)}")

    print("\n--- Scaling Recommendations ---")
    if throughput < 20:
        print("  ⚠️  LOW: Consider multi-worker configuration")
    elif throughput < 50:
        print("  ✅ GOOD: Suitable for small apps (<1K users/day)")
    elif throughput < 100:
        print("  🚀 EXCELLENT: Suitable for medium apps (<10K users/day)")
    else:
        print("  ⭐ OUTSTANDING: Suitable for large apps (>10K users/day)")

    print("="*60)


def main():
    print("="*60)
    print("🧮 BaZi Engine Performance Benchmark")
    print("="*60)

    # Warmup
    print("\n🔥 Warming up (5 requests)...")
    for _ in range(5):
        benchmark_single_request()
    print("  ✓ Warmup complete")

    # Benchmark
    num_requests = 100
    times, total_time = benchmark_sequential(num_requests)

    # Statistics
    print_statistics(times, total_time, num_requests)

    # Capacity estimation
    throughput = num_requests / total_time
    estimate_capacity(throughput)

    print("\n✅ Benchmark complete!\n")


if __name__ == "__main__":
    main()
