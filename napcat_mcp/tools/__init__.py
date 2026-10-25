"""
NapCat MCP 工具注册表与 Schema 自动生成器
将 Python 异步函数自动映射为符合 MCP 标准规范的 Tool 定义、Annotations 与 JSON Schema。
"""
import inspect
import os
import types
from typing import Any, Callable, Dict, List, Optional, Union, get_type_hints, get_origin, get_args

# 默认暴露的 19 个核心与纯本地工具（14 个高频核心工具 + 5 个无 OneBot HTTP 等价端点的纯本地工具）
# 其余 55 个细分 OneBot 具名工具可通过 call_napcat_api 透传调用、直接传给 tools/call，或通过 OMNIQQ_TOOL_PROFILE=full 全量暴露
CORE_TOOL_NAMES: tuple[str, ...] = (
    "check_napcat_environment",
    "deploy_or_update_napcat",
    "list_qq_accounts",
    "login_new_qq_by_qrcode",
    "get_login_qrcode_image",
    "switch_qq_account",
    "stop_napcat_service",
    "send_private_msg",
    "send_group_msg",
    "delete_msg",
    "upload_private_file",
    "upload_group_file",
    "get_login_info",
    "get_group_list",
    "get_recent_messages",
    "get_recent_notices_and_requests",
    "clear_recent_messages_buffer",
    "call_napcat_api",
    "list_supported_napcat_actions",
)

DEFAULT_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "description": "执行状态标识，成功为 'ok'（或特定生命周期状态），失败为 'failed' 或 'error'"
        },
        "retcode": {
            "type": "integer",
            "description": "OneBot 11 响应状态码，0 表示成功，非 0 表示协议端或网络错误"
        },
        "data": {
            "description": "接口返回的业务负载数据（对象或数组，具体字段依工具而定）"
        },
        "message": {
            "type": "string",
            "description": "状态说明或错误诊断详情"
        }
    },
    "additionalProperties": True
}

_LOCAL_READONLY_TOOLS = {
    "get_recent_messages",
    "get_recent_notices_and_requests",
    "list_supported_napcat_actions",
    "get_login_qrcode_image",
}

_DESTRUCTIVE_TOOLS = {
    "delete_msg",
    "delete_essence_msg",
    "delete_friend",
    "delete_group_file",
    "delete_group_folder",
    "set_group_kick",
    "set_group_leave",
    "clear_recent_messages_buffer",
    "stop_napcat_service",
    "call_napcat_api",
}

_IDEMPOTENT_MUTATION_TOOLS = {
    "clear_recent_messages_buffer",
    "stop_napcat_service",
    "start_napcat_service",
    "switch_qq_account",
    "mark_msg_as_read",
    "set_essence_msg",
    "set_msg_emoji_like",
    "set_group_ban",
    "set_group_whole_ban",
    "set_group_admin",
    "set_group_card",
    "set_group_name",
    "set_group_special_title",
    "set_group_portrait",
    "set_friend_remark",
    "set_qq_profile",
    "set_qq_avatar",
    "set_self_longnick",
    "set_online_status",
}


