#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Probe Redis connectivity."""

import os
import sys
import time
try:
    import redis
except ImportError:
    print("[ERROR] Módulo 'redis' não encontrado.")
    print("[INFO] Instale com: pip install redis")
    sys.exit(1)


def test_redis_connection(redis_url: str) -> bool:
    """Testa a conexão com Redis."""
    print("\n[INFO] Conectando ao Redis")
    print(f"[INFO] URL: {mask_password(redis_url)}\n")

    try:
        r = redis.from_url(redis_url, decode_responses=True)

        print("[1] PING", end=" ")
        result = r.ping()
        if result:
            print("[OK]")
        else:
            print("[ERROR]")
            return False

        print("[2] SET/GET", end=" ")
        test_key = f"negao:test:{int(time.time())}"
        test_value = "redis-probe"
        r.set(test_key, test_value)
        retrieved = r.get(test_key)
        if retrieved == test_value:
            print("[OK]")
        else:
            print("[ERROR]")
            return False

        print("[3] DELETE", end=" ")
        r.delete(test_key)
        if r.get(test_key) is None:
            print("[OK]")
        else:
            print("[ERROR]")
            return False

        print("[4] INFO", end=" ")
        try:
            info = r.info()
            version = info.get("redis_version", "unknown")
            memory = info.get("used_memory_human", "unknown")
            print("[OK]")
            print(f"[INFO] Redis version: {version}")
            print(f"[INFO] Used memory: {memory}")
        except Exception as e:
            print(f"[WARN] Informações indisponíveis ({e})")

        print("[5] Database size", end=" ")
        try:
            keys_count = r.dbsize()
            print("[OK]")
            print(f"[INFO] Keys: {keys_count}")
        except Exception as e:
            print(f"[WARN] Database size indisponível ({e})")

        print("\nRedis connectivity checks passed.")
        print("[INFO] Redis is available.\n")
        return True

    except redis.exceptions.ConnectionError as e:
        print(f"\n[ERROR] Falha de conexão: {e}")
        print("[INFO] Verifique host, porta, credenciais e firewall.")
        return False
    except redis.exceptions.AuthenticationError as e:
        print(f"\n[ERROR] Falha de autenticação: {e}")
        print("[INFO] Verifique as credenciais do Redis.")
        return False
    except Exception as e:
        print(f"\n[ERROR] Erro inesperado: {e}")
        return False


def mask_password(url: str) -> str:
    """Mascara credenciais na URL antes de exibi-la."""
    if "@" in url:
        scheme_and_creds, host = url.rsplit("@", 1)
        parts = scheme_and_creds.split(":")
        if len(parts) >= 3:
            password = parts[-1]
            masked = f"{password[:6]}..." if len(password) > 6 else "****"
            return f"{':'.join(parts[:-1])}:{masked}@{host}"
    return url


def main():
    print("\nRedis connection test")

    redis_url = os.getenv("SOPHIE_REDIS_URL") or os.getenv("NEGAO_REDIS_URL")
    if not redis_url:
        print("[BLOCKED] Defina SOPHIE_REDIS_URL ou NEGAO_REDIS_URL em ambiente ignorado.")
        return 2

    success = test_redis_connection(redis_url)

    if success:
        print("[OK] Redis connection verified.")
        print("[INFO] Start the backend and frontend services.\n")
        return 0
    else:
        print("[ERROR] Redis connection failed.")
        print("[INFO] Review the errors above and try again.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
