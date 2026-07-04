"""Git operations wrapper using subprocess calls to the system git binary."""
import logging
import os
import subprocess
from typing import List, Optional
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger("ha_github_sync.git")


class GitError(Exception):
    """Raised when a git command fails."""


class GitOps:
    """Wraps git operations for the local working-copy repository."""

    def __init__(
        self,
        repo_dir: str,
        repo_url: str,
        token: str,
        branch: str,
        author_name: str,
        author_email: str,
    ):
        self.repo_dir = repo_dir
        self.branch = branch
        self.author_name = author_name
        self.author_email = author_email

        # Build authenticated HTTPS URL (token embedded)
        if not repo_url.startswith("http"):
            repo_url = f"https://{repo_url}"
        parsed = urlparse(repo_url)
        self._authenticated_url = urlunparse(
            parsed._replace(netloc=f"x-access-token:{token}@{parsed.netloc}")
        )
        # Safe display URL (no token)
        self._display_url = urlunparse(parsed._replace(netloc=parsed.netloc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _env(self, extra: Optional[dict] = None) -> dict:
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = self.author_name
        env["GIT_AUTHOR_EMAIL"] = self.author_email
        env["GIT_COMMITTER_NAME"] = self.author_name
        env["GIT_COMMITTER_EMAIL"] = self.author_email
        # Disable interactive prompts
        env["GIT_TERMINAL_PROMPT"] = "0"
        if extra:
            env.update(extra)
        return env

    def _run(
        self,
        args: List[str],
        cwd: Optional[str] = None,
        check: bool = True,
        env_extra: Optional[dict] = None,
    ) -> subprocess.CompletedProcess:
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd or self.repo_dir,
                env=self._env(env_extra),
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            raise GitError("git executable not found – ensure git is installed in the container")

        if check and result.returncode != 0:
            stderr = result.stderr.strip()
            # Scrub token from error messages before logging
            if self._authenticated_url:
                stderr = stderr.replace(self._authenticated_url, self._display_url)
            raise GitError(f"git {args[0]} failed (exit {result.returncode}): {stderr}")

        return result

    # ------------------------------------------------------------------
    # Repository initialisation
    # ------------------------------------------------------------------

    def init_or_clone(self) -> bool:
        """
        Ensure the local working-copy repository exists.

        If the repo dir already contains a .git directory the remote URL is
        updated to reflect the current token.  Otherwise the remote is cloned;
        if the clone fails (empty repo, branch not found, etc.) a fresh local
        repo is initialised instead.

        Returns True when the repo was newly created/cloned.
        """
        git_dir = os.path.join(self.repo_dir, ".git")
        if os.path.exists(git_dir):
            logger.info("Using existing local repo at %s", self.repo_dir)
            self._run(["remote", "set-url", "origin", self._authenticated_url])
            return False

        os.makedirs(self.repo_dir, exist_ok=True)

        # Attempt clone
        clone_result = subprocess.run(
            ["git", "clone", "--branch", self.branch, "--depth", "1",
             self._authenticated_url, self.repo_dir],
            capture_output=True,
            text=True,
            env=self._env(),
        )
        if clone_result.returncode == 0:
            logger.info("Cloned %s (branch: %s)", self._display_url, self.branch)
            return True

        # Clone failed (empty repo, branch not yet created, etc.) – init fresh
        logger.info(
            "Clone failed (%s), initialising new local repo",
            clone_result.stderr.strip()[:120],
        )
        self._run(["init", f"--initial-branch={self.branch}"], cwd=self.repo_dir)
        self._run(["remote", "add", "origin", self._authenticated_url], cwd=self.repo_dir)
        return True

    def checkout_branch(self):
        """Switch to the target branch, creating it if it does not exist locally."""
        local_branches = self._run(["branch", "--list", self.branch]).stdout.strip()
        if local_branches:
            self._run(["checkout", self.branch])
            return

        # Fetch to discover remote branches
        self._run(["fetch", "origin"], check=False)

        remote_exists = self._run(
            ["ls-remote", "--heads", "origin", self.branch], check=False
        ).stdout.strip()

        if remote_exists:
            self._run(["checkout", "-b", self.branch, f"origin/{self.branch}"])
        else:
            self._run(["checkout", "-b", self.branch])

    # ------------------------------------------------------------------
    # Status / diff queries
    # ------------------------------------------------------------------

    def get_status(self) -> List[str]:
        """Return relative paths of files with uncommitted changes."""
        result = self._run(["status", "--porcelain"])
        paths = []
        for line in result.stdout.splitlines():
            if line.strip():
                paths.append(line[3:].strip())
        return paths

    def current_commit(self) -> Optional[str]:
        result = self._run(["rev-parse", "HEAD"], check=False)
        return result.stdout.strip() if result.returncode == 0 else None

    def has_any_commits(self) -> bool:
        result = self._run(["log", "--oneline", "-1"], check=False)
        return result.returncode == 0 and bool(result.stdout.strip())

    def get_remote_commits_ahead(self) -> int:
        """How many commits the remote branch is ahead of the local branch."""
        result = self._run(
            ["rev-list", "--count", f"HEAD..origin/{self.branch}"], check=False
        )
        if result.returncode != 0:
            return 0
        try:
            return int(result.stdout.strip())
        except ValueError:
            return 0

    def get_local_commits_ahead(self) -> int:
        """How many commits the local branch is ahead of the remote branch."""
        result = self._run(
            ["rev-list", "--count", f"origin/{self.branch}..HEAD"], check=False
        )
        if result.returncode != 0:
            return 0
        try:
            return int(result.stdout.strip())
        except ValueError:
            return 0

    def is_diverged(self) -> bool:
        """True when both local and remote have commits the other lacks."""
        return self.get_remote_commits_ahead() > 0 and self.get_local_commits_ahead() > 0

    def get_changed_files_since(self, base_commit: str) -> List[str]:
        result = self._run(["diff", "--name-only", base_commit, "HEAD"])
        return [f for f in result.stdout.splitlines() if f.strip()]

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def stage_all(self):
        self._run(["add", "-A"])

    def commit(self, message: str) -> str:
        """Commit all staged changes and return the new commit hash."""
        self._run(["commit", "-m", message])
        return self._run(["rev-parse", "HEAD"]).stdout.strip()

    def push(self, dry_run: bool = False):
        args = ["push", "origin", self.branch]
        if dry_run:
            args.append("--dry-run")
        self._run(args)
        verb = "Dry-run push" if dry_run else "Pushed"
        logger.info("%s to %s (branch: %s)", verb, self._display_url, self.branch)

    def fetch(self):
        self._run(["fetch", "origin"])

    def fast_forward_merge(self):
        """Merge the remote branch into the local branch using fast-forward only."""
        self._run(["merge", "--ff-only", f"origin/{self.branch}"])

    def backup_branch(self, backup_name: str):
        """Create or update a local backup branch pointing at the current HEAD."""
        self._run(["branch", "-f", backup_name, "HEAD"])

    def reset_to(self, commit: str):
        """Hard-reset the working tree and index to a specific commit."""
        self._run(["reset", "--hard", commit])

    def set_gitignore(self, patterns: List[str]):
        """Write a .gitignore containing the given deny patterns."""
        gitignore_path = os.path.join(self.repo_dir, ".gitignore")
        # Only write if the file does not already exist (respect user customisation)
        if os.path.exists(gitignore_path):
            return
        lines = [
            "# Managed by HA GitHub Sync – edit to customise exclusions",
            "# Re-creating this file on first run only; manual edits are preserved.",
            "",
        ] + list(patterns)
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
