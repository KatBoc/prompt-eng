#!/usr/bin/env python3
"""
Script to import GTFS data into SQLite database for the public transport API.
"""

import sqlite3
import csv
import os
from pathlib import Path

def create_table_from_csv(cursor, csv_file_path, table_name):
    """Create a table based on CSV headers."""
    with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
        csv_reader = csv.DictReader(file)
        columns = csv_reader.fieldnames
        columns = [col.strip().replace('\ufeff', '') for col in columns]

        # Create table with TEXT columns for all fields
        columns_def = ', '.join([f'"{col}" TEXT' for col in columns])
        create_table_sql = f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                {columns_def}
            )
        '''
        cursor.execute(create_table_sql)

def import_csv_to_table(cursor, csv_file_path, table_name):
    """Import CSV data into the specified table."""
    if not os.path.exists(csv_file_path):
        print(f"Warning: {csv_file_path} not found, skipping...")
        return

    print(f"Importing {csv_file_path} into {table_name}...")

    with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
        csv_reader = csv.DictReader(file)

        # Get column names from CSV header
        columns = csv_reader.fieldnames
        columns = [col.strip().replace('\ufeff', '') for col in columns]

        # Create placeholders for SQL INSERT
        placeholders = ', '.join(['?' for _ in columns])
        column_names = ', '.join([f'"{col}"' for col in columns])

        insert_sql = f"INSERT OR REPLACE INTO {table_name} ({column_names}) VALUES ({placeholders})"

        # Import data
        rows_imported = 0
        for row in csv_reader:
            values = [row.get(original_col, '') for original_col in csv_reader.fieldnames]
            cursor.execute(insert_sql, values)
            rows_imported += 1

            if rows_imported % 10000 == 0:
                print(f"  Imported {rows_imported} rows...")

        print(f"  Completed: {rows_imported} rows imported into {table_name}")

def main():
    """Main function to set up the database."""
    db_path = "trips.sqlite"
    gtfs_dir = "OtwartyWroclaw_rozklad_jazdy_GTFS"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Get all CSV files from the GTFS directory
        csv_files = [f for f in os.listdir(gtfs_dir) if f.endswith('.txt')]

        for filename in csv_files:
            table_name = os.path.splitext(filename)[0]  # Remove .txt extension
            file_path = os.path.join(gtfs_dir, filename)

            print(f"\nProcessing {filename}...")
            # Create table based on CSV structure
            create_table_from_csv(cursor, file_path, table_name)
            # Import data
            import_csv_to_table(cursor, file_path, table_name)
            conn.commit()

        print("\nDatabase setup completed successfully!")

        # Show statistics for all tables
        print("\nDatabase statistics:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for (table_name,) in tables:
            if table_name != 'sqlite_sequence':
                cursor.execute(f"SELECT COUNT(*) FROM \"{table_name}\"")
                count = cursor.fetchone()[0]
                print(f"  {table_name}: {count} rows")

    except Exception as e:
        print(f"Error setting up database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
