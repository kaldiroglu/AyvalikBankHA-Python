import pytest

from ayvalikbank_ha.domain.service import PasswordValidationService


@pytest.fixture
def service() -> PasswordValidationService:
    return PasswordValidationService()


def test_accepts_valid(service):
    service.validate("Goodpass1!")


def test_rejects_short(service):
    with pytest.raises(ValueError, match="length"):
        service.validate("Sho1!")


def test_rejects_no_digit(service):
    with pytest.raises(ValueError, match="digit"):
        service.validate("Password!")


def test_rejects_no_upper(service):
    with pytest.raises(ValueError, match="uppercase"):
        service.validate("password1!")


def test_rejects_no_special(service):
    with pytest.raises(ValueError, match="special"):
        service.validate("Password1")
