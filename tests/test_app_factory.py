import warnings


def test_create_app_does_not_emit_on_event_deprecation_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        from app.main import create_app

        _ = create_app()

    messages = [str(item.message) for item in caught]
    assert not any("on_event is deprecated" in message for message in messages)
