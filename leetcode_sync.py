import os
import requests
import datetime
from dotenv import load_dotenv

# Load local environment variables from .env file if it exists
load_dotenv()

# Configuration
LEETCODE_USERNAME = "harshkh08"
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
GH_PAT = os.getenv("GH_PAT")
NOTION_PARENT_PAGE_ID = "39d0c38a221480af9e09ca9889d57e26"

# Validate configuration
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

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

def get_recent_submissions(username, limit=20):
    """Fetches the most recent accepted submissions for a given user."""
    query = """
    query recentAcSubmissionList($username: String!, $limit: Int!) {
      recentAcSubmissionList(username: $username, limit: $limit) {
        id
        title
        titleSlug
        timestamp
      }
    }
    """
    variables = {"username": username, "limit": limit}
    response = requests.post(LEETCODE_GRAPHQL_URL, json={"query": query, "variables": variables})
    response.raise_for_status()
    data = response.json()
    return data.get("data", {}).get("recentAcSubmissionList", [])

def get_question_data(title_slug):
    """Fetches difficulty, topic tags, and frontend ID for a specific question."""
    query = """
    query questionData($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionFrontendId
        difficulty
        topicTags {
          name
        }
      }
    }
    """
    variables = {"titleSlug": title_slug}
    response = requests.post(LEETCODE_GRAPHQL_URL, json={"query": query, "variables": variables})
    response.raise_for_status()
    data = response.json()
    return data.get("data", {}).get("question")

def check_question_exists(lc_no):
    """Checks if a question with the given LC No. already exists in the Notion database."""
    url = f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query"
    payload = {
        "filter": {
            "property": "LC No.",
            "number": {
                "equals": lc_no
            }
        }
    }
    response = requests.post(url, headers=NOTION_HEADERS, json=payload)
    if response.status_code != 200:
        print(f"Error querying Notion API: {response.text}")
        return False
    results = response.json().get("results", [])
    return len(results) > 0

import base64

def fetch_solution_from_github(lc_no, title_slug):
    """Fetches the solution code and README from the LC_Journey repository."""
    folder_name = f"{lc_no:04d}-{title_slug}"
    url = f"https://api.github.com/repos/HARSH-KHEM/LC_Journey/contents/{folder_name}"
    
    headers = {}
    if GH_PAT:
        headers["Authorization"] = f"Bearer {GH_PAT}"
    else:
        print("Warning: GH_PAT environment variable not set. Using unauthenticated GitHub API calls (rate limits may apply).")

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            print(f"Warning: Solution folder {folder_name} not found in LC_Journey.")
            return None, None
        response.raise_for_status()
        files = response.json()
        
        readme_content = None
        code_content = None
        
        for file in files:
            if file["name"].lower() == "readme.md":
                file_resp = requests.get(file["url"], headers=headers)
                file_resp.raise_for_status()
                readme_content = base64.b64decode(file_resp.json()["content"]).decode('utf-8')
            elif file["name"].startswith(folder_name):
                file_resp = requests.get(file["url"], headers=headers)
                file_resp.raise_for_status()
                code_content = base64.b64decode(file_resp.json()["content"]).decode('utf-8')

        return readme_content, code_content

    except Exception as e:
        print(f"Error fetching solution from GitHub for {folder_name}: {e}")
        return None, None

def chunk_rich_text(text, is_code=False, max_length=1900):
    """Splits a string into chunks to fit within Notion's 2000 character limit per rich text object."""
    if not text:
        return []
    
    chunks = []
    for i in range(0, len(text), max_length):
        chunk = text[i:i + max_length]
        rich_text_obj = {
            "type": "text",
            "text": {"content": chunk}
        }
        if is_code:
            rich_text_obj["annotations"] = {"code": True}
        chunks.append(rich_text_obj)
    return chunks

def format_solution_rich_text(readme_content, code_content):
    """Combines approach and code into a single rich text array."""
    if not readme_content and not code_content:
        return []
        
    rich_text = []
    
    if readme_content:
        rich_text.extend(chunk_rich_text("Approach:\n"))
        rich_text.extend(chunk_rich_text(readme_content))
        if code_content:
            rich_text.extend(chunk_rich_text("\n\n---\n\n"))
            
    if code_content:
        rich_text.extend(chunk_rich_text("Code:\n"))
        rich_text.extend(chunk_rich_text(code_content, is_code=True))
        
    return rich_text

