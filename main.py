from fastmcp import FastMCP

mcp = FastMCP(name="calculator")


@mcp.tool
def multiply(a: float, b: float) -> float:
    """Multiplies two numbers together."""
    print(f"[MCP 서버] 곱셈 요청: {a} * {b}")
    return a * b


@mcp.tool
def add(a: float, b: float) -> float:
    """Adds two numbers together."""
    print(f"[MCP 서버] 덧셈 요청: {a} + {b}")
    return a + b


@mcp.tool
def subtract(a: float, b: float) -> float:
    """Subtracts the second number from the first."""
    print(f"[MCP 서버] 뺄셈 요청: {a} - {b}")
    return a - b


# @mcp.tool
# def divide(a: float, b: float) -> float:
#     """Divides the first number by the second. Division by zero is not allowed."""
#     print(f"[MCP 서버] 나눗셈 요청: {a} / {b}")
#     if b == 0:
#         raise ValueError("Division by zero is not allowed.")
#     return a / b


@mcp.tool
def square(a: float) -> float:
    """Squares a number."""
    print(f"[MCP 서버] 제곱 요청: {a}^2")
    return a * a


@mcp.tool
def power(a: float, b: float) -> float:
    """Raises a to the power of b."""
    print(f"[MCP 서버] 거듭제곱 요청: {a}^{b}")
    return a ** b


@mcp.tool
def greeting_length(greeting: str) -> int:
    """Returns the character count of a greeting message."""
    print(f"[MCP 서버] 인사말 글자 수 계산 요청: '{greeting}'")
    return len(greeting)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8080,
        log_level="debug",
    )
