from gangtise_core.endpoints import (
    destructive_for_tool,
    load_compensations,
    load_endpoints,
    retry_policy_for_url,
)


def test_destructive_roster_is_exact():
    eps = load_endpoints()
    destructive = sorted(k for k, e in eps.items() if e.destructive)
    assert destructive == ["vault.drive.delete-file", "vault.drive.delete-folder", "vault.stock-pool.delete"]


def test_stockpool_search_does_not_require_yes():
    assert destructive_for_tool("stockpool") is None
    dest = destructive_for_tool("vault.stock-pool.delete")
    assert dest is not None
    assert "--yes" in dest.warning


def test_destructive_is_resolved_per_mode():
    for tool, mode in [("stockpool", "delete"), ("private_cloud", "delete_file"), ("private_cloud", "delete_folder")]:
        dest = destructive_for_tool(tool, mode)
        assert dest is not None and "--yes" in dest.warning, (tool, mode)
    for tool, mode in [
        ("stockpool", "search"),
        ("stockpool", "delete_stock"),
        ("private_cloud", "search"),
        ("private_cloud", "move_file"),
        ("private_cloud", None),
    ]:
        assert destructive_for_tool(tool, mode) is None, (tool, mode)


def test_non_idempotent_writes_are_no_replay():
    eps = load_endpoints()
    for key in ["vault.stock-pool.create", "vault.drive.upload", "vault.drive.create-folder", "vault.drive.copy"]:
        assert eps[key].retry == "no-replay", key


def test_delete_flavoured_endpoints_are_classified():
    eps = load_endpoints()
    for key, spec in eps.items():
        path = spec.path.lower()
        if any(tok in path for tok in ("delete", "remove")):
            assert spec.destructive or spec.item_failures, key


def test_every_download_is_no_replay():
    eps = load_endpoints()
    for key, spec in eps.items():
        if spec.kind == "download":
            assert spec.retry == "no-replay", key
            assert retry_policy_for_url(f"https://openapi.gangtise.com{spec.path}") == "no-replay"


def test_billed_endpoints_are_no_replay():
    eps = load_endpoints()
    for key in ["insight.summary.download", "kb.resource.download", "indicator.edb-get-data"]:
        assert eps[key].retry == "no-replay", key


def test_ede_endpoints_use_no_999999_like_the_ts_cli():
    eps = load_endpoints()
    for key in ["indicator.search", "indicator.time-series", "indicator.cross-section", "screener.run"]:
        assert eps[key].retry == "no-999999", key
        assert retry_policy_for_url(f"https://openapi.gangtise.com{eps[key].path}") == "no-999999"


def test_compensations_have_tickets():
    items = load_compensations()
    assert items
    for item in items:
        assert item.id.startswith("C-")
        assert item.server_ticket
        assert item.reason
