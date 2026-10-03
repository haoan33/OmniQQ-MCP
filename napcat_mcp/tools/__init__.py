"""
NapCat MCP 工具注册表与 Schema 自动生成器
将 Python 异步函数自动映射为符合 MCP 标准规范的 Tool 定义与 JSON Schema。
"""
import inspect
from typing import Any, Callable, Dict, List, Optional, Union, get_type_hints, get_origin, get_args


class ToolRegistry:
    """MCP 工具注册与分发中心"""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        schema_override: Optional[Dict[str, Any]] = None
    ):
        """装饰器：将异步函数注册为 MCP Tool"""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_desc = (description or inspect.getdoc(func) or "").strip()
            input_schema = schema_override or self._build_json_schema(func)
            self._tools[tool_name] = {
                "name": tool_name,
                "description": tool_desc,
                "inputSchema": input_schema,
                "handler": func
            }
            return func
        return decorator

    @staticmethod
    def _py_type_to_json_type(py_type: Any) -> Dict[str, Any]:
        """将 Python 类型注解转换为 JSON Schema 属性定义"""
        origin = get_origin(py_type)
        args = get_args(py_type)

        # 处理 Optional[T] / Union[T, None]
        if origin is Union:
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                return ToolRegistry._py_type_to_json_type(non_none[0])
            return {"type": "string"}

        if py_type is int:
            return {"type": "integer"}
        if py_type is float:
            return {"type": "number"}
        if py_type is bool:
            return {"type": "boolean"}
        if py_type is str:
            return {"type": "string"}
        if py_type is list or origin is list:
            return {"type": "array", "items": {}}
        if py_type is dict or origin is dict:
            return {"type": "object"}
        return {"type": "string"}

    @classmethod
    def _build_json_schema(cls, func: Callable) -> Dict[str, Any]:
        """从函数签名与 docstring 提取参数说明并构造标准 JSON Schema"""
        sig = inspect.signature(func)
        try:
            hints = get_type_hints(func)
        except Exception:
            hints = {}

        # 解析 docstring 中的 :param xxx: 说明
        doc = inspect.getdoc(func) or ""
        param_docs: Dict[str, str] = {}
        for line in doc.splitlines():
            line_s = line.strip()
            if line_s.startswith(":param "):
                rest = line_s[len(":param "):]
                if ":" in rest:
                    p_name, p_desc = rest.split(":", 1)
                    param_docs[p_name.strip()] = p_desc.strip()

        properties: Dict[str, Any] = {}
        required: List[str] = []

        for param_name, param in sig.parameters.items():
            # 跳过内部注入的 client 参数
            if param_name == "client":
                continue

            py_t = hints.get(param_name, str)
            prop_schema = cls._py_type_to_json_type(py_t)

            if param_name in param_docs:
                prop_schema["description"] = param_docs[param_name]

            if param.default is inspect.Parameter.empty:
                required.append(param_name)
            else:
                if param.default is not None:
                    prop_schema["default"] = param.default

            properties[param_name] = prop_schema

        schema: Dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        return schema

    def list_tools(self) -> List[Dict[str, Any]]:
        """返回符合 MCP `tools/list` 标准响应格式的工具列表"""
        return [
            {
                "name": info["name"],
                "description": info["description"],
                "inputSchema": info["inputSchema"]
            }
            for info in self._tools.values()
        ]

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    @property
    def tools_map(self) -> Dict[str, Dict[str, Any]]:
        return self._tools


# 全局单例注册表
registry = ToolRegistry()
