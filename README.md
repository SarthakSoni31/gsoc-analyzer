# GitHub Repository Intelligence Analyzer

A tool that analyzes GitHub repositories and generates insights about activity, complexity, and learning difficulty.

Built for C2SI GSoC 2026 Pre-Task by Sarthak Soni.

## Live Demo
https://gsoc-analyzer-fwoau2cg2qhqvcghk2bck7.streamlit.app

## Features
- Activity Score (0-100) based on stars, forks, commits, contributors, issues, and recency
- Complexity Score (0-100) based on language diversity, file count, repo size, and dependency files
- Learning Difficulty Classification: Beginner / Intermediate / Advanced
- Interactive charts and comparison visualizations
- Edge case handling for missing data
- Rate limit protection with request delays

## Scoring Formulas

### Activity Score (0-100)
- Stars: min(stars/50, 20) → max 20 pts
- Forks: min(forks/20, 15) → max 15 pts
- Commits: min(commits * 0.5, 25) → max 25 pts
- Contributors: min(contributors * 2, 20) → max 20 pts
- Open Issues: min(issues * 0.5, 10) → max 10 pts
- Recent Push: 10pts (<7d), 7pts (<30d), 4pts (<90d), 1pt (<1yr) → max 10 pts

### Complexity Score (0-100)
- Language diversity: min(languages * 5, 30) → max 30 pts
- File count: min(files * 2, 20) → max 20 pts
- Repo size: min(size/500, 20) → max 20 pts
- Dependency files: +5pts each (package.json, requirements.txt, etc.) → max 30 pts

### Difficulty Classification
- Combined = (Activity * 0.4) + (Complexity * 0.6)
- < 30 → Beginner
- 30–60 → Intermediate
- > 60 → Advanced

## How to Run Locally
```bash