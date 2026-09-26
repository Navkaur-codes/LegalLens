from app.middleware import MULTIPART_OVERHEAD_BYTES, upload_size_error


def test_upload_within_limit_is_allowed(settings):
    assert upload_size_error(str(settings.max_file_bytes), settings) is None


def test_upload_over_limit_is_rejected(settings):
    error = upload_size_error(str(settings.max_file_bytes + MULTIPART_OVERHEAD_BYTES + 1), settings)
    assert error is not None and error.status_code == 413


def test_missing_content_length_is_rejected(settings):
    error = upload_size_error(None, settings)
    assert error is not None and error.status_code == 411


def test_malformed_content_length_is_rejected(settings):
    error = upload_size_error("12abc", settings)
    assert error is not None and error.status_code == 400
