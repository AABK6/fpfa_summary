from scripts.smoke_test_web import is_ignored_console_issue


def test_ignores_only_known_headless_webgl_noise():
    assert is_ignored_console_issue(
        "Automatic fallback to software WebGL has been deprecated."
    )
    assert is_ignored_console_issue(
        "GL Driver Message (OpenGL, Performance): GPU stall due to ReadPixels"
    )


def test_keeps_application_and_network_failures_blocking():
    assert not is_ignored_console_issue("Uncaught TypeError: Failed to fetch")
    assert not is_ignored_console_issue("EXCEPTION CAUGHT BY WIDGETS LIBRARY")
