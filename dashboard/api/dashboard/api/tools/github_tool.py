import os
from dotenv import load_dotenv
from git import Repo

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

FRONTEND_REPO = os.path.expanduser(os.getenv("GITHUB_FRONTEND_REPO") or "")
BACKEND_REPO = os.path.expanduser(os.getenv("GITHUB_BACKEND_REPO") or "")


def get_current_branch(repo_path):
    """Return the name of the currently checked-out branch."""
    repo = Repo(repo_path)
    branch = repo.active_branch.name
    print(f"Current branch in '{repo_path}': {branch}")
    return branch


def list_branches(repo_path):
    """List all local branches in the repo."""
    repo = Repo(repo_path)
    branches = [head.name for head in repo.heads]
    print(f"Branches in '{repo_path}':")
    for b in branches:
        prefix = "* " if b == repo.active_branch.name else "  "
        print(f"  {prefix}{b}")
    return branches


def switch_branch(repo_path, branch_name):
    """Switch to the given branch."""
    repo = Repo(repo_path)
    repo.git.checkout(branch_name)
    print(f"Switched to branch '{branch_name}' in '{repo_path}'")


def pull_latest(repo_path):
    """Pull the latest changes from the tracking remote branch."""
    repo = Repo(repo_path)
    origin = repo.remotes.origin
    result = origin.pull()
    for info in result:
        print(f"Pulled '{repo_path}': {info.ref} — {info.note or 'up to date'}")
    return result
