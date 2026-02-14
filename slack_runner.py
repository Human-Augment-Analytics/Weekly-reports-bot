# slack_runner.py

import os
import re
import tempfile
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from smart_bot import build_summary, parse_report  # smart_bot.py helpers

# =========================
# Slack Setup
# =========================

slack_token = os.environ["SLACK_BOT_TOKEN"]
channel_id = os.environ["SLACK_CHANNEL_ID"]

client = WebClient(token=slack_token)

# =========================
# Download Reports
# =========================

def download_reports(temp_dir):
    """
    Download all PDF files from the Slack channel to temp_dir.
    Returns a list of local file paths.
    """
    downloaded_files = []

    try:
        response = client.files_list(channel=channel_id)
        for f in response.get("files", []):
            if f.get("filetype") != "pdf":
                continue

            file_name = f["name"]
            file_url = f["url_private_download"]
            local_path = os.path.join(temp_dir, file_name)

            # Download file using requests
            r = requests.get(file_url, headers={"Authorization": f"Bearer {slack_token}"})
            if r.status_code != 200:
                print(f"Failed to download {file_name}: {r.status_code}")
                continue

            with open(local_path, "wb") as pdf_file:
                pdf_file.write(r.content)

            downloaded_files.append(local_path)

    except SlackApiError as e:
        print(f"Error fetching files from Slack: {e.response['error']}")

    return downloaded_files

# =========================
# Determine latest week
# =========================

def get_latest_week_files(files):
    """Filter the downloaded files to only include the latest week."""
    latest_week = -1
    latest_files = []

    for file_path in files:
        file_name = os.path.basename(file_path)
        match = re.search(r"Week(\d+)", file_name)
        if not match:
            continue

        week_num = int(match.group(1))
        if week_num > latest_week:
            latest_week = week_num
            latest_files = [file_path]
        elif week_num == latest_week:
            latest_files.append(file_path)

    return latest_week, latest_files

# =========================
# Run Bot
# =========================

def run_bot():
    with tempfile.TemporaryDirectory() as tmp_dir:
        print(f"Downloading reports to temp dir: {tmp_dir}")
        downloaded_files = download_reports(tmp_dir)

        if not downloaded_files:
            summary = "No reports found for the latest week."
        else:
            latest_week, latest_files = get_latest_week_files(downloaded_files)
            if not latest_files:
                summary = "No reports found for the latest week."
            else:
                summary = build_summary(latest_week, latest_files)

        # Post to Slack
        try:
            response = client.chat_postMessage(
                channel=channel_id,
                text=summary
            )
            print(f"Message posted successfully: {response['ts']}")
        except SlackApiError as e:
            print(f"Error posting message: {e.response['error']}")

if __name__ == "__main__":
    run_bot()
