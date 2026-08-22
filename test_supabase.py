#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test Supabase PostgreSQL Connection"""

import os
import sys

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("[ERROR] 'psycopg2' module not found. Install: pip install psycopg2-binary")
    sys.exit(1)


def test_supabase_connection():
    """Test Supabase PostgreSQL connection"""
    
    # Credenciais somente por ambiente; nunca manter host/senha real no source.
    host = os.environ.get("SOPHIE_TEST_DB_HOST")
    port = int(os.environ.get("SOPHIE_TEST_DB_PORT", "5432"))
    database = os.environ.get("SOPHIE_TEST_DB_NAME", "postgres")
    user = os.environ.get("SOPHIE_TEST_DB_USER", "postgres")
    password = os.environ.get("SOPHIE_TEST_DB_PASSWORD")
    if not host or not password:
        print("[BLOCKED] Defina SOPHIE_TEST_DB_HOST e SOPHIE_TEST_DB_PASSWORD para executar.")
        return False
    
    print("\nSupabase PostgreSQL connection test")
    
    print(f"\n[INFO] Connecting to Supabase PostgreSQL...")
    print(f"[INFO] Host: {host}")
    print(f"[INFO] Database: {database}")
    print(f"[INFO] User: {user}\n")
    
    try:
        print("[1] Establishing connection", end=" ")
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        print("[OK]")
        
        print("[2] Getting connection info", end=" ")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print("[OK]")
        print(f"[INFO] PostgreSQL Version: {version.split(',')[0]}")
        
        print("[3] Listing databases", end=" ")
        cursor.execute(
            "SELECT datname FROM pg_database WHERE datistemplate = false;"
        )
        databases = cursor.fetchall()
        print("[OK]")
        print(f"[INFO] Available databases: {len(databases)}")
        for db in databases[:5]:
            print(f"      - {db[0]}")
        
        print("[4] Listing schemas", end=" ")
        cursor.execute(
            "SELECT schema_name FROM information_schema.schemata;"
        )
        schemas = cursor.fetchall()
        print("[OK]")
        print(f"[INFO] Available schemas: {len(schemas)}")
        for schema in schemas:
            print(f"      - {schema[0]}")
        
        print("[5] Checking pgvector extension", end=" ")
        try:
            cursor.execute("SELECT * FROM pg_extension WHERE extname='vector';")
            has_vector = cursor.fetchone()
            if has_vector:
                print("[OK]")
                print("[INFO] pgvector extension is installed.")
            else:
                print("[WARN]")
                print("[WARN] pgvector extension not found (will install on first use)")
        except Exception as e:
            print(f"[WARN] {str(e)}")
        
        print("[6] Testing simple query", end=" ")
        cursor.execute("SELECT 1 as test;")
        result = cursor.fetchone()[0]
        if result == 1:
            print("[OK]")
        else:
            print("[FAIL]")
            return False
        
        cursor.close()
        conn.close()
        
        print("[OK] Supabase PostgreSQL connection verified.")
        print()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"\n[ERROR] Connection Error: {e}")
        print("[INFO] Check:")
        print("[INFO] - Host is correct?")
        print("[INFO] - Port is open?")
        print("[INFO] - Password is correct?")
        print("[INFO] - Network allows connection?")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected Error: {e}")
        return False


def main():
    success = test_supabase_connection()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