def create_notion_page(question_data, submission_data):
    """Creates a new page in the Notion database with the question details."""
    url = "https://api.notion.com/v1/pages"
    
    try:
        lc_no = int(question_data["questionFrontendId"])
    except ValueError:
        print(f"Warning: Could not parse question ID {question_data['questionFrontendId']} as integer. Skipping.")
        return False

    title = submission_data["title"]
    title_slug = submission_data["titleSlug"]
    timestamp = int(submission_data["timestamp"])
    
    # Format date as ISO string (YYYY-MM-DD)
    date_str = datetime.datetime.fromtimestamp(timestamp).isoformat()
    
    difficulty = question_data["difficulty"]
    topics = [{"name": tag["name"]} for tag in question_data.get("topicTags", [])]

    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": title}}]
            },
            "LC No.": {
                "number": lc_no
            },
            "Topic": {
                "multi_select": topics
            },
            "Difficulty": {
                "select": {"name": difficulty}
            },
            "Status": {
                "select": {"name": "Done"}
            },
            "Date": {
                "date": {"start": date_str}
            },
            "Link": {
                "url": f"https://leetcode.com/problems/{title_slug}/"
            }
        }
    }
    
    # Fetch solution
    readme, code = fetch_solution_from_github(lc_no, title_slug)
    solution_rich_text = format_solution_rich_text(readme, code)
    if solution_rich_text:
        payload["properties"]["Solution"] = {"rich_text": solution_rich_text}
    
    response = requests.post(url, headers=NOTION_HEADERS, json=payload)
    if response.status_code == 200:
        return True
    else:
        print(f"Error creating Notion page for {title}: {response.text}")
        return False

def update_database_schema():
    """Auto-colors the Difficulty and Status select options in the Notion database."""
    url = f"https://api.notion.com/v1/databases/{NOTION_DB_ID}"
    # 1. Update colors
    color_payload = {
        "properties": {
            "Difficulty": {
                "select": {
                    "options": [
                        {"name": "Easy", "color": "green"},
                        {"name": "Medium", "color": "yellow"},
                        {"name": "Hard", "color": "red"}
                    ]
                }
            },
            "Status": {
                "select": {
                    "options": [
                        {"name": "Done", "color": "green"},
                        {"name": "Revise", "color": "orange"}
                    ]
                }
            }
        }
    }
    color_response = requests.patch(url, headers=NOTION_HEADERS, json=color_payload)
    if color_response.status_code == 200:
        print("Database schema colors updated successfully.")
    else:
        print(f"Failed to update database schema colors: {color_response.text}")

    # 2. Add Solution property
    schema_payload = {
        "properties": {
            "Solution": {
                "rich_text": {}
            }
        }
    }
    schema_response = requests.patch(url, headers=NOTION_HEADERS, json=schema_payload)
    if schema_response.status_code == 200:
        print("Database schema (Solution property) updated successfully.")
    else:
        print(f"Failed to update database schema (Solution property): {schema_response.text}")

def get_stats():
    """Fetches all 'Done' questions from the database and calculates stats."""
    url = f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query"
    payload = {
        "filter": {
            "property": "Status",
            "select": {
                "equals": "Done"
            }
        }
    }
    has_more = True
    next_cursor = None
    
    total = 0
    difficulty_counts = {"Easy": 0, "Medium": 0, "Hard": 0}
    dates = set()
    
    while has_more:
        if next_cursor:
            payload["start_cursor"] = next_cursor
            
        response = requests.post(url, headers=NOTION_HEADERS, json=payload)
        if response.status_code != 200:
            print(f"Error querying Notion API for stats: {response.text}")
            break
            
        data = response.json()
        results = data.get("results", [])
        
        for row in results:
            total += 1
            props = row.get("properties", {})
            diff = props.get("Difficulty", {}).get("select", {})
            if diff:
                diff_name = diff.get("name")
                if diff_name in difficulty_counts:
                    difficulty_counts[diff_name] += 1
                    
            date_obj = props.get("Date", {}).get("date", {})
            if date_obj:
                date_str = date_obj.get("start")
                if date_str:
                    # extract just the YYYY-MM-DD part
                    date_only = date_str.split("T")[0]
                    dates.add(date_only)
                    
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")
        
    # Calculate streak
    sorted_dates = sorted(list(dates), reverse=True)
    streak = 0
    if sorted_dates:
        today = datetime.datetime.now().date()
        current_date_in_streak = datetime.datetime.strptime(sorted_dates[0], "%Y-%m-%d").date()
        
        # Streak continues if the most recent submission is today or yesterday
        if (today - current_date_in_streak).days <= 1:
            streak = 1
            for i in range(1, len(sorted_dates)):
                prev_date = datetime.datetime.strptime(sorted_dates[i], "%Y-%m-%d").date()
                if (current_date_in_streak - prev_date).days == 1:
                    streak += 1
                    current_date_in_streak = prev_date
                else:
                    break
                    
    return total, difficulty_counts, streak

