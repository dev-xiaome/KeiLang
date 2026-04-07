#!/usr/bin/env python
"""KeiLang 哈希函数库"""

import hashlib
from object import *
from lib.kei2py import *
from stdlib import kei

def md5(data: KeiString) -> KeiString:
    """MD5 哈希"""
    kei.check(data, KeiString, name='md5')
    return KeiString(hashlib.md5(data.value.encode('utf-8')).hexdigest())

def sha1(data: KeiString) -> KeiString:
    """SHA-1 哈希"""
    kei.check(data, KeiString, name='sha1')
    return KeiString(hashlib.sha1(data.value.encode('utf-8')).hexdigest())

def sha256(data: KeiString) -> KeiString:
    """SHA-256 哈希"""
    kei.check(data, KeiString, name='sha256')
    return KeiString(hashlib.sha256(data.value.encode('utf-8')).hexdigest())

def sha384(data: KeiString) -> KeiString:
    """SHA-384 哈希"""
    kei.check(data, KeiString, name='sha384')
    return KeiString(hashlib.sha384(data.value.encode('utf-8')).hexdigest())

def sha512(data: KeiString) -> KeiString:
    """SHA-512 哈希"""
    kei.check(data, KeiString, name='sha512')
    return KeiString(hashlib.sha512(data.value.encode('utf-8')).hexdigest())

def sha3_256(data: KeiString) -> KeiString:
    """SHA3-256 哈希"""
    kei.check(data, KeiString, name='sha3_256')
    return KeiString(hashlib.sha3_256(data.value.encode('utf-8')).hexdigest())

def sha3_512(data: KeiString) -> KeiString:
    """SHA3-512 哈希"""
    kei.check(data, KeiString, name='sha3_512')
    return KeiString(hashlib.sha3_512(data.value.encode('utf-8')).hexdigest())

def blake2b(data: KeiString) -> KeiString:
    """BLAKE2b 哈希"""
    kei.check(data, KeiString, name='blake2b')
    return KeiString(hashlib.blake2b(data.value.encode('utf-8')).hexdigest())

def blake2s(data: KeiString) -> KeiString:
    """BLAKE2s 哈希"""
    kei.check(data, KeiString, name='blake2s')
    return KeiString(hashlib.blake2s(data.value.encode('utf-8')).hexdigest())

def hmac_md5(key: KeiString, data: KeiString) -> KeiString:
    """HMAC-MD5"""
    kei.check(key, KeiString, name='hmac_md5')
    kei.check(data, KeiString, name='hmac_md5')
    import hmac
    return KeiString(hmac.new(key.value.encode('utf-8'),
                               data.value.encode('utf-8'),
                               hashlib.md5).hexdigest())

def hmac_sha256(key: KeiString, data: KeiString) -> KeiString:
    """HMAC-SHA256"""
    kei.check(key, KeiString, name='hmac_sha256')
    kei.check(data, KeiString, name='hmac_sha256')
    import hmac
    return KeiString(hmac.new(key.value.encode('utf-8'),
                               data.value.encode('utf-8'),
                               hashlib.sha256).hexdigest())

def hash_file(filename: KeiString, algorithm: KeiString = KeiString('sha256')) -> KeiString:
    """计算文件的哈希值"""
    kei.check(filename, KeiString, name='hash_file')
    kei.check(algorithm, KeiString, name='hash_file')

    algo = algorithm.value.lower()

    # 选择算法
    if algo == 'md5':
        hasher = hashlib.md5()
    elif algo == 'sha1':
        hasher = hashlib.sha1()
    elif algo == 'sha256':
        hasher = hashlib.sha256()
    elif algo == 'sha384':
        hasher = hashlib.sha384()
    elif algo == 'sha512':
        hasher = hashlib.sha512()
    elif algo == 'sha3_256':
        hasher = hashlib.sha3_256()
    elif algo == 'sha3_512':
        hasher = hashlib.sha3_512()
    else:
        raise KeiError("ValueError", f"不支持的哈希算法: {algo}")

    # 分块读取文件
    with open(filename.value, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)

    return KeiString(hasher.hexdigest())

# 导出
__all__ = [
    'md5', 'sha1', 'sha256', 'sha384', 'sha512',
    'sha3_256', 'sha3_512', 'blake2b', 'blake2s',
    'hmac_md5', 'hmac_sha256', 'hash_file'
]