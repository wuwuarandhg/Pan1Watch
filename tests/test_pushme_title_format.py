import sys
import types

sys.modules.setdefault("apprise", types.SimpleNamespace(Apprise=object))

from src.core.notifier import build_pushme_title


def test_build_pushme_title_appends_group_tag() -> None:
    title = build_pushme_title({"group_name": "PanWatch", "group_avatar": "PW"}, "测试消息")
    assert title == "[#PanWatch!PW]测试消息"


def test_build_pushme_title_keeps_theme_prefix_first() -> None:
    title = build_pushme_title(
        {"group_name": "PanWatch", "group_avatar": "📈"},
        "[s]任务执行成功",
    )
    assert title == "[s][#PanWatch!📈]任务执行成功"


def test_build_pushme_title_without_group_uses_original_title() -> None:
    assert build_pushme_title({}, "[w]服务器告警") == "[w]服务器告警"
