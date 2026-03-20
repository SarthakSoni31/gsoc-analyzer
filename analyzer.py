import requests
import time
from datetime import datetime, timezone

GITHUB_API = "https://api.github.com"

def get_headers(token=None):
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    return headers

def parse_repo_url(url):
    url = url.strip().rstrip("/")
    parts = url.replace("https://github.com/", "").split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None

def fetch_repo_data(owner, repo, token=None):
    headers = get_headers(token)
    data = {}

    try:
        r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=headers, timeout=10)
        if r.status_code == 404:
            return None, "Repository not found"
        if r.status_code == 403:
            return None, "Rate limit exceeded"
        r.raise_for_status()
        data["repo"] = r.json()
    except Exception as e:
        return None, str(e)

    # Commits (last 100)
    try:
        r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/commits?per_page=100", headers=headers, timeout=10)
        data["commits"] = r.json() if r.status_code == 200 else []
    except:
        data["commits"] = []

    # Contributors
    try:
        r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/contributors?per_page=100", headers=headers, timeout=10)
        data["contributors"] = r.json() if r.status_code == 200 else []
    except:
        data["contributors"] = []

    # Languages
    try:
        r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/languages", headers=headers, timeout=10)
        data["languages"] = r.json() if r.status_code == 200 else {}
    except:
        data["languages"] = {}

    # Issues (open)
    try:
        r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/issues?state=open&per_page=100", headers=headers, timeout=10)
        data["issues"] = r.json() if r.status_code == 200 else []
    except:
        data["issues"] = []

    # Contents (root)
    try:
        r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/contents", headers=headers, timeout=10)
        data["contents"] = r.json() if r.status_code == 200 else []
    except:
        data["contents"] = []

    return data, None

def calculate_activity_score(data):
    score = 0
    repo = data.get("repo", {})
    commits = data.get("commits", [])
    contributors = data.get("contributors", [])
    issues = data.get("issues", [])

    # Stars (max 20)
    stars = repo.get("stargazers_count", 0)
    score += min(stars / 50, 20)

    # Forks (max 15)
    forks = repo.get("forks_count", 0)
    score += min(forks / 20, 15)

    # Commits (max 25)
    score += min(len(commits) * 0.5, 25)

    # Contributors (max 20)
    score += min(len(contributors) * 2, 20)

    # Open issues (max 10)
    score += min(len(issues) * 0.5, 10)

    # Recent activity (max 10)
    pushed_at = repo.get("pushed_at")
    if pushed_at:
        last_push = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
        days_ago = (datetime.now(timezone.utc) - last_push).days
        if days_ago < 7:
            score += 10
        elif days_ago < 30:
            score += 7
        elif days_ago < 90:
            score += 4
        elif days_ago < 365:
            score += 1

    return round(min(score, 100), 2)

def calculate_complexity_score(data):
    score = 0
    languages = data.get("languages", {})
    contents = data.get("contents", [])
    repo = data.get("repo", {})

    # Language diversity (max 30)
    lang_count = len(languages)
    score += min(lang_count * 5, 30)

    # File count in root (max 20)
    file_count = len(contents) if isinstance(contents, list) else 0
    score += min(file_count * 2, 20)

    # Repo size (max 20)
    size = repo.get("size", 0)
    score += min(size / 500, 20)

    # Has dependency files (max 30)
    dep_files = ["package.json", "requirements.txt", "go.mod", "pom.xml",
                 "Cargo.toml", "build.gradle", "Gemfile", "composer.json"]
    if isinstance(contents, list):
        content_names = [f.get("name", "") for f in contents]
        for dep in dep_files:
            if dep in content_names:
                score += 5

    return round(min(score, 100), 2)

def classify_difficulty(activity_score, complexity_score):
    combined = (activity_score * 0.4) + (complexity_score * 0.6)
    if combined < 30:
        return "Beginner"
    elif combined < 60:
        return "Intermediate"
    else:
        return "Advanced"

def analyze_repository(url, token=None):
    owner, repo = parse_repo_url(url)
    if not owner or not repo:
        return {"url": url, "error": "Invalid URL format"}

    data, error = fetch_repo_data(owner, repo, token)
    if error:
        return {"url": url, "owner": owner, "repo": repo, "error": error}

    repo_info = data.get("repo", {})
    activity = calculate_activity_score(data)
    complexity = calculate_complexity_score(data)
    difficulty = classify_difficulty(activity, complexity)

    return {
        "url": url,
        "owner": owner,
        "repo": repo,
        "name": repo_info.get("full_name", f"{owner}/{repo}"),
        "description": repo_info.get("description") or "No description",
        "stars": repo_info.get("stargazers_count", 0),
        "forks": repo_info.get("forks_count", 0),
        "open_issues": repo_info.get("open_issues_count", 0),
        "language": repo_info.get("language") or "Unknown",
        "languages": list(data.get("languages", {}).keys()),
        "contributors_count": len(data.get("contributors", [])),
        "commits_count": len(data.get("commits", [])),
        "last_pushed": repo_info.get("pushed_at", "Unknown"),
        "activity_score": activity,
        "complexity_score": complexity,
        "difficulty": difficulty,
        "error": None
    }

def analyze_multiple(urls, token=None):
    results = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        result = analyze_repository(url, token)
        results.append(result)
        time.sleep(0.5)  # rate limit protection
    return results