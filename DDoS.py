#This Script DoNot Use Proxy

import asyncio
import aiohttp
import random
import time
import os
import logging
import csv
from datetime import datetime
from urllib.parse import urlparse
import numpy as np
from collections import deque

# Configure logging
logging.basicConfig(
    filename=f"stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Clear screen
os.system('cls' if os.name == 'nt' else 'clear')

print('''\033[92m

███████╗ █████╗ ███╗   ███╗ ██████╗ ███████╗ ██████╗ 
██╔════╝██╔══██╗████╗ ████║██╔═══██╗██╔════╝██╔═══██╗
█████╗  ███████║██╔████╔██║██║   ██║███████╗██║   ██║
██╔══╝  ██╔══██║██║╚██╔╝██║██║   ██║╚════██║██║   ██║
██║     ██║  ██║██║ ╚═╝ ██║╚██████╔╝███████║╚██████╔╝
╚═╝     ╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚══════╝ ╚═════╝ 
                                                     

                       🔥 Ultimate Stress Testing Tool 🔥
                         🛡️ Developed by FAMOSO 🛡️
                               Telegram : @famosot
\033[0m''')

# User input with validation
def get_valid_url():
    while True:
        url = input("\n[?] Target URL (http:// or https://): ").strip()
        if url.startswith(("http://", "https://")):
            return url
        print("\033[91m[!] Invalid URL. Must start with http:// or https://\033[0m")

def get_valid_concurrency():
    while True:
        try:
            concurrency = int(input("[?] Number of Concurrent Tasks (e.g., 50-1000): "))
            if 50 <= concurrency <= 1000:
                return concurrency
            print("\033[91m[!] Concurrency must be between 50 and 1000\033[0m")
        except ValueError:
            print("\033[91m[!] Please enter a valid number\033[0m")

def get_valid_duration():
    while True:
        try:
            duration = int(input("[?] Test Duration in Seconds (e.g., 60-3600): "))
            if 60 <= duration <= 3600:
                return duration
            print("\033[91m[!] Duration must be between 60 and 3600 seconds\033[0m")
        except ValueError:
            print("\033[91m[!] Please enter a valid number\033[0m")

url = get_valid_url()
concurrency = get_valid_concurrency()
duration = get_valid_duration()

# Metrics
metrics = {
    "success": 0,
    "failures": 0,
    "latencies": deque(maxlen=10000),  # Store up to 10k latencies for percentile calc
    "start_time": time.time(),
    "requests": 0
}

async def stress_test(session, url, hostname, semaphore):
    global metrics
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    async with semaphore:  # Limit concurrency
        try:
            headers = {
                "User-Agent": random.choice(user_agents),
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "X-Stress-Test": f"StressTest-{hostname}"
            }
            start_time = time.time()
            async with session.get(url, headers=headers, timeout=10) as response:
                status = response.status
                latency = time.time() - start_time
                metrics["latencies"].append(latency)
                metrics["requests"] += 1
                if 200 <= status < 300:
                    metrics["success"] += 1
                    log_message = f"Success | Status: {status} | Latency: {latency:.2f}s | URL: {url}"
                    print(f"\033[94m[+] {log_message}\033[0m")
                    logging.info(log_message)
                else:
                    metrics["failures"] += 1
                    log_message = f"Failed | Status: {status} | Latency: {latency:.2f}s | URL: {url}"
                    print(f"\033[91m[-] {log_message}\033[0m")
                    logging.error(log_message)
        except Exception as e:
            metrics["failures"] += 1
            latency = time.time() - start_time
            metrics["latencies"].append(latency)
            metrics["requests"] += 1
            log_message = f"Failed | Error: {str(e)} | Latency: {latency:.2f}s | URL: {url}"
            print(f"\033[91m[-] {log_message}\033[0m")
            logging.error(log_message)

async def monitor_metrics(duration):
    while time.time() - metrics["start_time"] < duration:
        await asyncio.sleep(5)
        elapsed = time.time() - metrics["start_time"]
        total_requests = metrics["success"] + metrics["failures"]
        rps = total_requests / elapsed if elapsed > 0 else 0
        latencies = list(metrics["latencies"])
        p50 = np.percentile(latencies, 50) if latencies else 0
        p95 = np.percentile(latencies, 95) if latencies else 0
        p99 = np.percentile(latencies, 99) if latencies else 0
        success_rate = (metrics["success"] / total_requests * 100) if total_requests > 0 else 0
        print(f"\033[93m[Live Metrics] RPS: {rps:.2f}, Success Rate: {success_rate:.2f}%, "
              f"P50 Latency: {p50:.2f}s, P95 Latency: {p95:.2f}s, P99 Latency: {p99:.2f}s\033[0m")
        logging.info(f"Live Metrics: RPS={rps:.2f}, Success Rate={success_rate:.2f}%, "
                     f"P50 Latency={p50:.2f}s, P95 Latency={p95:.2f}s, P99 Latency={p99:.2f}s")

async def main():
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    semaphore = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as session:
        tasks = [stress_test(session, url, hostname, semaphore) for _ in range(concurrency)]
        tasks.append(monitor_metrics(duration))
        await asyncio.gather(*tasks)

# Save metrics to CSV
def save_metrics_to_csv():
    with open(f"stress_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Total Requests", "Success", "Failures", "Success Rate", "P50 Latency", "P95 Latency", "P99 Latency", "RPS"])
        total_requests = metrics["success"] + metrics["failures"]
        rps = total_requests / (time.time() - metrics["start_time"]) if (time.time() - metrics["start_time"]) > 0 else 0
        latencies = list(metrics["latencies"])
        p50 = np.percentile(latencies, 50) if latencies else 0
        p95 = np.percentile(latencies, 95) if latencies else 0
        p99 = np.percentile(latencies, 99) if latencies else 0
        success_rate = (metrics["success"] / total_requests * 100) if total_requests > 0 else 0
        writer.writerow([total_requests, metrics["success"], metrics["failures"], f"{success_rate:.2f}%", f"{p50:.2f}s", f"{p95:.2f}s", f"{p99:.2f}s", f"{rps:.2f}"])

print("\n[*] Starting stress test. Press Ctrl+C to stop early...\n")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\n[!] Stopping stress test...")
finally:
    save_metrics_to_csv()
    total_requests = metrics["success"] + metrics["failures"]
    rps = total_requests / (time.time() - metrics["start_time"]) if (time.time() - metrics["start_time"]) > 0 else 0
    latencies = list(metrics["latencies"])
    p50 = np.percentile(latencies, 50) if latencies else 0
    p95 = np.percentile(latencies, 95) if latencies else 0
    p99 = np.percentile(latencies, 99) if latencies else 0
    success_rate = (metrics["success"] / total_requests * 100) if total_requests > 0 else 0
    print(f"\n\033[92m[Final Summary] Total Requests: {total_requests}, Success: {metrics['success']}, "
          f"Failures: {metrics['failures']}, Success Rate: {success_rate:.2f}%, "
          f"P50 Latency: {p50:.2f}s, P95 Latency: {p95:.2f}s, P99 Latency: {p99:.2f}s, RPS: {rps:.2f}\033[0m")
    logging.info(f"Final Summary: Total Requests={total_requests}, Success={metrics['success']}, "
                 f"Failures={metrics['failures']}, Success Rate={success_rate:.2f}%, "
                 f"P50 Latency={p50:.2f}s, P95 Latency={p95:.2f}s, P99 Latency={p99:.2f}s, RPS={rps:.2f}")
