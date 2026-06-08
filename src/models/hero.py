from dataclasses import dataclass
from exceptions import ValidationError


@dataclass
class Hero:
    name: str
    role: str
    level: int
    xp: int
    xp_required: int
    is_max_level: bool
    capture_run_id: int
    updated_at: str
    id: int = None
    ch1_progress: float = 0.0
    ch2_progress: float = 0.0
    ch3_progress: float = 0.0

    def validate(self):
        if not self.name or not self.name.strip():
            raise ValidationError("Hero name must not be empty")
        if self.level < 1:
            raise ValidationError(f"Hero level must be >= 1, got {self.level}")
        if self.xp < 0:
            raise ValidationError(f"Hero xp must be >= 0, got {self.xp}")
        if self.xp_required < 0:
            raise ValidationError(f"Hero xp_required must be >= 0, got {self.xp_required}")
        if self.is_max_level and self.xp_required != 0:
            raise ValidationError("xp_required must be 0 when is_max_level is True")
        if not self.is_max_level and self.xp >= self.xp_required:
            raise ValidationError(
                f"xp ({self.xp}) must be < xp_required ({self.xp_required}) when not max level"
            )

    @property
    def progress_pct(self) -> float:
        if self.is_max_level or self.xp_required == 0:
            return 0.0
        return self.xp / self.xp_required * 100
