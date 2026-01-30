import database_manager as db
import data_engine as de
import os

def run_verification():
    print("--- 1. Initialize DB ---")
    try:
        db.init_db()
        print("PASS: Database initialized.")
    except Exception as e:
        print(f"FAIL: Database init failed: {e}")
        return

    print("\n--- 2. Add Portfolio Item ---")
    success, msg = db.add_portfolio_item("BBCA", 8500, notes="Test Entry")
    if success:
        print("PASS: Item added.")
    else:
        print(f"FAIL: Add item failed: {msg}")
        return

    print("\n--- 3. Verify Persistence ---")
    df = db.get_portfolio()
    if not df.empty and "BBCA" in df['ticker'].values:
        print("PASS: Item found in DB.")
    else:
        print("FAIL: Item not found.")
        return

    print("\n--- 4. Fetch Price (BBCA) ---")
    price = de.get_current_price("BBCA")
    if price and price > 0:
        print(f"PASS: Price fetched: {price}")
    else:
        print(f"FAIL: Price fetch failed or returned 0.")

    print("\n--- 5. Cleanup ---")
    db.delete_portfolio_item("BBCA")
    print("PASS: Cleanup done.")
    
    print("\n✅ PRE-FLIGHT CHECK COMPLETE")

if __name__ == "__main__":
    run_verification()
