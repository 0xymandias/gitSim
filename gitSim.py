#!/usr/bin/env python3
"""
A Python script that simulates contributions over a period by generating backdated commits
to an activity file. It optionally pushes these commits to a remote repository,
creates a new branch, opens a pull request, and simulates a code review.

Usage examples:
    python contribute.py --repository=git@github.com:user/repo.git
    python contribute.py --max_commits=12 --frequency=60 --repository=git@github.com:user/repo.git
    python contribute.py --no_weekends
    python contribute.py --days_before=10 --days_after=15
"""

import argparse
import os
import subprocess
import random
import datetime
import logging
import sys
from github import Github

# Configure logging
logging.basicConfig(
    filename='contribute.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Simulate contributions by generating backdated commits and (optionally) pushing to a remote repo."
    )
    parser.add_argument("--repository", help="Remote repository URL (e.g., git@github.com:user/repo.git)")
    parser.add_argument("--max_commits", type=int, default=12, help="Maximum commits per day")
    parser.add_argument("--frequency", type=int, default=60, help="Percentage of days with commits (0-100)")
    parser.add_argument("--no_weekends", action="store_true", help="Do not commit on weekends")
    parser.add_argument("--days_before", type=int, default=365, help="Days before today to start committing")
    parser.add_argument("--days_after", type=int, default=0, help="Days after today to commit")
    parser.add_argument("--file", default="activity.txt", help="File to update with commits")
    return parser.parse_args()

def init_repo():
    """Initialize a git repository if not already present."""
    if not os.path.exists(".git"):
        subprocess.run(["git", "init"], check=True)
        logging.info("Initialized a new git repository.")
    else:
        logging.info("Git repository already initialized.")

def set_remote(remote_url):
    """Set the remote repository URL if not already set."""
    result = subprocess.run(["git", "remote"], capture_output=True, text=True)
    if "origin" not in result.stdout:
        subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
        logging.info(f"Set remote origin to {remote_url}.")
    else:
        logging.info("Remote origin already set.")

def simulate_commits(args):
    """
    Generate commits over a specified date range by modifying a text file.
    Each commit's date is backdated using GIT_AUTHOR_DATE and GIT_COMMITTER_DATE.
    """
    file_path = args.file
    # Create the file if it doesn't exist
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            f.write("Activity Log\n")
        logging.info(f"Created file {file_path}.")
    else:
        logging.info(f"Using existing file {file_path}.")

    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=args.days_before)
    end_date = today + datetime.timedelta(days=args.days_after)
    
    current_date = start_date
    while current_date <= end_date:
        # Skip weekends if --no_weekends is set
        if args.no_weekends and current_date.weekday() >= 5:
            current_date += datetime.timedelta(days=1)
            continue

        # Decide if commits should be made on this day based on frequency
        if random.randint(1, 100) <= args.frequency:
            num_commits = random.randint(1, args.max_commits)
            for _ in range(num_commits):
                # Pick a random time during the day
                commit_time = datetime.datetime.combine(
                    current_date,
                    datetime.time(random.randint(0,23), random.randint(0,59), random.randint(0,59))
                )
                with open(file_path, "a") as f:
                    f.write(f"Update at {commit_time}\n")
                # Set commit date environment variables
                env = os.environ.copy()
                iso_date = commit_time.isoformat()
                env["GIT_AUTHOR_DATE"] = iso_date
                env["GIT_COMMITTER_DATE"] = iso_date
                subprocess.run(["git", "add", file_path], check=True, env=env)
                commit_msg = f"Automated commit on {commit_time.strftime('%Y-%m-%d %H:%M:%S')}"
                subprocess.run(["git", "commit", "-m", commit_msg], check=True, env=env)
                logging.info(f"Committed: {commit_msg}")
        current_date += datetime.timedelta(days=1)

