"""Plans and report packs, loaded from plans.toml and validated at startup."""
from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt, model_validator

PLANS_FILE = Path(__file__).with_name("plans.toml")

ModelTier = Literal["lite", "standard", "premium"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Money(_Strict):
    sar: NonNegativeInt
    usd: NonNegativeInt


class Prices(_Strict):
    monthly: Money
    yearly: Money


class Limits(_Strict):
    reports_per_month: PositiveInt | None = None  # None = unlimited
    chat_per_report: PositiveInt | None = None


class Features(_Strict):
    templates: bool
    regenerate: bool
    watermark: bool
    branded_pdf: bool
    seats: PositiveInt


class Plan(_Strict):
    key: str = ""
    name_ar: str
    name_en: str
    price: Prices
    model_tier: ModelTier
    limits: Limits
    features: Features


class Pack(_Strict):
    key: str = ""
    name_ar: str
    name_en: str
    price: Money
    credits: PositiveInt
    valid_months: PositiveInt
    model_tier: ModelTier
    limits: Limits
    features: Features


class Catalog(_Strict):
    default_plan: str
    plans: dict[str, Plan] = Field(min_length=1)
    packs: dict[str, Pack] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _fill_keys(cls, data: dict) -> dict:
        for group in ("plans", "packs"):
            for key, item in (data.get(group) or {}).items():
                item.setdefault("key", key)
        return data

    @model_validator(mode="after")
    def _default_exists(self) -> Catalog:
        if self.default_plan not in self.plans:
            raise ValueError(f"default_plan {self.default_plan!r} is not in [plans]")
        return self

    @property
    def free(self) -> Plan:
        return self.plans[self.default_plan]


def load_catalog(path: Path = PLANS_FILE) -> Catalog:
    with path.open("rb") as f:
        return Catalog.model_validate(tomllib.load(f))


@lru_cache
def get_catalog() -> Catalog:
    return load_catalog()


def public_catalog() -> dict:
    """What the pricing page needs (no internal fields hidden today, but kept explicit)."""
    c = get_catalog()
    return {
        "default_plan": c.default_plan,
        "plans": [p.model_dump() for p in c.plans.values()],
        "packs": [p.model_dump() for p in c.packs.values()],
    }
