#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test Supabase PostgreSQL Connection with SSL"""

import sys

try:
    import psycopg2
except ImportError:
    print("[ERROR] 'psycopg2' module not found. Install: pip install psycopg2-binary")
    sys.exit(1)


def test_supabase_connection():
    """Test Supabase PostgreSQL connection with SSL"""
    
    # Supabase connection details
    host = "db.rvxbbbssgexqnheteobf.supabase.co"
    port = 5432
    database = "postgres"
    user = "postgres"
    password = "#-Cdp4Wbu@rb7D+"
    
    print("\n" + "="*60)
    print("    SUPABASE PostgreSQL CONNECTION TEST (with SSL)")
    print("="*60)
    
    print(f"\n[INFO] Connecting to Supabase PostgreSQL...")
    print(f"[INFO] Host: {host}")
    print(f"[INFO] Database: {database}\n")
    
    try:
        # TEST 1: Connection with SSL
        print("[TEST 1] Connecting with SSL=require...", end=" ")
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            sslmode='require'
        )
        print("[OK]")
        
        # TEST 2: Get version
        print("[TEST 2] Getting PostgreSQL version...", end=" ")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print("[OK]")
        print(f"[INFO] Version: {version.split(',')[0]}")
        
        # TEST 3: Simple query
        print("[TEST 3] Testing simple query...", end=" ")
        cursor.execute("SELECT 1 as test;")
        result = cursor.fetchone()[0]
        print("[OK]")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("   SUCCESS! Supabase is ready!")
        print("="*60 + "\n")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print(f"\n[INFO] Trying alternative: sslmode='prefer'...\n")
        
        try:
            print("[TEST 1] Connecting with SSL=prefer...", end=" ")
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                sslmode='prefer'
            )
            print("[OK]")
            
            print("[TEST 2] Getting version...", end=" ")
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            cursor.fetchone()
            print("[OK]")
            
            cursor.close()
            conn.close()
            
            print("\n[SUCCESS] Connection works with prefer mode!")
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
