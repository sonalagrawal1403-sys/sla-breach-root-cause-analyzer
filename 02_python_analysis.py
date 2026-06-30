import pandas as pd
from scipy.stats import chi2_contingency
import matplotlib.pyplot as plt
from google.colab import files

# ------------------------------------------------------------
# STEP 1: Upload the two cleaned tables exported from MySQL
# When prompted, select BOTH tickets.csv and agents.csv
# ------------------------------------------------------------
uploaded = files.upload()

tickets = pd.read_csv("tickets.csv")
agents = pd.read_csv("agents.csv")

# ------------------------------------------------------------
# STEP 2: Recreate the SQL join in pandas
# Doing this in Python too (instead of just exporting the
# already-joined result) shows the same join logic works
# consistently whether you write it in SQL or pandas.
# ------------------------------------------------------------
df = tickets.merge(agents, on="agent_id", how="left")
print("Merged shape:", df.shape)

# ------------------------------------------------------------
# STEP 3: Restrict to tickets with a valid SLA breach flag
# (mirrors the WHERE sla_breached IS NOT NULL filter from SQL)
# ------------------------------------------------------------
analysis_df = df[df["sla_breached"].notna()].copy()
print("Tickets included in analysis:", len(analysis_df))

# ------------------------------------------------------------
# STEP 4: Build the flag for the finding: Team C + Technical Bug
# ------------------------------------------------------------
analysis_df["is_team_c_techbug"] = (
    (analysis_df["team"] == "Team C") & (analysis_df["category"] == "Technical Bug")
)

# ------------------------------------------------------------
# STEP 5: Chi-square test of independence
# Question: is SLA breach really associated with being
# Team C + Technical Bug, or could this pattern plausibly
# show up by chance alone?
# ------------------------------------------------------------
contingency = pd.crosstab(analysis_df["is_team_c_techbug"], analysis_df["sla_breached"])
print("\nContingency table:")
print(contingency)

chi2, p_value, dof, expected = chi2_contingency(contingency)
print(f"\nChi-square statistic: {chi2:.2f}")
print(f"p-value: {p_value:.10f}")

if p_value < 0.05:
    print("Statistically significant: this pattern is very unlikely to be due to chance.")
else:
    print("Not statistically significant at the 0.05 level.")

# ------------------------------------------------------------
# STEP 6: Pareto analysis across all team + category combinations
# Which combinations drive the most TOTAL breaches, not just rate?
# ------------------------------------------------------------
pareto = (
    analysis_df.groupby(["team", "category"])["sla_breached"]
    .sum()
    .reset_index()
    .sort_values("sla_breached", ascending=False)
)
pareto["cumulative_pct"] = 100 * pareto["sla_breached"].cumsum() / pareto["sla_breached"].sum()
pareto["combo"] = pareto["team"] + " - " + pareto["category"]
print("\nTop contributors to total SLA breaches:")
print(pareto.head(10)[["combo", "sla_breached", "cumulative_pct"]])

# ------------------------------------------------------------
# STEP 7: Pareto chart
# ------------------------------------------------------------
top = pareto.head(10)
fig, ax1 = plt.subplots(figsize=(11, 5))
ax1.bar(top["combo"], top["sla_breached"], color="#1F3864")
ax1.set_ylabel("Total SLA Breaches")
ax1.set_xticklabels(top["combo"], rotation=45, ha="right")

ax2 = ax1.twinx()
ax2.plot(top["combo"], top["cumulative_pct"], color="orange", marker="o")
ax2.set_ylabel("Cumulative % of All Breaches")
ax2.set_ylim(0, 110)

plt.title("Pareto Analysis: SLA Breaches by Team + Category")
plt.tight_layout()
plt.savefig("pareto_breaches.png", dpi=150)
plt.show()

# ------------------------------------------------------------
# STEP 8: Export the merged, analysis-ready dataset for Power BI
# ------------------------------------------------------------
df.to_csv("tickets_for_powerbi.csv", index=False)
files.download("tickets_for_powerbi.csv")
