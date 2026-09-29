"""
tools_socket.py — Socket 2: Cautreo Native Tool Registry
Exposes WebSearch, SysTools, FileSystem, and Dynamic Cautreo Plugins.

Author: Antigravity IDE (Sprint D1/D4)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger("cautreo.studio.sockets.tools")


class ToolsSocket:
    """Cautreo Plugin & Tool Registry Socket."""

    def __init__(self) -> None:
        self.plugins = [
            {
                "id": "websearch",
                "name": "WebSearch Plugin (C Native)",
                "description": "Tìm kiếm web thời gian thực, trích xuất dữ liệu markdown sạch.",
                "enabled": True,
                "sandbox_level": "READ_ONLY",
                "calls_count": 28,
            },
            {
                "id": "systools",
                "name": "SysTools Plugin (C Native)",
                "description": "Thực thi lệnh hệ thống, giám sát tài nguyên CPU/RAM/Disk.",
                "enabled": True,
                "sandbox_level": "DRY_RUN_GUARD",
                "calls_count": 142,
            },
            {
                "id": "filesystem",
                "name": "FileSystem I/O Plugin",
                "description": "Đọc ghi file an toàn, kiểm soát immutable banner & changelog.",
                "enabled": True,
                "sandbox_level": "RESTRICTED_WORKSPACE",
                "calls_count": 89,
            },
            {
                "id": "context_memory",
                "name": "Cautreo 0ms Memory Plugin",
                "description": "Truy xuất trực tiếp C-ABI context memory và score graph.",
                "enabled": True,
                "sandbox_level": "ZERO_LATENCY_RAM",
                "calls_count": 618,
            },
        ]

    def get_state(self) -> Dict[str, Any]:
        return {
            "socket_name": "Tool Registry Socket",
            "plugins": self.plugins,
            "total_tools": len(self.plugins),
            "active_tools": sum(1 for p in self.plugins if p["enabled"]),
        }

    def toggle_tool(self, tool_id: str) -> bool:
        for p in self.plugins:
            if p["id"] == tool_id:
                p["enabled"] = not p["enabled"]
                logger.info("Tool %s toggled to %s", tool_id, p["enabled"])
                return p["enabled"]
        return False
