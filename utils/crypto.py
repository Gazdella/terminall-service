"""
RSA + AES hybrid encryption/decryption for the Keepz API (Python mirror).

Keepz requires:
- AES-256-CBC with PKCS7 padding for payload encryption
- RSA OAEP SHA-256 for encrypting the AES key+IV
- Base64 encoding for transport
"""

import base64
import json
import os

from cryptography.hazmat.primitives import hashes, padding, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class KeepzCrypto:
    """Handles RSA + AES hybrid encryption/decryption for the Keepz API."""

    def __init__(self, public_key_b64: str, private_key_b64: str):
        """
        Args:
            public_key_b64: Keepz's RSA public key (Base64-encoded DER, SPKI format)
            private_key_b64: Integrator's RSA private key (Base64-encoded DER, PKCS8 format)
        """
        self._public_key = serialization.load_der_public_key(
            base64.b64decode(public_key_b64)
        )
        self._private_key = serialization.load_der_private_key(
            base64.b64decode(private_key_b64),
            password=None,
        )

    def encrypt(self, data: dict) -> dict:
        """Encrypts a JSON payload for the Keepz API.

        Returns:
            dict with 'encryptedData', 'encryptedKeys', and 'aes': True
        """
        # 1. Generate random AES-256 key (32 bytes) and IV (16 bytes)
        aes_key = os.urandom(32)
        iv = os.urandom(16)

        # 2. Encrypt payload with AES-256-CBC + PKCS7 padding
        json_payload = json.dumps(data).encode("utf-8")
        encrypted_data = self._aes_encrypt(json_payload, aes_key, iv)

        # 3. Prepare encryptedKeys: Base64(key).Base64(iv) → RSA OAEP encrypt
        encoded_key = base64.b64encode(aes_key).decode("ascii")
        encoded_iv = base64.b64encode(iv).decode("ascii")
        concat = f"{encoded_key}.{encoded_iv}"
        encrypted_keys = self._rsa_encrypt(concat.encode("utf-8"))

        return {
            "encryptedData": base64.b64encode(encrypted_data).decode("ascii"),
            "encryptedKeys": base64.b64encode(encrypted_keys).decode("ascii"),
            "aes": True,
        }

    def decrypt(self, encrypted_data_b64: str, encrypted_keys_b64: str) -> dict:
        """Decrypts a Keepz API response.

        Args:
            encrypted_data_b64: Base64-encoded AES-encrypted payload
            encrypted_keys_b64: Base64-encoded RSA-encrypted AES key+IV

        Returns:
            Decrypted JSON as a dict.
        """
        # 1. RSA decrypt the encryptedKeys → "Base64(key).Base64(iv)"
        decrypted_concat = self._rsa_decrypt(
            base64.b64decode(encrypted_keys_b64)
        ).decode("utf-8")
        parts = decrypted_concat.split(".")
        aes_key = base64.b64decode(parts[0])
        iv = base64.b64decode(parts[1])

        # 2. AES decrypt the encryptedData
        decrypted_data = self._aes_decrypt(base64.b64decode(encrypted_data_b64), aes_key, iv)
        return json.loads(decrypted_data.decode("utf-8"))

    def _aes_encrypt(self, data: bytes, key: bytes, iv: bytes) -> bytes:
        """AES-256-CBC encrypt with PKCS7 padding."""
        padder = padding.PKCS7(128).padder()
        padded = padder.update(data) + padder.finalize()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        return encryptor.update(padded) + encryptor.finalize()

    def _aes_decrypt(self, data: bytes, key: bytes, iv: bytes) -> bytes:
        """AES-256-CBC decrypt with PKCS7 unpadding."""
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(data) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded) + unpadder.finalize()

    def _rsa_encrypt(self, data: bytes) -> bytes:
        """RSA OAEP SHA-256 encrypt."""
        return self._public_key.encrypt(
            data,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    def _rsa_decrypt(self, data: bytes) -> bytes:
        """RSA OAEP SHA-256 decrypt."""
        return self._private_key.decrypt(
            data,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
