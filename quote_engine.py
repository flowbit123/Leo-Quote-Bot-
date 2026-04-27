from config import PRICING_CONFIG


def size_from_label(trade: str, label: str) -> float:
    return float(PRICING_CONFIG[trade]["size_guide"][label.lower()])


def calculate_quote(trade: str, job_details: dict, area_m2: float) -> dict:
    line_items: list[dict] = []
    cfg = PRICING_CONFIG[trade]

    if trade == "painting":
        surfaces = job_details.get("surfaces", [])
        if "walls" in surfaces:
            amount = area_m2 * cfg["walls_per_m2"]
            line_items.append({"label": "Wall painting", "amount": amount})
        if "ceiling" in surfaces:
            amount = area_m2 * cfg["ceiling_per_m2"]
            line_items.append({"label": "Ceiling painting", "amount": amount})
        if job_details.get("prep"):
            amount = area_m2 * cfg["prep_per_m2"]
            line_items.append({"label": "Surface preparation", "amount": amount})
        parts = [s.capitalize() for s in surfaces]
        if job_details.get("prep"):
            parts.append("prep")
        summary = "Painting — " + " + ".join(parts)

    elif trade == "tiling":
        amount = area_m2 * cfg["labour_per_m2"]
        tiling_type = job_details.get("tiling_type", "floor")
        line_items.append({"label": f"Tiling labour ({tiling_type})", "amount": amount})
        if job_details.get("removal"):
            removal_amount = area_m2 * cfg["removal_per_m2"]
            line_items.append({"label": "Tile removal", "amount": removal_amount})
        summary = f"Tiling — {tiling_type}"
        if job_details.get("removal"):
            summary += " + removal"

    elif trade == "building":
        work_types = job_details.get("work_type", [])
        if "brickwork" in work_types:
            amount = area_m2 * cfg["brickwork_per_m2"]
            line_items.append({"label": "Brickwork", "amount": amount})
        if "plastering" in work_types:
            amount = area_m2 * cfg["plastering_per_m2"]
            line_items.append({"label": "Plastering", "amount": amount})
        work_label = " + ".join(w.capitalize() for w in work_types)
        job_nature = job_details.get("job_nature", "")
        summary = f"Building — {work_label}"
        if job_nature:
            summary += f" ({job_nature})"

    else:
        raise ValueError(f"Unknown trade: {trade}")

    total = sum(item["amount"] for item in line_items)
    return {"line_items": line_items, "total": total, "summary": summary}
