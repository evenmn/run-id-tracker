import csv
import re
from pathlib import Path

INPUT_FILE = Path("runs.csv")
README_FILE = Path("README.md")
MERMAID_FILE = Path("run_lineage.mmd")

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
    "comparison": "stroke-width:4px",
}

TABLE_COLUMNS = [
    "Run ID",
    "Type",
    "Parent Run IDs",
    "Family",
    "Category",
    "Status",
    "Notes",
]


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def mermaid_id(run_id):
    return "run_" + re.sub(r"[^a-zA-Z0-9_]", "_", clean(run_id))


def class_name(prefix, value):
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", clean(value).lower())
    return f"{prefix}_{safe}"


def parse_parent_ids(value):
    value = clean(value)
    if not value:
        return []

    value = value.replace("\n", ";").replace(",", ";")

    return [
        parent.strip()
        for parent in value.split(";")
        if parent.strip()
    ]


def escape_mermaid_label(value):
    return clean(value).replace('"', "'")


def escape_markdown_cell(value):
    value = clean(value)
    value = value.replace("|", r"\|")
    value = value.replace("\n", "<br/>")
    return value


def read_runs():
    with INPUT_FILE.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    return rows


def included_in_diagram(row):
    value = clean(row.get("Include in diagram", "yes")).lower()
    return value in {"yes", "y", "true", "1", ""}


def generate_mermaid(rows):
    diagram_rows = [row for row in rows if included_in_diagram(row)]

    known_run_ids = {
        clean(row.get("Run ID"))
        for row in diagram_rows
        if clean(row.get("Run ID"))
    }

    lines = ["flowchart TD", ""]

    used_type_classes = set()
    used_category_classes = set()
    class_assignments = []

    # Nodes
    for row in diagram_rows:
        run_id = clean(row.get("Run ID"))
        if not run_id:
            continue

        run_type = clean(row.get("Type"))
        category = clean(row.get("Category"))

        node_id = mermaid_id(run_id)

        label_parts = [escape_mermaid_label(run_id)]
        if run_type:
            label_parts.append(escape_mermaid_label(run_type))
        if category:
            label_parts.append(escape_mermaid_label(category))

        label = "<br/>".join(label_parts)

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

    for row in diagram_rows:
        run_id = clean(row.get("Run ID"))
        if not run_id:
            continue

        run_type = clean(row.get("Type"))
        parent_ids = parse_parent_ids(row.get("Parent Run IDs") or row.get("Parent Run ID"))

        if len(parent_ids) > 1 and run_type != "evaluation":
            print(
                f"Warning: {run_id} has multiple parents, "
                f"but type is {run_type!r}, not 'evaluation'"
            )

        for parent_id in parent_ids:
            if parent_id not in known_run_ids:
                print(f"Warning: parent run ID not found in diagram table: {parent_id}")

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

    return "\n".join(lines)


def generate_markdown_table(rows):
    if not rows:
        return "_No runs found._"

    available_columns = rows[0].keys()
    columns = [col for col in TABLE_COLUMNS if col in available_columns]

    if not columns:
        columns = list(available_columns)

    lines = []

    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")

    for row in rows:
        values = [escape_markdown_cell(row.get(col)) for col in columns]
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def replace_section(text, marker_name, new_content):
    start = f"<!-- {marker_name}_START -->"
    end = f"<!-- {marker_name}_END -->"

    if start not in text or end not in text:
        raise ValueError(f"Missing markers: {start} / {end}")

    before = text.split(start)[0]
    after = text.split(end)[1]

    return (
        before
        + start
        + "\n"
        + new_content.strip()
        + "\n"
        + end
        + after
    )


def main():
    rows = read_runs()

    mermaid = generate_mermaid(rows)
    table = generate_markdown_table(rows)

    MERMAID_FILE.write_text(mermaid + "\n", encoding="utf-8")

    mermaid_block = f"```mermaid\n{mermaid}\n```"

    if README_FILE.exists():
        readme = README_FILE.read_text(encoding="utf-8")
    else:
        readme = """# Run Registry

## Run lineage

<!-- RUN_LINEAGE_START -->
<!-- RUN_LINEAGE_END -->

## Runs

<!-- RUN_TABLE_START -->
<!-- RUN_TABLE_END -->
"""

    readme = replace_section(readme, "RUN_LINEAGE", mermaid_block)
    readme = replace_section(readme, "RUN_TABLE", table)

    README_FILE.write_text(readme, encoding="utf-8")

    print(f"Wrote {MERMAID_FILE}")
    print(f"Wrote {README_FILE}")


if __name__ == "__main__":
    main()
