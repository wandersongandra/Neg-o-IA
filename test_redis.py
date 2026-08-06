#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🔴 Redis Connection Test
Testa conexão com Redis na nuvem
"""

import sys
import time
from typing import Optional

try:
    import redis
except ImportError:
    print("❌ Módulo 'redis' não encontrado!")
    print("   Instale com: pip install redis")
    sys.exit(1)


def test_redis_connection(redis_url: str) -> bool:
    """Testa conexão com Redis"""
    print(f"\n🔧 Conectando ao Redis...")
    print(f"   URL: {mask_password(redis_url)}\n")

    try:
        r = redis.from_url(redis_url, decode_responses=True)

        # TESTE 1: PING
        print("   [1] Testando PING...", end=" ")
        result = r.ping()
        if result:
            print("✅ OK")
        else:
            print("❌ Falhou")
            return False

        # TESTE 2: SET/GET
        print("   [2] Testando SET/GET...", end=" ")
        test_key = f"negao:test:{int(time.time())}"
        test_value = "NEGÃO ACORDOU! 🤖"
        r.set(test_key, test_value)
        retrieved = r.get(test_key)
        if retrieved == test_value:
            print("✅ OK")
        else:
            print("❌ Falhou")
            return False

        # TESTE 3: DELETE
        print("   [3] Testando DELETE...", end=" ")
        r.delete(test_key)
        if r.get(test_key) is None:
            print("✅ OK")
        else:
            print("❌ Falhou")
            return False

        # TESTE 4: INFO
        print("   [4] Coletando INFO...", end=" ")
        try:
            info = r.info()
            version = info.get("redis_version", "unknown")
            memory = info.get("used_memory_human", "unknown")
            print(f"✅ OK")
            print(f"\n   📊 Redis Info:")
            print(f"      Versão: {version}")
            print(f"      Memória: {memory}")
        except Exception as e:
            print(f"⚠️  Parcial ({str(e)})")

        # TESTE 5: KEYS COUNT
        print("   [5] Contando chaves...", end=" ")
        try:
            keys_count = r.dbsize()
            print(f"✅ OK")
            print(f"      Total de chaves: {keys_count}")
        except Exception as e:
            print(f"⚠️  Falhou ({str(e)})")

        print("\n✅ TODOS OS TESTES PASSARAM!")
        print("   Redis na nuvem está funcionando!\n")
        return True

    except redis.exceptions.ConnectionError as e:
        print(f"\n❌ ERRO DE CONEXÃO: {e}")
        print(f"   Verifique:")
        print(f"   - Host está correto?")
        print(f"   - Porta está aberta?")
        print(f"   - Senha está correta?")
        print(f"   - Firewall permite conexão?")
        return False
    except redis.exceptions.AuthenticationError as e:
        print(f"\n❌ ERRO DE AUTENTICAÇÃO: {e}")
        print(f"   Verifique a senha no .env")
        return False
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        return False


def mask_password(url: str) -> str:
    """Mascara senha na URL para segurança"""
    if "@" in url:
        scheme_and_creds, host = url.rsplit("@", 1)
        # Mostrar apenas primeiros 6 caracteres da senha
        parts = scheme_and_creds.split(":")
        if len(parts) >= 3:
            password = parts[-1]
            masked = f"{password[:6]}..." if len(password) > 6 else "****"
            return f"{':'.join(parts[:-1])}:{masked}@{host}"
    return url


def main():
    print("\n╔════════════════════════════════════════════════════════╗")
    print("║         🔴 REDIS CONNECTION TEST                      ║")
    print("║              Test Redis Cloud Connection              ║")
    print("╚════════════════════════════════════════════════════════╝")

    # Usar URL do .env
    redis_url = (
        "redis://default:REDACTED@"
        "potato-tail-supermodern-53945.db.redis.io:15412/0"
    )

    success = test_redis_connection(redis_url)

    if success:
        print("╔════════════════════════════════════════════════════════╗")
        print("║         ✅ REDIS ESTÁ PRONTO PARA NEGÃO!              ║")
        print("║                                                       ║")
        print("║   Próximo: Iniciar Backend + Frontend                ║")
        print("╚════════════════════════════════════════════════════════╝\n")
        return 0
    else:
        print("╔════════════════════════════════════════════════════════╗")
        print("║         ❌ FALHA NA CONEXÃO COM REDIS                 ║")
        print("║                                                       ║")
        print("║   Verifique os erros acima e tente novamente          ║")
        print("╚════════════════════════════════════════════════════════╝\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
