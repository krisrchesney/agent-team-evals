"""Turn aggregated results into report text."""


def render(results, key_header, value_header):
    lines = [f"{key_header},{value_header}"]
    for group in sorted(results):
        lines.append(f"{group},{results[group]:.2f}")
    return "\n".join(lines)
