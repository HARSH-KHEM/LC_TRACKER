# LeetCode to Notion Sync

This repository contains an automated Python script that syncs your recently solved LeetCode questions to a Notion database. It uses GitHub Actions to run automatically every 20 minutes, ensuring your Notion workspace stays up to date without any manual intervention.

## Features
- Fetches your recently accepted submissions from LeetCode.
- Retrieves metadata (difficulty, topics, problem number) for each problem.
- Checks your Notion database to ensure the problem hasn't already been added (based on the `LC No.` property) to avoid duplicates.
- Creates a new page in Notion with all the relevant details (Name, Topic, Difficulty, Status, Date, Link).

## Setup Instructions

### 1. Local Testing
To test this script on your own machine:
1. Clone this repository.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory and add your secrets (never commit this file):
   ```env
   NOTION_TOKEN=your_notion_internal_integration_token
   NOTION_DB_ID=39d0c38a2214808f97b4d6b39756a0b7
   ```
4. Run the script:
   ```bash
   python leetcode_sync.py
   ```

### 2. GitHub Actions Automation
This repo is configured to run the sync automatically every 20 minutes. For this to work, you need to add your Notion credentials as GitHub Repository Secrets.

1. Go to your GitHub repository on the web.
2. Navigate to **Settings** > **Secrets and variables** > **Actions**.
3. Click **New repository secret**.
4. Create a secret named `NOTION_TOKEN` and paste your Notion internal integration token.
5. Create another secret named `NOTION_DB_ID` and paste your Notion database ID (`39d0c38a2214808f97b4d6b39756a0b7`).
6. You can manually trigger the workflow from the **Actions** tab to test it immediately.

## Customization
- If you need to change the LeetCode username in the future, update the `LEETCODE_USERNAME` variable in `leetcode_sync.py`.
- The database schema assumes properties like `Name`, `LC No.`, `Topic`, `Difficulty`, `Status`, `Date`, and `Link` exist in your Notion database. If you change your schema, update the `create_notion_page` function in the script.
