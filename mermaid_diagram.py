import pandas as pd
import re

INPUT_FILE = "runs.csv"
OUTPUT_FILE = "run_lineage.mmd"

TYPE_STYLES = {
    "train": "fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px",
    "fine-tune": "fill:#e3f2fd,stroke:#1565c0,stroke-width:2px",
    "continue-train": "fill:#e0f2f1,stroke:#00796b,stroke-width:2px",
    "inference": "fill:#fff8e1,stroke:#f9a825,stroke-width:2px",
    "evaluation": "fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px",
}

CATEGORY_STYLES = {
    "production-candidate": "stroke-width:4px",
    "debug": "stroke-dasharray: 5 5",
    "failed-but-useful": "stroke:#c62828,stroke-width:3px",
    "archive": "fill:#eeeeee,stroke:#9e9e9e,color:#777777",
}

def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()

def mermaid_id(run_id: str) -> str:
    return "run_" + re.sub(r"[^a-zA-Z0-9_]", "_", run_id)

def class_name(prefix: str, value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", value.lower())
    return f"{prefix}_{safe}"

df = pd.read_csv(INPUT_FILE)

if "Include in diagram" in df.columns:
    df = df[df["Include in diagram"].fillna("").astype(str).str.lower().isin(["yes", "y", "true", "1"])]

known_run_ids = set(df["Run ID"].map(clean))

lines = ["flowchart TD", ""]

used_type_classes = set()
used_category_classes = set()

class_assignments = []

# Nodes
for _, row in df.iterrows():
    run_id = clean(row["Run ID"])
    run_type = clean(row.get("Type", ""))
    category = clean(row.get("Category", ""))

    node_id = mermaid_id(run_id)

    label_parts = [run_id]
    if run_type:
        label_parts.append(run_type)
    if category:
        label_parts.append(category)

    label = "<br/>".join(label_parts).replace('"', "'")

    # Write node WITHOUT inline classes
    lines.append(f'    {node_id}["{label}"]')

    # Add class assignments separately
    if run_type:
        type_cls = class_name("type", run_type)
        class_assignments.append(f"    class {node_id} {type_cls};")
        used_type_classes.add((type_cls, run_type))

    if category:
        category_cls = class_name("category", category)
        class_assignments.append(f"    class {node_id} {category_cls};")
        used_category_classes.add((category_cls, category))

    lines.append(f'    {node_id}["{label}"]')

    #for cls in classes:
    #    class_assignments.append(f"    class {node_id} {cls};")

# Edges
lines.append("")

for _, row in df.iterrows():
    run_id = clean(row["Run ID"])
    parent_id = clean(row.get("Parent Run ID", ""))

    if parent_id:
        lines.append(f"    {mermaid_id(parent_id)} --> {mermaid_id(run_id)}")

# Class assignments
lines.append("")

for assignment in class_assignments:
    lines.append(assignment)

# Class definitions
lines.append("")

for cls, run_type in sorted(used_type_classes):
    style = TYPE_STYLES.get(run_type)
    if style:
        lines.append(f"    classDef {cls} {style};")

for cls, category in sorted(used_category_classes):
    style = CATEGORY_STYLES.get(category)
    if style:
        lines.append(f"    classDef {cls} {style};")

with open(OUTPUT_FILE, "w") as f:
    f.write("\n".join(lines))

print(f"Wrote {OUTPUT_FILE}")

lines2 = ["```mermaid"] + lines + ["```"]

with open("run_lineage.md", "w") as f:
    f.write("\n".join(lines2))

print(f"Wrote run_lineage.md")