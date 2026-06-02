import pandas as pd
import re

INPUT_FILE = "runs.csv"
OUTPUT_FILE = "run_lineage.mmd"
MARKDOWN_OUTPUT_FILE = "run_lineage.md"

TYPE_STYLES = {
    "train": "fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px",
    "fine-tune": "fill:#e3f2fd,stroke:#1565c0,stroke-width:2px",
    "continue-train": "fill:#e0f2f1,stroke:#00796b,stroke-width:2px",
    "inference": "fill:#fff8e1,stroke:#f9a825,stroke-width:2px",
    "evaluation": "fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px",
}

CATEGORY_STYLES = {
    "production-candidate": "stroke-width:4px",
    "debug": "stroke-dasharray:5 5",
    "failed-but-useful": "stroke:#c62828,stroke-width:3px",
    "archive": "fill:#eeeeee,stroke:#9e9e9e,color:#777777",
    "avg-dt": "stroke-dasharray:5 5",
    "1y-rollout": "stroke-width:4px",
}

def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()

def mermaid_id(run_id: str) -> str:
    return "run_" + re.sub(r"[^a-zA-Z0-9_]", "_", clean(run_id))

def class_name(prefix: str, value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", clean(value).lower())
    return f"{prefix}_{safe}"

def escape_label(value: str) -> str:
    return clean(value).replace('"', "'")

def parse_parent_ids(value):
    value = clean(value)
    if not value:
        return []

    # Supports semicolon, comma, or newline separated parents
    value = value.replace(";", ",").replace("\n", ",")

    return [
        parent.strip()
        for parent in value.split(",")
        if parent.strip()
    ]

df = pd.read_csv(INPUT_FILE)

# Optional filter
if "Include in diagram" in df.columns:
    df = df[
        df["Include in diagram"]
        .fillna("")
        .astype(str)
        .str.lower()
        .isin(["yes", "y", "true", "1"])
    ]

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

    label_parts = [escape_label(run_id)]
    if run_type:
        label_parts.append(escape_label(run_type))
    if category:
        label_parts.append(escape_label(category))

    label = "<br/>".join(label_parts)

    # Important: no inline ::: classes here
    lines.append(f'    {node_id}["{label}"]')

    if run_type:
        type_cls = class_name("type", run_type)
        class_assignments.append(f"    class {node_id} {type_cls};")
        used_type_classes.add((type_cls, run_type))

    if category:
        category_cls = class_name("category", category)
        class_assignments.append(f"    class {node_id} {category_cls};")
        used_category_classes.add((category_cls, category))

# Edges
lines.append("")

parent_col = "Parent Run IDs" if "Parent Run IDs" in df.columns else "Parent Run ID"

for _, row in df.iterrows():
    run_id = clean(row["Run ID"])
    run_type = clean(row.get("Type", ""))
    parent_ids = parse_parent_ids(row.get(parent_col, ""))

    if len(parent_ids) > 1 and run_type != "evaluation":
        print(
            f"Warning: {run_id} has multiple parents, "
            f"but type is {run_type!r}, not 'evaluation'"
        )

    for parent_id in parent_ids:
        if parent_id not in known_run_ids:
            print(f"Warning: parent run ID not found in table: {parent_id}")

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

# Write raw Mermaid file
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Wrote {OUTPUT_FILE}")

# Write Markdown wrapper
markdown_lines = ["```mermaid"] + lines + ["```"]

with open(MARKDOWN_OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(markdown_lines))

print(f"Wrote {MARKDOWN_OUTPUT_FILE}")