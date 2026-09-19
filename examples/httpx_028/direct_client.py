import httpx

client = httpx.Client(
    proxies={"https://": "http://localhost:8080"},
)

raise RuntimeError("Openfield must parse this fixture without executing it")
