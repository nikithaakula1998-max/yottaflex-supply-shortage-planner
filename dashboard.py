
from pathlib import Path
import csv
import json

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="YottaFlex Supply Shortage Planner",
    page_icon="📦",
    layout="wide",
)

BASE = Path(__file__).resolve().parent
SAMPLES = BASE / "sample_outputs"
FULL = BASE / "outputs" / "streaming_full_02"

st.title("📦 YottaFlex Supply Shortage Planner")
st.caption(
    "Synthetic supply-chain planning | "
    "Full-scale validation results and sample data"
)

st.info(
    "This dashboard displays previously verified full-scale results "
    "and small CSV previews. Sample rows are not used to calculate "
    "full-scale totals."
)


@st.cache_data
def read_sample(filename):
    path = SAMPLES / filename
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


@st.cache_data
def read_manifest():
    path = FULL / "manifest.json"
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def show_table(filename, title):
    st.subheader(title)
    df = read_sample(filename)

    if df.empty:
        st.info("No data rows available in this sample.")
        return

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.download_button(
        "Download sample CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        key=f"download_{filename}",
    )


st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select section",
    [
        "Overview",
        "Shortage Analysis",
        "Production Feasibility",
        "Mitigation Decisions",
        "Supplier Validation",
        "Data Explorer",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Source: synthetic YottaFlex project data")
st.sidebar.caption("Sample files contain at most 100 data rows.")

if page == "Overview":
    st.header("Project Overview")

    a, b, c, d = st.columns(4)
    a.metric("SKUs", "3,000")
    b.metric("Locations", "50")
    c.metric("Suppliers", "500")
    d.metric("Forecast records", "7,800,000")

    a, b, c, d = st.columns(4)
    a.metric("Shortage records", "7,065,828")
    b.metric("Mitigation candidates", "7,065,828")
    c.metric("Purchase orders", "10,000")
    d.metric("Automated tests passed", "16 / 16")

    st.subheader("How the project works")
    st.markdown(
        """
        1. Generate connected synthetic supply-chain datasets.
        2. Calculate projected shortages across locations and weeks.
        3. Validate supplier orders and capacity constraints.
        4. Evaluate production plans against BOM and capacity.
        5. Review mitigation candidates for preliminary feasibility.
        6. Export reports for analysis and review.
        """
    )

    st.subheader("Verified production results")
    st.metric("Feasible production units", "260,000")
    st.metric("Unfulfilled proposed units", "59,954,200")

    st.caption(
        "These metrics come from the project's completed full-scale "
        "validation run. They are not recalculated from sample files."
    )

elif page == "Shortage Analysis":
    st.header("Shortage Analysis")
    st.metric("Generated shortage records", "7,065,828")

    df = read_sample("shortage.csv")
    if df.empty:
        st.warning("Shortage sample not available.")
    else:
        st.subheader("Sample shortage records")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("Sample column explorer")
        numeric_cols = df.select_dtypes(
            include="number"
        ).columns.tolist()

        if numeric_cols:
            selected = st.selectbox(
                "Choose a numeric column",
                numeric_cols,
            )
            st.bar_chart(df[selected].head(30))
        else:
            st.info("No numeric columns available for charting.")

        st.caption(
            "Chart uses only the first sample rows; "
            "it does not describe the full population."
        )

elif page == "Production Feasibility":
    st.header("Production and BOM Feasibility")

    a, b, c = st.columns(3)
    a.metric("Feasible production units", "260,000")
    b.metric("Feasible share", "0.43%")
    c.metric("Unfulfilled proposed units", "59,954,200")

    st.warning(
        "Production proposals are not all executable. "
        "BOM, component availability, and weekly capacity "
        "constraints restrict feasibility."
    )

    show_table(
        "cumulative_bom_report.csv",
        "Sample cumulative BOM validation",
    )
    show_table(
        "feasible_shortage_plan.csv",
        "Sample feasible shortage plan",
    )

elif page == "Mitigation Decisions":
    st.header("Mitigation Validation")

    a, b, c = st.columns(3)
    a.metric("Candidates evaluated", "7,065,828")
    b.metric("Potentially feasible", "500")
    c.metric("Flagged for review", "7,065,328")

    chart_data = pd.DataFrame(
        {
            "Decision": [
                "Potentially feasible",
                "Flag for review",
            ],
            "Count": [500, 7065328],
        }
    ).set_index("Decision")

    st.bar_chart(chart_data)

    st.caption(
        "POTENTIALLY_FEASIBLE_UNCONFIRMED is not an "
        "approved or guaranteed executable mitigation."
    )

    show_table(
        "mitigation_feasibility_report.csv",
        "Sample mitigation feasibility decisions",
    )

elif page == "Supplier Validation":
    st.header("Supplier Validation")

    a, b = st.columns(2)
    a.metric("Purchase orders checked", "10,000")
    b.metric("Supplier validation issues", "0")

    st.success(
        "The full-scale supplier validation run reported "
        "no issues for the generated purchase orders."
    )

    st.caption(
        "This does not guarantee that every downstream "
        "production or mitigation proposal is feasible."
    )

    show_table(
        "purchase_order.csv",
        "Sample purchase orders",
    )
    show_table(
        "supplier_validation_report.csv",
        "Supplier validation issues",
    )

elif page == "Data Explorer":
    st.header("Explore Generated Data")

    available = sorted(
        p.name for p in SAMPLES.glob("*.csv")
    ) if SAMPLES.exists() else []

    if not available:
        st.error(
            "No sample files found. Run: "
            "py -m src.create_sample_outputs"
        )
    else:
        filename = st.selectbox(
            "Choose a sample dataset",
            available,
        )

        df = read_sample(filename)
        st.metric("Sample rows", len(df))

        if not df.empty:
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("This report contains no data rows.")

        st.download_button(
            "Download selected CSV",
            data=(SAMPLES / filename).read_bytes(),
            file_name=filename,
            mime="text/csv",
        )

st.divider()
st.caption(
    "YottaFlex Supply Shortage Planner | "
    "Synthetic data only | "
    "Candidate mitigations require further review"
)
