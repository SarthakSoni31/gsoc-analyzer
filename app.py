import streamlit as st
import pandas as pd
import plotly.express as px
from analyzer import analyze_multiple

st.set_page_config(page_title="GitHub Repo Intelligence Analyzer", page_icon="🔍", layout="wide")

st.title("🔍 GitHub Repository Intelligence Analyzer")
st.markdown("Analyze GitHub repositories for activity, complexity, and learning difficulty.")

with st.sidebar:
    st.header("Configuration")
    token = st.text_input("GitHub Token (optional but recommended)", type="password", 
                          help="Add your GitHub token to avoid rate limits")
    st.markdown("---")
    st.markdown("**Scoring Formula**")
    st.markdown("**Activity Score (0-100)**")
    st.markdown("- Stars: up to 20 pts")
    st.markdown("- Forks: up to 15 pts")
    st.markdown("- Commits: up to 25 pts")
    st.markdown("- Contributors: up to 20 pts")
    st.markdown("- Open Issues: up to 10 pts")
    st.markdown("- Recent Push: up to 10 pts")
    st.markdown("**Complexity Score (0-100)**")
    st.markdown("- Language diversity: up to 30 pts")
    st.markdown("- File count: up to 20 pts")
    st.markdown("- Repo size: up to 20 pts")
    st.markdown("- Dependency files: up to 30 pts")
    st.markdown("**Difficulty = 40% Activity + 60% Complexity**")

st.markdown("### Enter GitHub Repository URLs")
default_repos = """https://github.com/c2siorg/Webiu
https://github.com/c2siorg/imagelab
https://github.com/c2siorg/tensormap
https://github.com/c2siorg/codelabz
https://github.com/c2siorg/b0bot"""

urls_input = st.text_area("One URL per line", value=default_repos, height=180)

if st.button("🚀 Analyze Repositories", type="primary"):
    urls = [u.strip() for u in urls_input.strip().split("\n") if u.strip()]
    
    if not urls:
        st.error("Please enter at least one repository URL.")
    else:
        with st.spinner(f"Analyzing {len(urls)} repositories..."):
            results = analyze_multiple(urls, token if token else None)
        
        successful = [r for r in results if not r.get("error")]
        failed = [r for r in results if r.get("error")]

        if failed:
            st.warning(f"{len(failed)} repository/repositories could not be analyzed:")
            for r in failed:
                st.error(f"❌ {r['url']} — {r['error']}")

        if successful:
            st.success(f"✅ Successfully analyzed {len(successful)} repositories")
            st.markdown("---")

            # Summary cards
            col1, col2, col3 = st.columns(3)
            avg_activity = sum(r["activity_score"] for r in successful) / len(successful)
            avg_complexity = sum(r["complexity_score"] for r in successful) / len(successful)
            difficulties = [r["difficulty"] for r in successful]
            most_common = max(set(difficulties), key=difficulties.count)

            col1.metric("Avg Activity Score", f"{avg_activity:.1f}/100")
            col2.metric("Avg Complexity Score", f"{avg_complexity:.1f}/100")
            col3.metric("Most Common Difficulty", most_common)

            st.markdown("---")
            st.markdown("### 📊 Repository Analysis Results")

            for r in successful:
                with st.expander(f"**{r['name']}** — {r['difficulty']} | Activity: {r['activity_score']} | Complexity: {r['complexity_score']}"):
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("⭐ Stars", r["stars"])
                    col2.metric("🍴 Forks", r["forks"])
                    col3.metric("👥 Contributors", r["contributors_count"])
                    col4.metric("📝 Commits", r["commits_count"])

                    st.markdown(f"**Description:** {r['description']}")
                    st.markdown(f"**Primary Language:** {r['language']}")
                    st.markdown(f"**All Languages:** {', '.join(r['languages']) if r['languages'] else 'Unknown'}")
                    st.markdown(f"**Last Pushed:** {r['last_pushed'][:10] if r['last_pushed'] != 'Unknown' else 'Unknown'}")
                    st.markdown(f"**Open Issues:** {r['open_issues']}")

                    diff_color = {"Beginner": "🟢", "Intermediate": "🟡", "Advanced": "🔴"}
                    st.markdown(f"**Difficulty:** {diff_color.get(r['difficulty'], '⚪')} {r['difficulty']}")

                    col1, col2 = st.columns(2)
                    col1.progress(r["activity_score"] / 100, text=f"Activity: {r['activity_score']}/100")
                    col2.progress(r["complexity_score"] / 100, text=f"Complexity: {r['complexity_score']}/100")

            st.markdown("---")
            st.markdown("### 📈 Comparison Charts")

            df = pd.DataFrame(successful)

            fig1 = px.bar(df, x="repo", y=["activity_score", "complexity_score"],
                         barmode="group", title="Activity vs Complexity Scores",
                         labels={"value": "Score", "repo": "Repository"},
                         color_discrete_map={"activity_score": "#2E75B6", "complexity_score": "#1F4E79"})
            st.plotly_chart(fig1, use_container_width=True)

            fig2 = px.scatter(df, x="activity_score", y="complexity_score",
                             size="stars", color="difficulty", hover_name="repo",
                             title="Activity vs Complexity (bubble = stars)",
                             color_discrete_map={"Beginner": "green", "Intermediate": "orange", "Advanced": "red"})
            st.plotly_chart(fig2, use_container_width=True)

            diff_counts = df["difficulty"].value_counts().reset_index()
            diff_counts.columns = ["difficulty", "count"]
            fig3 = px.pie(diff_counts, values="count", names="difficulty",
                         title="Difficulty Distribution",
                         color_discrete_map={"Beginner": "green", "Intermediate": "orange", "Advanced": "red"})
            st.plotly_chart(fig3, use_container_width=True)

            st.markdown("---")
            st.markdown("### 📋 Full Data Table")
            display_cols = ["name", "stars", "forks", "contributors_count", 
                           "commits_count", "activity_score", "complexity_score", "difficulty"]
            st.dataframe(df[display_cols], use_container_width=True)

st.markdown("---")
st.markdown("Built by **Sarthak Soni** for C2SI GSoC 2026 Pre-Task | [GitHub](https://github.com/SarthakSoni31)")