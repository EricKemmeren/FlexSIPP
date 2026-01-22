from enum import Enum
from typing import TypeVar

NodeType  = TypeVar('NodeType', bound="Node")
EdgeType  = TypeVar('EdgeType', bound="Edge")
GraphType = TypeVar('GraphType', bound="Graph")

AgentT = TypeVar('AgentT', bound="Agent")

class Direction(Enum):
    SAME = 1
    OPPOSE = 2
    BOTH = 3