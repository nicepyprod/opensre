"""Base tool interface for opensre integrations.

All tools must inherit from BaseTool and implement the required methods
as defined in .cursor/rules/tools.mdc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolParams:
    """Generic container for tool execution parameters."""

    raw: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)

    def require(self, key: str) -> Any:
        """Return a required parameter, raising ValueError if missing."""
        if key not in self.raw:
            raise ValueError(f"Required parameter '{key}' is missing")
        return self.raw[key]


@dataclass
class ToolResult:
    """Encapsulates the outcome of a tool execution."""

    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, output: Any, **metadata: Any) -> "ToolResult":
        return cls(success=True, output=output, metadata=metadata)

    @classmethod
    def fail(cls, error: str, **metadata: Any) -> "ToolResult":
        return cls(success=False, error=error, metadata=metadata)


class BaseTool(ABC):
    """Abstract base class for all opensre tools.

    Subclasses must define:
        - my_tool_name  (str class attribute)
        - MyToolName    (the class name itself)
        - is_available()
        - extract_params()
        - run()
    """

    #: Unique snake_case identifier for this tool (maps to my_tool_name in rules)
    my_tool_name: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "my_tool_name", ""):
            raise TypeError(
                f"Tool '{cls.__name__}' must define a non-empty 'my_tool_name' class attribute"
            )

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when the tool's external dependency is reachable/configured."""

    @abstractmethod
    def extract_params(self, raw_input: Dict[str, Any]) -> ToolParams:
        """Validate and normalise raw input into a ToolParams instance."""

    @abstractmethod
    def run(self, params: ToolParams) -> ToolResult:
        """Execute the tool with the given params and return a ToolResult."""

    def safe_run(self, raw_input: Dict[str, Any]) -> ToolResult:
        """Convenience wrapper: extract params then run, catching unexpected errors."""
        if not self.is_available():
            return ToolResult.fail(f"Tool '{self.my_tool_name}' is not available")
        try:
            params = self.extract_params(raw_input)
            return self.run(params)
        except ValueError as exc:
            logger.warning("Parameter error in tool '%s': %s", self.my_tool_name, exc)
            return ToolResult.fail(str(exc))
        except Exception as exc:  # noqa: BLE001  # catch-all so callers always get a ToolResult
            logger.exception("Unexpected error in tool '%s'", self.my_tool_name)
            return ToolResult.fail(f"Unexpected error: {exc}")
