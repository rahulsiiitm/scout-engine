from __future__ import annotations

from dataclasses import dataclass
from urllib import robotparser


@dataclass(slots=True)
class RobotsPolicy:
    parser: robotparser.RobotFileParser | None
    status_code: int
    failed_closed: bool = False

    @classmethod
    def from_response(cls, *, url: str, status_code: int, text: str) -> "RobotsPolicy":
        if 200 <= status_code < 300:
            parser = robotparser.RobotFileParser(url)
            parser.parse(text.splitlines())
            return cls(parser=parser, status_code=status_code)
        if 400 <= status_code < 500:
            return cls(parser=None, status_code=status_code, failed_closed=False)
        return cls(parser=None, status_code=status_code, failed_closed=True)

    def can_fetch(self, user_agent: str, url: str) -> bool:
        if self.failed_closed:
            return False
        if self.parser is None:
            return True
        return self.parser.can_fetch(user_agent, url)

    def crawl_delay(self, user_agent: str) -> float | None:
        if self.parser is None:
            return None
        value = self.parser.crawl_delay(user_agent)
        return float(value) if value is not None else None

    def site_maps(self) -> list[str]:
        if self.parser is None:
            return []
        return list(self.parser.site_maps() or [])
