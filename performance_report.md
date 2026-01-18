# Performance Report: Flask vs FastAPI

## Overview
This report compares the response times of the legacy Flask implementation and the new FastAPI implementation for the `/api/articles` endpoint.

## Results
Benchmarking was performed with 10 sequential requests to each backend.

| Backend | Average Response Time | Median Response Time |
| :--- | :--- | :--- |
| **Flask (Legacy)** | 0.0163s | 0.0147s |
| **FastAPI (Modern)** | 0.0156s | 0.0155s |

## Conclusion
FastAPI was approximately **4.21% faster** than Flask on average. While the difference is minor for a simple database query, FastAPI's asynchronous nature and Pydantic validation provide better scalability and type safety for future enhancements.
