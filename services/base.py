from dataclasses import dataclass
from typing import Callable, Dict, Any, List

@dataclass
class ServicePlugin:
    id: str
    label: str
    module: str
    item_keys: List[str]
    render_fields: Callable[[], Dict[str, Any]]
    compute: Callable[[Any, Dict[str, Any]], Dict[str, Any]]
