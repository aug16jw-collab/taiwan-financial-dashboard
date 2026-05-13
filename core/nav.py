import pandas as pd
import streamlit as st


def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def stock_table(
    df: pd.DataFrame,
    key: str,
    *,
    use_container_width: bool = True,
    hide_index: bool = True,
    column_config: dict | None = None,
    height: int | None = None,
) -> None:
    """
    Display a dataframe with single-row selection.
    When a row is selected, shows a '查看個股分析' navigation button.
    Expects the dataframe to have a column named '代號' or 'code'.
    """
    kwargs: dict = dict(
        use_container_width=use_container_width,
        hide_index=hide_index,
        on_select="rerun",
        selection_mode="single-row",
        key=key,
    )
    if column_config:
        kwargs["column_config"] = column_config
    if height:
        kwargs["height"] = height

    event = st.dataframe(df, **kwargs)
    rows = event.selection.rows

    if not rows:
        return

    code_col = _find_col(df, ["代號", "code"])
    name_col = _find_col(df, ["名稱", "name"])
    if code_col is None:
        return

    row = df.iloc[rows[0]]
    selected_code = str(row[code_col]).strip()
    selected_name = str(row[name_col]).strip() if name_col else selected_code

    c1, c2 = st.columns([5, 1])
    c1.info(f"已選取：**{selected_code} {selected_name}**")
    with c2:
        if st.button("🔍 個股分析", key=f"_nav_{key}", use_container_width=True):
            # Use session_state to pass code — more reliable than query_params across page switches
            st.session_state["nav_code"] = selected_code
            st.switch_page("pages/2_個股分析.py")
