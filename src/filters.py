import pandas as pd


def apply_filters(
    geojson_data,
    restriction_dict,
    period_start,
    period_end,
    show_full_closure,
    show_alternate,
    show_lane,
    show_completed,
    contractor_filter,
):
    filtered_features = []

    for i, feature in enumerate(geojson_data["features"], start=1):
        props = feature.setdefault("properties", {})
        props["規制ID"] = str(props.get("規制ID") or f"R-{i:03}").strip()

        if props["規制ID"] not in restriction_dict:
            continue

        props.update(restriction_dict[props["規制ID"]])

        restriction = str(props.get("規制種別", "")).strip()

        is_allowed = (
            ("全面" in restriction and show_full_closure)
            or (("片側" in restriction or "片交" in restriction) and show_alternate)
            or ("車線" in restriction and show_lane)
            or ("完了" in restriction and show_completed)
        )

        if not is_allowed:
            continue

        feature_contractor = str(props.get("施工者", "")).strip()

        if contractor_filter != "すべて" and feature_contractor != contractor_filter:
            continue

        start = pd.to_datetime(props["開始日"])
        end = pd.to_datetime(props["終了日"])

        period_start = pd.to_datetime(period_start)
        period_end = pd.to_datetime(period_end)

        if end < period_start or start > period_end:
            continue

        total_days = (end - start).days
        elapsed_days = (period_end - start).days

        if total_days <= 0:
            schedule_progress = 100
        else:
            schedule_progress = int(max(0, min(100, elapsed_days / total_days * 100)))

        props["予定進捗率"] = f"{schedule_progress}%"
        props["開始日"] = start.strftime("%Y-%m-%d")
        props["終了日"] = end.strftime("%Y-%m-%d")

        filtered_features.append(feature)

    geojson_data["features"] = filtered_features
    return geojson_data, filtered_features
