import time
import requests
import statistics

def benchmark(url, name, n=10):
    print(f"Benchmarking {name} at {url} ({n} requests)...")
    times = []
    for _ in range(n):
        start = time.perf_counter()
        try:
            response = requests.get(url)
            response.raise_for_status()
            end = time.perf_counter()
            times.append(end - start)
        except Exception as e:
            print(f"  Error: {e}")
            return None
    
    avg = statistics.mean(times)
    med = statistics.median(times)
    print(f"  Average: {avg:.4f}s")
    print(f"  Median:  {med:.4f}s")
    return {"avg": avg, "med": med}

def main():
    # Note: This assumes both servers are running.
    # Flask: python app.py (usually port 5000)
    # FastAPI: uvicorn main:app (usually port 8000)
    
    flask_url = "http://localhost:5000/api/articles"
    fastapi_url = "http://localhost:8000/api/articles"
    
    results = {}
    
    # Try Flask
    res_flask = benchmark(flask_url, "Flask (Legacy)")
    if res_flask:
        results["flask"] = res_flask
        
    # Try FastAPI
    res_fastapi = benchmark(fastapi_url, "FastAPI (Modern)")
    if res_fastapi:
        results["fastapi"] = res_fastapi
        
    if "flask" in results and "fastapi" in results:
        diff = ((results["flask"]["avg"] - results["fastapi"]["avg"]) / results["flask"]["avg"]) * 100
        print(f"\nFastAPI is {diff:.2f}% {'faster' if diff > 0 else 'slower'} than Flask on average.")

if __name__ == "__main__":
    main()
