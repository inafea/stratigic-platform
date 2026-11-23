import pytest
from pydantic import ValidationError

from backend.billing.plans import get_catalog, load_catalog


def test_shipped_catalog_is_valid():
    c = get_catalog()
    assert list(c.plans) == ["free", "entrepreneur", "pro", "business"]
    assert c.free.key == "free" and c.free.price.monthly.sar == 0
    assert set(c.packs) == {"pack_1", "pack_5"}


def test_prices_match_the_plan():
    p = get_catalog().plans
    assert (p["entrepreneur"].price.monthly.sar, p["entrepreneur"].price.monthly.usd) == (49, 13)
    assert (p["pro"].price.monthly.sar, p["pro"].price.yearly.sar) == (149, 1430)
    assert p["business"].price.monthly.usd == 129


def test_yearly_is_cheaper_than_twelve_months():
    for plan in get_catalog().plans.values():
        m, y = plan.price.monthly, plan.price.yearly
        assert y.sar <= m.sar * 12 and y.usd <= m.usd * 12


def test_limits_and_features():
    p = get_catalog().plans
    assert p["free"].limits.reports_per_month == 2 and p["free"].limits.chat_per_report == 5
    assert p["free"].features.templates is False and p["free"].features.watermark is True
    assert p["pro"].limits.chat_per_report is None  # unlimited
    assert p["pro"].model_tier == "premium" and p["free"].model_tier == "lite"
    assert p["business"].features.seats == 5


def write(tmp_path, text):
    f = tmp_path / "plans.toml"
    f.write_text(text, encoding="utf-8")
    return f


PLAN = """
[plans.free]
name_ar = "x"
name_en = "x"
price = { monthly = { sar = 0, usd = 0 }, yearly = { sar = 0, usd = 0 } }
model_tier = "lite"
limits = { reports_per_month = 2 }
features = { templates = false, regenerate = false, watermark = true, branded_pdf = false, seats = 1 }
"""


def test_minimal_valid_file(tmp_path):
    c = load_catalog(write(tmp_path, 'default_plan = "free"\n' + PLAN))
    assert c.free.limits.chat_per_report is None


@pytest.mark.parametrize("bad", [
    'default_plan = "gold"\n' + PLAN,                                  # default plan missing
    'default_plan = "free"\n' + PLAN.replace('"lite"', '"ultra"'),     # unknown model tier
    'default_plan = "free"\n' + PLAN.replace("sar = 0, usd = 0 }, yearly", "sar = -5, usd = 0 }, yearly"),
    'default_plan = "free"\n' + PLAN.replace("reports_per_month = 2", "reports_per_month = 0"),
    'default_plan = "free"\n' + PLAN.replace("seats = 1", "seats = 1, typo = true"),  # unknown key
])
def test_invalid_files_rejected(tmp_path, bad):
    with pytest.raises(ValidationError):
        load_catalog(write(tmp_path, bad))


def test_plans_endpoint_is_public(anon_client):
    body = anon_client.get("/api/plans").json()
    assert [p["key"] for p in body["plans"]] == ["free", "entrepreneur", "pro", "business"]
    assert body["plans"][2]["price"]["monthly"] == {"sar": 149, "usd": 39}
    assert body["packs"][0]["credits"] == 1
