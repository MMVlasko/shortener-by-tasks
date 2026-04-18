import hashlib


def generate_short_alias(original, length=6):
    hash_object = hashlib.md5(original.encode())
    hash_hex = hash_object.hexdigest()

    num = int(hash_hex[:8], 16)

    chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    result = []

    while num > 0 and len(result) < length:
        result.append(chars[num % 62])
        num //= 62

    return ''.join(result)
