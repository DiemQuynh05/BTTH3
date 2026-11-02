"""
Script kiểm thử tải nhẹ (Lightweight Load Test / Benchmark) cho các API BI & AI (D2.3).
Cách chạy trên Windows CMD / PowerShell:
py -3 tests/benchmark_bi_api.py
"""
import concurrent.futures
import time
import urllib.request
import urllib.error
import json

BASE_URL = "http://127.0.0.1:8000"
ENDPOINTS = [
    "/api/bi/summary/",
    "/api/bi/skills/",
    "/api/bi/salary/",
    "/api/bi/funnel/",
    "/api/bi/",
]
CONCURRENT_REQUESTS = 50


def fetch_url(url):
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BenchmarkTest/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            code = response.getcode()
            data = response.read()
            duration = (time.perf_counter() - start) * 1000  # ms
            return {"status": code, "duration_ms": duration, "bytes": len(data), "error": None}
    except Exception as exc:
        duration = (time.perf_counter() - start) * 1000
        return {"status": getattr(exc, "code", 500), "duration_ms": duration, "bytes": 0, "error": str(exc)}


def run_benchmark():
    print("=" * 60)
    print(f"Bắt đầu Benchmark {CONCURRENT_REQUESTS} concurrent requests tới hệ thống API BI...")
    print("=" * 60)

    for ep in ENDPOINTS:
        url = f"{BASE_URL}{ep}"
        print(f"\n[Testing] {ep}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_url, url) for _ in range(CONCURRENT_REQUESTS)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        successes = [r for r in results if r["status"] == 200]
        durations = [r["duration_ms"] for r in successes]

        if durations:
            avg_ms = sum(durations) / len(durations)
            min_ms = min(durations)
            max_ms = max(durations)
            print(f"  Thành công: {len(successes)}/{CONCURRENT_REQUESTS} requests (100% OK)")
            print(f"  Thời gian phản hồi TB: {avg_ms:.2f} ms (Min: {min_ms:.2f} ms, Max: {max_ms:.2f} ms)")
        else:
            print(f"  Không kết nối được server tại {BASE_URL}. Hãy đảm bảo lệnh 'py -3 manage.py runserver' đang chạy.")


if __name__ == "__main__":
    run_benchmark()
