#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test Supabase PostgreSQL Connection"""

import sys
import os

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("[ERROR] 'psycopg2' module not found. Install: pip install psycopg2-binary")
    sys.exit(1)


def test_supabase_connection():
    """Test Supabase PostgreSQL connection"""
    
    # Supabase connection details
    host = "db.rvxbbbssgexqnheteobf.supabase.co"
    port = 5432
    database = "postgres"
    user = "postgres"
    password = "#-Cdp4Wbu@rb7D+"
    
    print("\n" + "="*60)
    print("         SUPABASE PostgreSQL CONNECTION TEST")
    print("="*60)
    
    print(f"\n[INFO] Connecting to Supabase PostgreSQL...")
    print(f"[INFO] Host: {host}")
    print(f"[INFO] Database: {database}")
    print(f"[INFO] User: {user}\n")
    
    try:
        # TEST 1: Basic Connection
        print("[TEST 1] Establishing connection...", end=" ")
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        print("[OK]")
        
        # TEST 2: Get connection info
        print("[TEST 2] Getting connection info...", end=" ")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print("[OK]")
        print(f"[INFO] PostgreSQL Version: {version.split(',')[0]}")
        
        # TEST 3: List databases
        print("[TEST 3] Listing databases...", end=" ")
        cursor.execute(
            "SELECT datname FROM pg_database WHERE datistemplate = false;"
        )
        databases = cursor.fetchall()
        print("[OK]")
        print(f"[INFO] Available databases: {len(databases)}")
        for db in databases[:5]:
            print(f"      - {db[0]}")
        
        # TEST 4: List schemas
        print("[TEST 4] Listing schemas...", end=" ")
        cursor.execute(
            "SELECT schema_name FROM information_schema.schemata;"
        )
        schemas = cursor.fetchall()
        print("[OK]")
        print(f"[INFO] Available schemas: {len(schemas)}")
        for schema in schemas:
            print(f"      - {schema[0]}")
        
        # TEST 5: Test pgvector extension
        print("[TEST 5] Checking pgvector extension...", end=" ")
        try:
            cursor.execute("SELECT * FROM pg_extension WHERE extname='vector';")
            has_vector = cursor.fetchone()
            if has_vector:
                print("[OK]")
                print("[INFO] pgvector extension is installed!")
            else:
                print("[WARN]")
                print("[WARN] pgvector extension not found (will install on first use)")
        except Exception as e:
            print(f"[WARN] {str(e)}")
        
        # TEST 6: Test a simple query
        print("[TEST 6] Testing simple query...", end=" ")
        cursor.execute("SELECT 1 as test;")
        result = cursor.fetchone()[0]
        if result == 1:
            print("[OK]")
        else:
            print("[FAIL]")
            return False
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("   SUCCESS! Supabase PostgreSQL is ready!")
        print("="*60 + "\n")
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