def get_github_repo_name_from_remote():
    """Extract the GitHub repository full name (owner/repo) from the remote URL."""
    try:
        result = subprocess.run(
            ['git', 'config', '--get', 'remote.origin.url'],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()
        if remote_url.startswith("git@github.com:"):
            remote_url = remote_url[len("git@github.com:"):]
        elif remote_url.startswith("https://github.com/"):
            remote_url = remote_url[len("https://github.com/"):]
        if remote_url.endswith(".git"):
            remote_url = remote_url[:-len(".git")]
        logging.info(f"Determined GitHub repo name: {remote_url}")
        return remote_url
    except Exception as e:
        logging.error(f"Error getting GitHub repo name: {e}")
        return None

def create_new_branch(repo_path, branch_name):
    """Create and switch to a new branch."""
    try:
        subprocess.run(['git', 'checkout', '-b', branch_name], cwd=repo_path, check=True)
        logging.info(f"Created and switched to branch: {branch_name}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error creating branch {branch_name}: {e}")
        sys.exit("Branch creation failed.")

def push_branch(repo_path, branch_name):
    """Push the new branch and set upstream."""
    try:
        subprocess.run(['git', 'push', '--set-upstream', 'origin', branch_name], cwd=repo_path, check=True)
        logging.info(f"Pushed branch {branch_name} to remote.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error pushing branch {branch_name}: {e}")

def create_pull_request(github_token, repo_full_name, branch_name, base_branch="main"):
    """
    Create a pull request from branch 'branch_name' to the base branch using the GitHub API.
    Returns the PR object if successful.
    """
    try:
        g = Github(github_token)
        repo = g.get_repo(repo_full_name)
        title = "Automated Pull Request: Bot Update"
        body = "This pull request was created automatically by the bot."
        pr = repo.create_pull(title=title, body=body, head=branch_name, base=base_branch)
        logging.info(f"Created pull request #{pr.number} in {repo_full_name}")
        return pr
    except Exception as e:
        logging.error(f"Error creating pull request: {e}")
        return None

def simulate_code_review(pr):
    """
    Simulate a code review by posting a review comment.
    Since you cannot approve or request changes on your own PR,
    this function always posts a comment.
    """
    try:
        # Randomly decide if there are simulated issues
        simulated_issues = random.choice([True, False])
        if simulated_issues:
            review_message = (
                "Automated review:\n"
                "- Found minor style issues in the diff.\n"
                "- Consider refactoring for better clarity.\n"
                "Note: This is a self-review comment; please address these issues."
            )
        else:
            review_message = "Automated review: Everything looks good. (Self-review comment)"
        pr.create_review(body=review_message, event="COMMENT")
        logging.info("Simulated code review: posted comment.")
    except Exception as e:
        logging.error(f"Error simulating code review: {e}")

def main():
    args = parse_args()
    
    # Initialize repository if needed
    init_repo()

    # Set remote if provided
    if args.repository:
        set_remote(args.repository)

    # Generate commits over the specified date range
    simulate_commits(args)

    # If a remote repository URL is provided, push commits and create a PR
    if args.repository:
        # Instead of pushing all branches, push only the new branch.
        branch_name = f"auto_pr_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        create_new_branch(os.getcwd(), branch_name)
        push_branch(os.getcwd(), branch_name)

        # Get GitHub repository name from remote URL
        github_repo_name = get_github_repo_name_from_remote()
        if not github_repo_name:
            logging.error("Could not determine GitHub repo name. Exiting.")
            return

        # Get GitHub token from environment variable
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logging.error("GITHUB_TOKEN environment variable not set. Exiting.")
            return

        # Create a pull request from the new branch into the base branch (default: main)
        pr = create_pull_request(github_token, github_repo_name, branch_name)
        if pr:
            simulate_code_review(pr)
        else:
            logging.error("Pull request creation failed.")
    else:
        logging.info("No remote repository provided; skipping push and pull request creation.")

    logging.info("Bot execution finished.")

if __name__ == '__main__':
    main()
