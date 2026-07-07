def style_by_restriction(feature, selected_id=None):
    props = feature.get("properties", {})
    restriction = str(props.get("規制種別", "")).strip()

    if "全面" in restriction:
        color = "red"
    elif "片側" in restriction or "片交" in restriction:
        color = "orange"
    elif "車線" in restriction:
        color = "yellow"
    elif "完了" in restriction:
        color = "blue"
    else:
        color = "gray"

    if props.get("規制ID") == selected_id:
        return {
            "color": "black",
            "weight": 11,
            "opacity": 1.0,
        }

    return {
        "color": color,
        "weight": 6,
        "opacity": 0.9,
    }
