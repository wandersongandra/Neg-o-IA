#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test Supabase PostgreSQL Connection with SSL"""

import os
import sys

try:
    import psycopg2
except ImportError:
    print("[ERROR] 'psycopg2' module not found. Install: pip install psycopg2-binary")
    sys.exit(1)


def test_supabase_connection():
    """Test Supabase PostgreSQL connection with SSL"""
    
    # Credenciais somente por ambiente; nunca manter host/senha real no source.
    host = os.environ.get("SOPHIE_TEST_DB_HOST")
    port = int(os.environ.get("SOPHIE_TEST_DB_PORT", "5432"))
    database = os.environ.get("SOPHIE_TEST_DB_NAME", "postgres")
    user = os.environ.get("SOPHIE_TEST_DB_USER", "postgres")
    password = os.environ.get("SOPHIE_TEST_DB_PASSWORD")
    if not host or not password:
        print("[BLOCKED] Defina SOPHIE_TEST_DB_HOST e SOPHIE_TEST_DB_PASSWORD para executar.")
        return False
    
    print("\nSupabase PostgreSQL connection test (SSL)")
    
    print(f"\n[INFO] Connecting to Supabase PostgreSQL...")
    print(f"[INFO] Host: {host}")
    print(f"[INFO] Database: {database}\n")
    
    try:
        print("[1] Connecting with SSL=require", end=" ")
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            sslmode='require'
        )
        print("[OK]")
        
        print("[2] Getting PostgreSQL version", end=" ")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print("[OK]")
        print(f"[INFO] Version: {version.split(',')[0]}")
        
        print("[3] Testing simple query", end=" ")
        cursor.execute("SELECT 1 as test;")
        result = cursor.fetchone()[0]
        print("[OK]")
        
        cursor.close()
        conn.close()
        
        print("[OK] Supabase connection verified.")
        print()
        return True
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print(f"\n[INFO] Trying alternative: sslmode='prefer'...\n")
        
        try:
            print("[1] Connecting with SSL=prefer", end=" ")
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                sslmode='prefer'
            )
            print("[OK]")
            
            print("[2] Getting version", end=" ")
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            cursor.fetchone()
            print("[OK]")
            
            cursor.close()
            conn.close()
            
            print("\n[OK] Connection works with prefer mode.")
            print("[NOTE] Update .env to use: sslmode=prefer\n")
            return True
            
        except Exception as e2:
            print(f"\n[ERROR] Both attempts failed: {e2}\n")
            return False


def main():
    success = test_supabase_connection()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
