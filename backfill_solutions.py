import os
import requests
from dotenv import load_dotenv
from leetcode_sync import fetch_solution_from_github, format_solution_rich_text

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
GH_PAT = os.getenv("GH_PAT")

if not NOTION_TOKEN or not NOTION_DB_ID:
    print("Error: NOTION_TOKEN or NOTION_DB_ID environment variables are not set.")
    exit(1)

if GH_PAT:
    print("Startup Info: GH_PAT is present in the environment.")
else:
    print("Startup Info: GH_PAT is missing from the environment. Unauthenticated limits may apply.")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def backfill_solutions():
    url = f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query"
    payload = {}
    has_more = True
    next_cursor = None
    
    total_processed = 0
    total_updated = 0
    total_skipped = 0

    print("Starting backfill process...")

    while has_more:
        if next_cursor:
            payload["start_cursor"] = next_cursor
            
        response = requests.post(url, headers=NOTION_HEADERS, json=payload)
        if response.status_code != 200:
            print(f"Error querying Notion API: {response.text}")
            break
            
        data = response.json()
        results = data.get("results", [])
        
        for row in results:
            total_processed += 1
            page_id = row["id"]
            props = row.get("properties", {})
            
            # Check if Solution property is empty
            solution_prop = props.get("Solution", {}).get("rich_text", [])
            if solution_prop:
                print(f"Skipping page {page_id} - Solution already populated.")
                total_skipped += 1
                continue

            lc_no_prop = props.get("LC No.", {}).get("number")
            link_prop = props.get("Link", {}).get("url")
            
            if not lc_no_prop or not link_prop:
                print(f"Skipping page {page_id} - Missing LC No. or Link.")
                total_skipped += 1
                continue
                
            lc_no = int(lc_no_prop)
            # Extract title_slug from URL, handle trailing slashes
            title_slug = link_prop.strip('/').split('/')[-1]
            
            print(f"Processing #{lc_no} ({title_slug})...")
            
            readme, code = fetch_solution_from_github(lc_no, title_slug)
            
            if not readme and not code:
                print(f"  -> No solution found in GitHub. Skipping.")
                total_skipped += 1
                continue
                
            solution_rich_text = format_solution_rich_text(readme, code)
            
            if solution_rich_text:
                update_url = f"https://api.notion.com/v1/pages/{page_id}"
                update_payload = {
                    "properties": {
                        "Solution": {
                            "rich_text": solution_rich_text
                        }
                    }
                }
                
                update_res = requests.patch(update_url, headers=NOTION_HEADERS, json=update_payload)
                if update_res.status_code == 200:
                    print(f"  -> Successfully updated Solution property.")
                    total_updated += 1
                else:
                    print(f"  -> Failed to update Notion page: {update_res.text}")
                    total_skipped += 1
                    
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")
        
    print(f"\nBackfill Complete!")
    print(f"Total Pages Processed: {total_processed}")
    print(f"Pages Updated: {total_updated}")
    print(f"Pages Skipped/Failed: {total_skipped}")

if __name__ == "__main__":
    backfill_solutions()
