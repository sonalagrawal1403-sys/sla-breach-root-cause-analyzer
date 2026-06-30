import random
import datetime
import csv

random.seed(42)

FIRST_NAMES = ["Aisha","Ravi","Maria","John","Priya","Carlos","Wei","Fatima","Tom","Nina",
               "Omar","Sara","Liam","Anjali","David","Mei","Hassan","Elena","Kunal","Grace"]
LAST_NAMES = ["Sharma","Patel","Garcia","Smith","Khan","Lopez","Chen","Ahmed","Brown","Singh",
              "Ali","Rossi","Murphy","Verma","Kim","Zhang","Hussain","Bianchi","Mehta","Clark"]

TEAMS = ["Team A", "Team B", "Team C", "Team D"]

NUM_AGENTS = 60
agents = []
for i in range(1, NUM_AGENTS + 1):
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    team = random.choices(TEAMS, weights=[0.27, 0.27, 0.2, 0.26])[0]
    hire_date = datetime.date(2025, 1, 1) + datetime.timedelta(days=random.randint(0, 700))
    agents.append({"agent_id": 5000 + i, "agent_name": name, "team": team, "hire_date": hire_date.isoformat()})

with open("/home/claude/agents.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["agent_id", "agent_name", "team", "hire_date"])
    writer.writeheader()
    writer.writerows(agents)

team_c_agents = [a["agent_id"] for a in agents if a["team"] == "Team C"]
other_agents = [a["agent_id"] for a in agents if a["team"] != "Team C"]

CATEGORIES = {
    "Billing Issue": ["Incorrect Charge", "Duplicate Payment", "Refund Delay"],
    "Technical Bug": ["App Crash", "Login Failure", "Sync Error"],
    "Shipping & Delivery": ["Delayed Shipment", "Lost Package", "Wrong Item Sent"],
    "Account Access": ["Password Reset", "Account Locked", "2FA Issue"],
    "Product Defect": ["Damaged on Arrival", "Missing Parts", "Quality Issue"],
    "Customer Service": ["Miscommunication", "Long Wait Time", "Unresolved Follow-up"],
}
CATEGORY_WEIGHTS = [0.22, 0.18, 0.18, 0.14, 0.14, 0.14]

PRIORITY_SLA = {"Critical": 4, "High": 24, "Medium": 48, "Low": 72}
PRIORITY_WEIGHTS = {"Critical": 0.08, "High": 0.27, "Medium": 0.40, "Low": 0.25}
CHANNELS = ["Call", "Chat", "Email"]
SEGMENTS = ["Consumer", "Small Business", "Enterprise"]

START = datetime.datetime(2026, 1, 1)
END = datetime.datetime(2026, 6, 30)
SPAN_MIN = int((END - START).total_seconds() // 60)

NUM_TICKETS = 1800
rows = []

for i in range(1, NUM_TICKETS + 1):
    ticket_id = 100000 + i
    category = random.choices(list(CATEGORIES.keys()), weights=CATEGORY_WEIGHTS)[0]
    sub_category = random.choice(CATEGORIES[category])
    priority = random.choices(list(PRIORITY_SLA.keys()), weights=list(PRIORITY_WEIGHTS.values()))[0]
    sla_target = PRIORITY_SLA[priority]
    channel = random.choices(CHANNELS, weights=[0.3, 0.45, 0.25])[0]
    segment = random.choices(SEGMENTS, weights=[0.55, 0.3, 0.15])[0]

    if category == "Technical Bug" and random.random() < 0.65:
        agent_id = random.choice(team_c_agents)
    else:
        agent_id = random.choice(team_c_agents + other_agents)

    is_team_c = agent_id in team_c_agents
    breach_prob = 0.5 if (is_team_c and category == "Technical Bug") else 0.13

    created_offset = random.randint(0, SPAN_MIN)
    created_at = START + datetime.timedelta(minutes=created_offset)

    is_open = random.random() < 0.04
    if is_open:
        resolved_at = None
        resolution_hours = None
    else:
        breached = random.random() < breach_prob
        if breached:
            resolution_hours = round(sla_target * random.uniform(1.15, 2.6), 1)
        else:
            resolution_hours = round(sla_target * random.uniform(0.25, 0.95), 1)
        resolved_at = created_at + datetime.timedelta(hours=resolution_hours)

    rows.append({
        "ticket_id": ticket_id,
        "created_at": created_at,
        "resolved_at": resolved_at,
        "category": category,
        "sub_category": sub_category,
        "priority": priority,
        "channel": channel,
        "agent_id": agent_id,
        "customer_segment": segment,
        "sla_target_hours": sla_target,
    })

def fmt_dt_a(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def fmt_dt_b(dt):
    return dt.strftime("%d/%m/%Y %H:%M")

n = len(rows)
mixed_format_idx = set(random.sample(range(n), int(n * 0.08)))
missing_agent_idx = set(random.sample(range(n), int(n * 0.05)))
case_mangle_idx = set(random.sample(range(n), int(n * 0.05)))
logic_error_idx = set(random.sample(range(n), int(n * 0.02)))
outlier_idx = set(random.sample(range(n), int(n * 0.015)))
whitespace_idx = set(random.sample(range(n), int(n * 0.04)))

final_rows = []
for idx, r in enumerate(rows):
    row = dict(r)

    if idx in mixed_format_idx:
        row["created_at"] = fmt_dt_b(row["created_at"])
        row["resolved_at"] = fmt_dt_b(row["resolved_at"]) if row["resolved_at"] else ""
    else:
        row["created_at"] = fmt_dt_a(row["created_at"])
        row["resolved_at"] = fmt_dt_a(row["resolved_at"]) if row["resolved_at"] else ""

    if idx in missing_agent_idx:
        row["agent_id"] = ""

    if idx in case_mangle_idx:
        row["priority"] = random.choice([row["priority"].lower(), row["priority"].upper()])

    if idx in whitespace_idx:
        row["category"] = f"  {row['category']} "

    if idx in logic_error_idx and r["resolved_at"] is not None:
        bad_resolved = r["created_at"] - datetime.timedelta(hours=random.uniform(1, 5))
        row["resolved_at"] = fmt_dt_a(bad_resolved)

    final_rows.append(row)

for idx in random.sample(range(n), int(n * 0.015)):
    if rows[idx]["resolved_at"] is not None:
        created = rows[idx]["created_at"]
        outlier_resolved = created + datetime.timedelta(hours=random.choice([0.05, 600, 850]))
        final_rows[idx]["resolved_at"] = fmt_dt_a(outlier_resolved)

dupes = random.sample(final_rows, int(n * 0.03))
for d in dupes:
    new_row = dict(d)
    new_row["ticket_id"] = 100000 + n + len(final_rows) - len(rows) + 1 + dupes.index(d)
    final_rows.append(new_row)

random.shuffle(final_rows)

fieldnames = ["ticket_id", "created_at", "resolved_at", "category", "sub_category",
              "priority", "channel", "agent_id", "customer_segment", "sla_target_hours"]

with open("/home/claude/tickets.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in final_rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})

print(f"Generated {len(agents)} agents and {len(final_rows)} ticket rows.")