class ToolRegistry:
    """MCP 工具注册与分发中心"""

    def __init__(self, default_include_all: Optional[bool] = None):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self.default_include_all: Optional[bool] = default_include_all

    @staticmethod
    def _clean_description(raw_doc: str) -> str:
        """剥离 docstring 中的 :param 行，避免在工具主描述中与 inputSchema 重复"""
        lines = []
        for line in (raw_doc or "").splitlines():
            if line.strip().startswith(":param "):
                continue
            lines.append(line.rstrip())
        return "\n".join(lines).strip()

    @staticmethod
    def _infer_annotations(tool_name: str, explicit: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """根据工具语义生成符合 MCP 规范的 Tool Annotations"""
        is_readonly = (
            tool_name.startswith(("get_", "list_", "check_", "fetch_"))
            or tool_name == "ocr_image"
        )
        is_destructive = tool_name in _DESTRUCTIVE_TOOLS
        is_idempotent = is_readonly or (tool_name in _IDEMPOTENT_MUTATION_TOOLS)
        is_open_world = tool_name not in _LOCAL_READONLY_TOOLS and tool_name != "clear_recent_messages_buffer"

        annotations: Dict[str, Any] = {
            "title": tool_name.replace("_", " ").title(),
            "readOnlyHint": bool(is_readonly),
            "destructiveHint": bool(is_destructive),
            "idempotentHint": bool(is_idempotent),
            "openWorldHint": bool(is_open_world),
        }
        if explicit:
            annotations.update(explicit)
        return annotations

    def register(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        schema_override: Optional[Dict[str, Any]] = None,
        annotations: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        core: Optional[bool] = None,
    ):
        """装饰器：将异步函数注册为 MCP Tool"""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            raw_doc = description or inspect.getdoc(func) or ""
            tool_desc = self._clean_description(raw_doc)
            input_schema = schema_override or self._build_json_schema(func)
            tool_annotations = self._infer_annotations(tool_name, annotations)
            is_core = (tool_name in CORE_TOOL_NAMES or self is not registry) if core is None else bool(core)
            self._tools[tool_name] = {
                "name": tool_name,
                "description": tool_desc,
                "inputSchema": input_schema,
                "outputSchema": output_schema or dict(DEFAULT_OUTPUT_SCHEMA),
                "annotations": tool_annotations,
                "core": is_core,
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
        if origin in (Union, types.UnionType):
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                return ToolRegistry._py_type_to_json_type(non_none[0])
            return {'anyOf': [ToolRegistry._py_type_to_json_type(a) for a in args]}

        if py_type is Any:
            return {}

        if py_type is int:
            return {"type": "integer"}
        if py_type is float:
            return {"type": "number"}
        if py_type is bool:
            return {"type": "boolean"}
        if py_type is str:
            return {"type": "string"}
        if py_type is list or origin is list:
            return {"type": "array", "items": ToolRegistry._py_type_to_json_type(args[0]) if args else {}}
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
            "additionalProperties": False,
        }
        if required:
            schema["required"] = required
        return schema

    @staticmethod
    def validate(value, schema, path='arguments'):
        if 'anyOf' in schema:
            for variant in schema['anyOf']:
                try:
                    ToolRegistry.validate(value, variant, path)
                    return
                except ValueError:
                    pass
            raise ValueError(f'{path} 不符合任何允许的类型')
        typ = schema.get('type')
        valid = {'object':isinstance(value,dict), 'array':isinstance(value,list),
                 'string':isinstance(value,str), 'integer':type(value) is int,
                 'number':type(value) in (int,float), 'boolean':type(value) is bool,
                 'null':value is None}
        if typ and not valid.get(typ,False):
            raise ValueError(f'{path} 必须为 {typ}')
        if typ == 'object':
            for key in schema.get('required',[]):
                if key not in value:
                    raise ValueError(f'{path}.{key} 为必填参数')
            properties = schema.get('properties',{})
            if schema.get('additionalProperties') is False and set(value) - set(properties):
                raise ValueError(f'{path} 含未知参数')
            for key, child in value.items():
                if key in properties:
                    ToolRegistry.validate(child,properties[key],f'{path}.{key}')
        if typ == 'array':
            for index, child in enumerate(value):
                ToolRegistry.validate(child,schema.get('items',{}),f'{path}[{index}]')

    def _should_include_all(self, include_all: Optional[bool] = None) -> bool:
        if include_all is not None:
            return bool(include_all)
        if self.default_include_all is not None:
            return bool(self.default_include_all)
        profile = os.environ.get("OMNIQQ_TOOL_PROFILE", "core").strip().lower()
        full_flag = os.environ.get("OMNIQQ_FULL_TOOLS", "").strip().lower()
        return profile in ("full", "all") or full_flag in ("1", "true", "yes")

    def list_tools(self, include_all: Optional[bool] = None) -> List[Dict[str, Any]]:
        """返回符合 MCP `tools/list` 标准响应格式的工具列表"""
        show_all = self._should_include_all(include_all)
        result: List[Dict[str, Any]] = []
        for info in self._tools.values():
            if not show_all and not info.get("core", True):
                continue
            item: Dict[str, Any] = {
                "name": info["name"],
                "description": info["description"],
                "inputSchema": info["inputSchema"],
            }
            if "outputSchema" in info:
                item["outputSchema"] = info["outputSchema"]
            if "annotations" in info:
                item["annotations"] = info["annotations"]
            result.append(item)
        return result

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    @property
    def tools_map(self) -> Dict[str, Dict[str, Any]]:
        return self._tools


# 全局单例注册表
registry = ToolRegistry()
