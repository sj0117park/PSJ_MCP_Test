# PSJ_MCP_Test

FastMCP 기반 계산기 MCP 서버 (streamable-http, 포트 8080).

## 제공 Tool

- `add(a, b)`, `subtract(a, b)`, `multiply(a, b)`
- `square(a)`, `power(a, b)`
- `greeting_length(greeting)`

## 실행

```bash
uv sync
uv run main.py
```

서버 엔드포인트: `http://<host>:8080/mcp`

## 참고

의존성은 공개 PyPI(`https://pypi.org/simple`)에서 설치됩니다.