def update_stats_blocks(total, difficulty_counts, streak):
    """Updates or appends the stats callout blocks in the parent Notion page."""
    if not NOTION_PARENT_PAGE_ID:
        return
        
    url = f"https://api.notion.com/v1/blocks/{NOTION_PARENT_PAGE_ID}/children"
    
    # 1. Fetch existing blocks to see if our stats block exists
    response = requests.get(url, headers=NOTION_HEADERS)
    if response.status_code != 200:
        print(f"Error fetching page blocks: {response.text}")
        return
        
    blocks = response.json().get("results", [])
    
    stats_heading_id = None
    stats_callout_ids = []
    
    in_stats_section = False
    for block in blocks:
        block_type = block["type"]
        if block_type == "heading_2":
            text_arr = block["heading_2"].get("rich_text", [])
            if text_arr and "📊 Stats" in text_arr[0].get("plain_text", ""):
                stats_heading_id = block["id"]
                in_stats_section = True
                continue
        
        if in_stats_section:
            if block_type == "callout":
                stats_callout_ids.append(block["id"])
                if len(stats_callout_ids) == 3:
                    break
            elif block_type != "heading_2":
                # If we hit something else before getting 3 callouts, stop
                break
                
    # Create the block objects
    total_text = f"Total Questions Solved: {total}"
    diff_text = f"Difficulty Breakdown: Easy {difficulty_counts['Easy']} | Medium {difficulty_counts['Medium']} | Hard {difficulty_counts['Hard']}"
    streak_text = f"Current Streak: {streak} days"
    
    def make_callout(text, emoji):
        return {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": text}}],
                "icon": {"type": "emoji", "emoji": emoji},
                "color": "default"
            }
        }
        
    if stats_heading_id and len(stats_callout_ids) == 3:
        # Update existing blocks
        callout_data = [
            (stats_callout_ids[0], total_text, "📈"),
            (stats_callout_ids[1], diff_text, "🟢"), 
            (stats_callout_ids[2], streak_text, "🔥")
        ]
        
        for block_id, text, emoji in callout_data:
            patch_url = f"https://api.notion.com/v1/blocks/{block_id}"
            payload = make_callout(text, emoji)
            res = requests.patch(patch_url, headers=NOTION_HEADERS, json=payload)
            if res.status_code != 200:
                print(f"Failed to update block {block_id}: {res.text}")
            
        print("Updated existing stats blocks.")
        
    else:
        # Append new blocks
        print("Stats blocks not found, appending them...")
        payload = {
            "children": [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "📊 Stats"}}]
                    }
                },
                make_callout(total_text, "📈"),
                make_callout(diff_text, "🟢"),
                make_callout(streak_text, "🔥")
            ]
        }
        append_response = requests.patch(url, headers=NOTION_HEADERS, json=payload)
        if append_response.status_code == 200:
            print("Appended new stats blocks.")
        else:
            print(f"Failed to append stats blocks: {append_response.text}")

def main():
    print("Updating database schema colors...")
    update_database_schema()

    print(f"Fetching recent submissions for {LEETCODE_USERNAME}...")
    try:
        submissions = get_recent_submissions(LEETCODE_USERNAME)
    except Exception as e:
        print(f"Failed to fetch submissions: {e}")
        return

    if not submissions:
        print("No recent accepted submissions found.")
        return

    print(f"Found {len(submissions)} recent submissions. Processing...")
    
    for sub in reversed(submissions): # Process oldest first
        title = sub["title"]
        title_slug = sub["titleSlug"]
        
        try:
            q_data = get_question_data(title_slug)
        except Exception as e:
            print(f"Failed to fetch question data for {title}: {e}")
            continue

        if not q_data:
            print(f"Question data not found for {title}. Skipping.")
            continue
            
        try:
            lc_no = int(q_data["questionFrontendId"])
        except ValueError:
            print(f"Skipping '{title}': Non-numeric question ID ({q_data['questionFrontendId']})")
            continue

        if check_question_exists(lc_no):
            print(f"Skipped: {title} (#{lc_no}) - Already in Notion.")
        else:
            print(f"Syncing: {title} (#{lc_no})...", end=" ")
            if create_notion_page(q_data, sub):
                print("Success.")
            else:
                print("Failed.")

    print("\nCalculating stats and updating dashboard...")
    total, difficulty_counts, streak = get_stats()
    update_stats_blocks(total, difficulty_counts, streak)
    print("Dashboard updated.")

if __name__ == "__main__":
    main()
