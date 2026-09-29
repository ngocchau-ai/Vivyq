"""
skills_socket.py — Socket 3: Agent Skills Library
Scans workspace and system skills, providing 1-click prompt injection.

Author: Antigravity IDE (Sprint D1/D4)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("cautreo.studio.sockets.skills")

DESKTOP_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = DESKTOP_DIR.parent.parent


class SkillsSocket:
    """Agent Skills Directory Scanner & Injector."""

    def __init__(self) -> None:
        self.skills_dir = WORKSPACE_ROOT / ".agents" / "skills"
        self._cached_skills: List[Dict[str, Any]] = []
        self.refresh()

    def refresh(self) -> None:
        skills = []
        # Add primary builtin skills
        default_skills = [
            {
                "id": "hoh-vivy-default",
                "name": "HoH × ViVy Final Flow",
                "description": "Luồng agent mặc định HoH × ViVy Final, tự động nạp Intuition Digest và chấm điểm Cautreo.",
                "keywords": ["hoh vivy", "vivy session", "vivy final", "vivy_final"],
                "badge": "DEFAULT",
            },
            {
                "id": "autoplan",
                "name": "Autoplan Pipeline",
                "description": "Quy trình lập kế hoạch tự động: CEO Review → Design Review → Eng Review → DevEx.",
                "keywords": ["/autoplan", "kế hoạch", "plan"],
                "badge": "STRATEGY",
            },
            {
                "id": "spec",
                "name": "Spec Generator",
                "description": "Chuyển đổi ý tưởng thành bản đặc tả kỹ thuật chi tiết chuẩn hóa.",
                "keywords": ["/spec", "specification", "đặc tả"],
                "badge": "SPEC",
            },
            {
                "id": "review",
                "name": "Code & Architecture Review",
                "description": "Kiểm định 4 trục: Xung đột - Hợp lý - Dư thừa - Hiệu quả.",
                "keywords": ["/review", "audit", "thẩm định"],
                "badge": "AUDIT",
            },
            {
                "id": "cso",
                "name": "Chief Security Officer",
                "description": "Kiểm tra bảo mật OWASP/STRIDE, sandbox và rò rỉ dữ liệu.",
                "keywords": ["/cso", "security", "bảo mật"],
                "badge": "SECURITY",
            },
        ]
        self._cached_skills = default_skills

    def get_state(self) -> Dict[str, Any]:
        return {
            "socket_name": "Skill Library Socket",
            "skills": self._cached_skills,
            "total_skills": len(self._cached_skills),
        }

    def get_skill_content(self, skill_id: str) -> str:
        for s in self._cached_skills:
            if s["id"] == skill_id:
                return f"[KÍCH HOẠT SKILL: {s['name']}]\n{s['description']}\nTrigger keywords: {', '.join(s['keywords'])}"
        return ""
