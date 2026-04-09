import warnings


def test_create_app_does_not_emit_on_event_deprecation_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        from app.main import create_app

        _ = create_app()

    messages = [str(item.message) for item in caught]
    assert not any("on_event is deprecated" in message for message in messages)


def test_create_app_uses_packetbench_title_and_cookie_name():
    from app.main import create_app

    app = create_app()

    session_middleware = next(m for m in app.user_middleware if m.cls.__name__ == "SessionMiddleware")
    assert app.title == "PacketBench"
    assert app.version == "v0.1.0"
    assert session_middleware.kwargs["session_cookie"] == "packetbench_session"
