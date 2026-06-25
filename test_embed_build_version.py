from scripts.embed_build_version import build_ci_label, update_build_label


def test_build_ci_label_uses_short_sha() -> None:
    assert build_ci_label("v1.2.3", "0123456789abcdef") == "v1.2.3 (0123456)"


def test_update_build_label_replaces_only_build_label() -> None:
    content = "\n".join(
        [
            'BUILD_LABEL = "dev"',
            "",
            "OTHER_VALUE = 1",
            "",
        ]
    )

    assert update_build_label(content, "v1.2.3 (0123456)") == "\n".join(
        [
            "BUILD_LABEL = 'v1.2.3 (0123456)'",
            "",
            "OTHER_VALUE = 1",
            "",
        ]
    )
