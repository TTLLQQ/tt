import ast
import math
import operator
import random
import os
import re
from datetime import datetime


def calculator(expression: str) -> str:
    if len(expression) > 160:
        raise ValueError("Expression is too long")
    tree = ast.parse(expression, mode="eval")
    binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
    unary = {ast.UAdd: operator.pos, ast.USub: operator.neg}

    def evaluate(node, depth=0):
        if depth > 20:
            raise ValueError("Expression is too deeply nested")
        if isinstance(node, ast.Expression):
            return evaluate(node.body, depth + 1)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float) and abs(node.value) <= 1e12:
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in unary:
            value = unary[type(node.op)](evaluate(node.operand, depth + 1))
        elif isinstance(node, ast.BinOp) and type(node.op) in binary:
            left, right = evaluate(node.left, depth + 1), evaluate(node.right, depth + 1)
            if isinstance(node.op, ast.Pow) and (not isinstance(right, (int, float)) or abs(right) > 8):
                raise ValueError("Exponent must be between -8 and 8")
            value = binary[type(node.op)](left, right)
        else:
            raise ValueError("Only bounded numeric arithmetic is allowed")
        if not isinstance(value, (int, float)) or abs(value) > 1e12:
            raise ValueError("Intermediate result exceeds the allowed range")
        return value

    try:
        result = evaluate(tree)
    except (ArithmeticError, OverflowError) as error:
        raise ValueError(f"Invalid arithmetic expression: {error}") from error
    if not math.isfinite(result):
        raise ValueError("Result is not a finite number")
    return str(result)


def date_format(date_text: str = "") -> str:
    if not date_text:
        return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    parsed = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def text_process(text: str, operation: str = "trim") -> str:
    if len(text) > 5000 or operation not in {"trim", "upper", "lower", "word_count"}:
        raise ValueError("Unsupported text operation or input too long")
    return {"trim": lambda: text.strip(), "upper": lambda: text.upper(), "lower": lambda: text.lower(), "word_count": lambda: str(len(re.findall(r"\w+", text)))}[operation]()


def random_number(minimum: int = 1, maximum: int = 100) -> int:
    if minimum > maximum or maximum - minimum > 1_000_000:
        raise ValueError("Invalid random number range")
    return random.randint(minimum, maximum)


def weather_lookup(city: str) -> str:
    api_key = os.getenv("WEATHER_API_KEY", "")
    if not api_key:
        raise RuntimeError("Weather provider is not configured; set WEATHER_API_KEY to enable it")
    if not city.strip() or len(city) > 100:
        raise ValueError("City is required and must be at most 100 characters")
    import httpx

    try:
        response = httpx.get("https://api.openweathermap.org/data/2.5/weather", params={"q": city, "appid": api_key, "units": "metric"}, timeout=8)
        response.raise_for_status()
        data = response.json()
        return f"{data.get('name', city)}: {data.get('main', {}).get('temp')}°C, {data.get('weather', [{}])[0].get('description', '')}"
    except httpx.HTTPError as error:
        raise RuntimeError("Weather provider request failed") from error


REGISTRY = {
    "calculator": calculator,
    "date_format": date_format,
    "text_process": text_process,
    "random_number": random_number,
    "weather_lookup": weather_lookup,
}


def execute_builtin(key: str, arguments: dict):
    function = REGISTRY.get(key)
    if function is None:
        raise ValueError("Tool is not allow-listed")
    return function(**arguments)
