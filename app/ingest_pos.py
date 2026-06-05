import os
import sys
# Add the parent directory (Code/) to the Python path so 'app' can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy import create_engine
from app.models import Base
import argparse

# The DB URL for synchronous operations using psycopg2 (default postgresql:// driver)
DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL", 
    "postgresql://store_admin:store_secure_pass@127.0.0.1:5433/store_intelligence"
)

def main():
    parser = argparse.ArgumentParser(description="Ingest POS transactions into PostgreSQL")
    parser.add_argument("--csv", required=True, help="Path to POS CSV file")
    args = parser.parse_args()

    print(f"Loading POS data from {args.csv}...")
    try:
        df = pd.read_csv(args.csv)
    except FileNotFoundError:
        print(f"Error: Could not find file {args.csv}")
        return

    # Clean data
    # Create combined transaction_timestamp from order_date and order_time
    # Data format: order_date = DD-MM-YYYY (e.g., 10-04-2026), order_time = HH:MM:SS
    print("Cleaning and transforming data...")
    df['transaction_timestamp'] = pd.to_datetime(
        df['order_date'] + ' ' + df['order_time'], 
        format="%d-%m-%Y %H:%M:%S", 
        errors='coerce'
    )
    
    # Fill NA for total_amount if any
    if 'total_amount' in df.columns:
        df['total_amount'] = pd.to_numeric(df['total_amount'], errors='coerce').fillna(0.0)

    # Convert UUIDs/strings as necessary
    df['order_id'] = df['order_id'].astype(str)
    
    # Ensure all expected columns are present
    expected_cols = [
        "order_id", "order_date", "order_time", "store_id", 
        "product_id", "brand_name", "total_amount"
    ]
    for col in expected_cols:
        if col not in df.columns:
            print(f"Warning: Expected column '{col}' missing from CSV. Using defaults.")
            df[col] = None

    print("Connecting to database and ensuring schema exists...")
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)

    print("Inserting data into PostgreSQL 'pos_transactions' table...")
    
    # Filter columns to match the DB schema
    columns_to_insert = expected_cols + ["transaction_timestamp"]
    df_insert = df[columns_to_insert]
    
    from sqlalchemy.exc import IntegrityError
    try:
        df_insert.to_sql("pos_transactions", engine, if_exists="append", index=False)
        print(f"Successfully ingested {len(df_insert)} records into 'pos_transactions'.")
    except IntegrityError as e:
        if "duplicate key" in str(e) or "UniqueViolation" in str(e):
            print("Data has already been ingested. Skipping duplicate insertion to prevent primary key conflicts.")
        else:
            print(f"Database Integrity Error: {e}")
    except Exception as e:
        print(f"Failed to insert data to SQL: {e}")

if __name__ == "__main__":
    main()
