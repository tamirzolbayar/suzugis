import json
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from popup import make_popup_html
from map_generator import style_by_restriction
from excel_loader import load_excel, save_excel
from filters import apply_filters
from config import DEFAULT_LOCATION, DEFAULT_ZOOM, MAP_STYLES
from permit_documents import make_permit_link_html


def parse_progress(value):
    try:
        return int(str(value).replace("%", "").strip())
    except (TypeError, ValueError):
        return 0


def iter_coordinate_pairs(geometry):
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])

    if geometry_type == "Point":
        yield coordinates
    elif geometry_type in ("LineString", "MultiPoint"):
        yield from coordinates
    elif geometry_type in ("Polygon", "MultiLineString"):
        for part in coordinates:
            yield from part
    elif geometry_type == "MultiPolygon":
        for polygon in coordinates:
            for ring in polygon:
                yield from ring


def get_feature_bounds(features):
    lats = []
    lngs = []

    for feature in features:
        for coordinate in iter_coordinate_pairs(feature.get("geometry", {})):
            if len(coordinate) >= 2:
                lngs.append(coordinate[0])
                lats.append(coordinate[1])

    if not lats or not lngs:
        return None

    return [[min(lats), min(lngs)], [max(lats), max(lngs)]]


BASE_DIR = Path(__file__).resolve().parent.parent
GEOJSON_PATH = BASE_DIR / "data" / "geojson" / "suzu_sample.geojson"
EXCEL_PATH = BASE_DIR / "data" / "excel" / "restriction_list.xlsx"

st.set_page_config(page_title="SuzuGIS", layout="wide")

st.markdown(
    """
    <style>
        .block-container {
            max-width: 100%;
            padding-top: 0.15rem;
            padding-left: 0;
            padding-right: 0;
            padding-bottom: 0;
        }

        [data-testid="stSidebar"] {
            min-width: 21rem;
            max-width: 21rem;
        }

        [data-testid="stVerticalBlock"] {
            gap: 0.15rem;
        }

        .main-title {
            display: none;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">SuzuGIS</div>', unsafe_allow_html=True)
df, restriction_dict = load_excel(EXCEL_PATH)


# Sidebar

with st.sidebar:
    st.header("SuzuGIS")
    st.caption("操作パネル")

    st.markdown("---")
    st.subheader("🗺 地図設定")

    map_style = st.selectbox(
        "地図タイプ",
        list(MAP_STYLES.keys()),
        index=list(MAP_STYLES.keys()).index("淡色地図"),
    )

    st.markdown("---")
    st.subheader("📅 表示条件")

    target_date = st.date_input(
        "対象日",
        value=pd.to_datetime("2026-07-15")
    )

    st.subheader("🚧 規制種別")

    show_full_closure = st.checkbox("全面通行止め", value=True)
    show_alternate = st.checkbox("片側交互通行", value=True)
    show_lane = st.checkbox("車線規制", value=True)
    show_completed = st.checkbox("完了", value=True)
    st.subheader("📊 進捗")
    st.subheader("🏗 施工者")

    contractors = ["すべて"] + sorted(df["施工者"].dropna().unique().tolist())
    
    contractor_filter = st.selectbox(
        "施工者を選択",
        contractors
    )

    st.markdown("---")
    st.subheader("✏️ 選択中の規制")

    restriction_ids = df["規制ID"].tolist()
    selected_id = st.session_state.get(
        "selected_restriction_id",
        restriction_ids[0]
    )
    if selected_id not in restriction_ids:
        selected_id = restriction_ids[0]

    selected_id = st.selectbox(
        "編集する規制ID",
        restriction_ids,
        index=restriction_ids.index(selected_id),
    )
    st.session_state["selected_restriction_id"] = selected_id

    edit_id = selected_id
    edit_row = df[df["規制ID"] == edit_id].iloc[0]
    permit_link_html = make_permit_link_html(BASE_DIR, edit_id)

    st.markdown(
        f"""
        <div style="
            background-color:#f7f9fc;
            padding:12px;
            border-radius:10px;
            border:1px solid #d0d7de;
            margin-bottom:12px;
        ">
            <div style="font-size:14px; color:#666;">現在選択中</div>
            <div style="font-size:22px; font-weight:bold;">🚧 {edit_id}</div>
            <div style="font-size:14px; margin-top:4px;">{edit_row["工事名"]}</div>
            <div style="font-size:13px; color:#666; margin-top:4px;">
                {edit_row["施工者"]} / 進捗 {edit_row["進捗率"]}%
            </div>
            <div style="font-size:13px; margin-top:8px;">
                <b>道路使用許可:</b> {permit_link_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.form("selected_road_edit_form"):
        edit_contractor = st.text_input(
            "施工者",
            value=str(edit_row["施工者"])
        )

        edit_progress = st.number_input(
            "進捗率",
            min_value=0,
            max_value=100,
            value=parse_progress(edit_row["進捗率"])
        )

        edit_note = st.text_area(
            "備考",
            value=str(edit_row["備考"])
        )

        submitted = st.form_submit_button("保存")

        if submitted:
            df.loc[df["規制ID"] == edit_id, "施工者"] = edit_contractor
            df.loc[df["規制ID"] == edit_id, "進捗率"] = edit_progress
            df.loc[df["規制ID"] == edit_id, "備考"] = edit_note

            backup_path = save_excel(df, EXCEL_PATH)
            st.success(f"{edit_id} を保存しました")
            if backup_path is not None:
                st.caption(f"バックアップ作成：{backup_path.name}")
            else:
                st.caption("バックアップ作成：未確認")
            st.rerun()
    

# GeoJSON load
with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

geojson_data, filtered_features = apply_filters(
    geojson_data=geojson_data,
    restriction_dict=restriction_dict,
    target_date=target_date,
    show_full_closure=show_full_closure,
    show_alternate=show_alternate,
    show_lane=show_lane,
    show_completed=show_completed,
    contractor_filter=contractor_filter,
)


# Counts
st.sidebar.markdown("---")
st.sidebar.subheader("表示件数")
st.sidebar.metric("規制区間数", len(filtered_features))

m = folium.Map(
    location=DEFAULT_LOCATION,
    zoom_start=DEFAULT_ZOOM,
    tiles=None,
    width="100%",
    height="850px",
)

folium.TileLayer(
    tiles=MAP_STYLES[map_style]["url"],
    attr=MAP_STYLES[map_style]["attr"],
    name=map_style,
).add_to(m)

if len(geojson_data["features"]) > 0:
    feature_bounds = get_feature_bounds(geojson_data["features"])
    if feature_bounds is not None:
        m.fit_bounds(feature_bounds, padding=(30, 30))

    gj = folium.GeoJson(
        geojson_data,
        name="規制区間",
        style_function=lambda feature: style_by_restriction(
            feature,
            st.session_state.get("selected_restriction_id")
            )
    ).add_to(m)

    for feature in geojson_data["features"]:
        props = feature["properties"]
        permit_link_html = make_permit_link_html(BASE_DIR, props.get("規制ID", ""))
        road_info_html = make_popup_html(props, permit_link_html)
        folium.GeoJson(
            feature,
            style_function=style_by_restriction,
            tooltip=folium.Tooltip(road_info_html, sticky=True),
            popup=folium.Popup(road_info_html, max_width=450)
        ).add_to(m)

else:
    st.warning("この条件に該当する規制区間はありません。")

folium.LayerControl().add_to(m)

st_folium(m, width=1500, height=850)
