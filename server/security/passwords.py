"""PBKDF2 密码生成与验证。"""

import hashlib
import hmac
import secrets


class PasswordHasher:
    """PBKDF2 密码生成与验证。"""

    PASSWORD_ALGORITHM = "pbkdf2_sha256"
    PASSWORD_ITERATIONS = 310000
    PASSWORD_SALT_BYTES = 16
    PASSWORD_DERIVED_KEY_BYTES = 32

    @classmethod
    def hash_password(cls, password):
        """
        使用 PBKDF2-HMAC-SHA256 生成密码 Hash。

        返回格式：

        pbkdf2_sha256$310000$<salt>$<hash>
        """
        if not isinstance(password, str):
            raise ValueError("password must be a string")
        if not password:
            raise ValueError("password cannot be empty")
        salt = secrets.token_bytes(cls.PASSWORD_SALT_BYTES)
        derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            cls.PASSWORD_ITERATIONS,
            dklen=cls.PASSWORD_DERIVED_KEY_BYTES,
        )
        return "{}${}${}${}".format(
            cls.PASSWORD_ALGORITHM,
            cls.PASSWORD_ITERATIONS,
            salt.hex(),
            derived_key.hex(),
        )

    @classmethod
    def verify_password(cls, password, password_hash):
        """
        验证密码是否与 Hash 匹配。
        """
        if not isinstance(password, str):
            return False
        if not isinstance(password_hash, str):
            return False
        parts = password_hash.split("$")
        if len(parts) != 4:
            return False
        algorithm = parts[0]
        if algorithm != cls.PASSWORD_ALGORITHM:
            return False
        try:
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            expected_hash = bytes.fromhex(parts[3])
        except (ValueError, TypeError):
            return False
        if iterations <= 0:
            return False
        if len(expected_hash) != (cls.PASSWORD_DERIVED_KEY_BYTES):
            return False
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
            dklen=len(expected_hash),
        )
        return hmac.compare_digest(actual_hash, expected_hash)
