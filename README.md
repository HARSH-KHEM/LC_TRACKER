# LeetCode to Notion Sync

This repository contains an automated Python script that syncs your recently solved LeetCode questions to a Notion database. It uses GitHub Actions to run automatically every 20 minutes, ensuring your Notion workspace stays up to date without any manual intervention.

## Features
- **Auto-Sync:** Fetches your recently accepted submissions from LeetCode. Retrieves metadata (difficulty, topics, problem number) for each problem and creates a page in Notion if it hasn't been added yet (checks `LC No.` property).
- **Auto-Colors:** Updates your Notion database automatically to color-code difficulty (Easy=green, Medium=yellow, Hard=red) and status (Done=green, Revise=orange).
- **Stats Dashboard:** Maintains and automatically updates a stats summary block on the parent page ("DSA COMMAND CENTRE") with callouts showing total questions solved, a difficulty breakdown, and your current streak.
- **Solution Sync:** Automatically fetches your approach notes (from `README.md`) and solution code from your `LC_Journey` repository, combining them into a single `Solution` property in the Notion database.

## Notion Custom Views
Please note that the Notion API cannot currently create custom database views (like Board, Gallery, or Timeline). To create these, you will need to add them manually using the "+ Add view" button in the Notion UI, which takes under a minute.

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
   GH_PAT=your_github_personal_access_token
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
6. Create another secret named `GH_PAT` and paste your GitHub Personal Access Token (this prevents API rate limiting when fetching solutions).
7. You can manually trigger the workflow from the **Actions** tab to test it immediately.

### 3. Backfilling Solutions for Existing Pages
If you already have a populated Notion database and want to pull in solutions from your `LC_Journey` repository for all past questions:
1. Ensure your `.env` file is set up with `NOTION_TOKEN`, `NOTION_DB_ID`, and `GH_PAT`.
2. Run the one-time backfill script:
   ```bash
   python backfill_solutions.py
   ```
   This will iterate through your database and populate the new `Solution` property for any page missing it. It handles Notion API pagination automatically.

## Customization
- If you need to change the LeetCode username in the future, update the `LEETCODE_USERNAME` variable in `leetcode_sync.py`.
- The database schema assumes properties like `Name`, `LC No.`, `Topic`, `Difficulty`, `Status`, `Date`, and `Link` exist in your Notion database. If you change your schema, update the `create_notion_page` function in the script.
