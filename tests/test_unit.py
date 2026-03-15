import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.crud import _generate_short_code
from app.auth import get_password_hash, verify_password, create_access_token
from app.schemas import LinkCreate, UserCreate


# Генерация короткого кода
def test_generate_short_code_length():
    """Код по умолчанию должен быть длиной 6 символов"""
    code = _generate_short_code()
    assert len(code) == 6


def test_generate_short_code_custom_length():
    """Код с кастомной длиной должен соответствовать ей"""
    code = _generate_short_code(length=10)
    assert len(code) == 10


def test_generate_short_code_chars():
    """Код должен содержать только буквы и цифры"""
    import string
    allowed = set(string.ascii_letters + string.digits)
    code = _generate_short_code()
    assert all(c in allowed for c in code)


def test_generate_short_code_uniqueness():
    """Два вызова подряд крайне редко должны давать одинаковый результат"""
    codes = {_generate_short_code() for _ in range(100)}
    # Из 100 кодов должно быть минимум 90 уникальных
    assert len(codes) >= 90


# Хэширование паролей
def test_password_hash_is_not_plaintext():
    """Хэш не должен совпадать с исходным паролем"""
    password = "mysecretpassword"
    hashed = get_password_hash(password)
    assert hashed != password


def test_password_hash_verify_correct():
    """Правильный пароль должен пройти проверку"""
    password = "mysecretpassword"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True


def test_password_hash_verify_wrong():
    """Неправильный пароль должен не пройти проверку"""
    password = "mysecretpassword"
    hashed = get_password_hash(password)
    assert verify_password("wrongpassword", hashed) is False


def test_password_hash_different_each_time():
    """Два хэша одного пароля должны отличаться"""
    password = "mysecretpassword"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)
    assert hash1 != hash2


# JWT-токены
def test_create_access_token_returns_string():
    """Токен должен быть строкой"""
    token = create_access_token(data={"sub": "test_user"})
    assert isinstance(token, str)


def test_create_access_token_not_empty():
    """Токен не должен быть пустым"""
    token = create_access_token(data={"sub": "test_user"})
    assert len(token) > 0


def test_create_access_token_with_expiry():
    """Токен с явным временем жизни должен создаваться без ошибок"""
    token = create_access_token(
        data={"sub": "test_user"},
        expires_delta=timedelta(minutes=30)
    )
    assert isinstance(token, str)


def test_create_access_token_different_users():
    """Токены разных пользователей должны отличаться"""
    token1 = create_access_token(data={"sub": "user1"})
    token2 = create_access_token(data={"sub": "user2"})
    assert token1 != token2


# Валидация схем Pydantic
def test_link_create_valid():
    """Валидная ссылка должна создаваться без ошибок"""
    link = LinkCreate(original_url="https://example.com")
    assert str(link.original_url) == "https://example.com/"


def test_link_create_invalid_url():
    """Невалидный URL должен вызывать ошибку валидации"""
    with pytest.raises(Exception):
        LinkCreate(original_url="not-a-url")


def test_link_create_with_alias():
    """Ссылка с кастомным алиасом должна создаваться корректно"""
    link = LinkCreate(original_url="https://example.com", custom_alias="mylink")
    assert link.custom_alias == "mylink"


def test_link_create_alias_too_short():
    """Алиас короче 3 символов должен отклоняться"""
    with pytest.raises(Exception):
        LinkCreate(original_url="https://example.com", custom_alias="ab")


def test_link_create_alias_invalid_chars():
    """Алиас со спецсимволами должен отклоняться"""
    with pytest.raises(Exception):
        LinkCreate(original_url="https://example.com", custom_alias="my link!")


def test_link_create_with_expiry():
    """Ссылка с датой истечения должна создаваться корректно"""
    future = datetime.utcnow() + timedelta(days=7)
    link = LinkCreate(original_url="https://example.com", expires_at=future)
    assert link.expires_at is not None


def test_user_create_valid():
    """Валидный пользователь должен создаваться без ошибок"""
    user = UserCreate(username="test_user", email="test@example.com", password="secret123")
    assert user.username == "test_user"


def test_user_create_username_too_short():
    """Имя пользователя короче 3 символов должно отклоняться"""
    with pytest.raises(Exception):
        UserCreate(username="ab", email="test@example.com", password="secret123")


def test_user_create_password_too_short():
    """Пароль короче 6 символов должен отклоняться"""
    with pytest.raises(Exception):
        UserCreate(username="test_user", email="test@example.com", password="123")