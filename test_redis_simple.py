#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test Redis Connection"""

import os
import sys
import time

try:
    import redis
except ImportError:
    print("[ERROR] 'redis' module not found. Install: pip install redis")
    sys.exit(1)


def mask_password(url: str) -> str:
    """Mask password in URL"""
    if "@" in url:
        scheme_and_creds, host = url.rsplit("@", 1)
        parts = scheme_and_creds.split(":")
        if len(parts) >= 3:
            password = parts[-1]
            masked = f"{password[:6]}..." if len(password) > 6 else "****"
            return f"{':'.join(parts[:-1])}:{masked}@{host}"
    return url


def test_redis_connection(redis_url: str) -> bool:
    """Test Redis connection"""
    print("\n[INFO] Connecting to Redis...")
    print(f"[INFO] URL: {mask_password(redis_url)}\n")

    try:
        r = redis.from_url(redis_url, decode_responses=True)

        print("[1] PING", end=" ")
        result = r.ping()
        if result:
            print("[OK]")
        else:
            print("[FAIL]")
            return False

        print("[2] SET/GET", end=" ")
        test_key = f"negao:test:{int(time.time())}"
        test_value = "redis-probe"
        r.set(test_key, test_value)
        retrieved = r.get(test_key)
        if retrieved == test_value:
            print("[OK]")
        else:
            print("[FAIL]")
            return False

        print("[3] DELETE", end=" ")
        r.delete(test_key)
        if r.get(test_key) is None:
            print("[OK]")
        else:
            print("[FAIL]")
            return False

        print("[4] INFO", end=" ")
        try:
            info = r.info()
            version = info.get("redis_version", "unknown")
            memory = info.get("used_memory_human", "unknown")
            print("[OK]")
            print(f"\n[INFO] Redis Version: {version}")
            print(f"[INFO] Memory Used: {memory}")
        except Exception as e:
            print(f"[WARN] {str(e)}")

        print("[5] DBSIZE", end=" ")
        try:
            keys_count = r.dbsize()
            print("[OK]")
            print(f"[INFO] Total Keys: {keys_count}")
        except Exception as e:
            print(f"[WARN] {str(e)}")

        print("\nRedis connectivity checks passed.")
        print("[INFO] Redis is available.\n")
        return True

    except redis.exceptions.ConnectionError as e:
        print(f"\n[ERROR] Connection Error: {e}")
        print("[INFO] Check:")
        print("[INFO] - Host is correct?")
        print("[INFO] - Port is open?")
        print("[INFO] - Password is correct?")
        print("[INFO] - Firewall allows connection?")
        return False
    except redis.exceptions.AuthenticationError as e:
        print(f"\n[ERROR] Authentication Error: {e}")
        print("[INFO] Check password in .env")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected Error: {e}")
        return False


def main():
    print("\nRedis connection test")

    redis_url = os.getenv("SOPHIE_REDIS_URL") or os.getenv("NEGAO_REDIS_URL")
    if not redis_url:
        print("[BLOCKED] Set SOPHIE_REDIS_URL or NEGAO_REDIS_URL in an ignored environment file.")
        return 2

    success = test_redis_connection(redis_url)

    if success:
        print("[OK] Redis connection verified.")
        print()
        return 0
    else:
        print("[ERROR] Redis connection failed.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
