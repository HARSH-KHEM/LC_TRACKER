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

# Validate configuration
if not NOTION_TOKEN or not NOTION_DB_ID:
    print("Error: NOTION_TOKEN or NOTION_DB_ID environment variables are not set.")
    exit(1)

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
    
    response = requests.post(url, headers=NOTION_HEADERS, json=payload)
    if response.status_code == 200:
        return True
    else:
        print(f"Error creating Notion page for {title}: {response.text}")
        return False

def main():
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

if __name__ == "__main__":
    main()
