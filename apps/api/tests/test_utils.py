from app.core.errors import NotFoundError, ValidationError


def test_error_hierarchy():
    err = NotFoundError("missing")
    assert err.status_code == 404
    assert err.code == "not_found"

    err2 = ValidationError("bad input")
    assert err2.status_code == 422
    assert err2.code == "validation_error"
