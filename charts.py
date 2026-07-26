"""Small, automatic visualizations for SQL result sets."""
import pandas as pd
import streamlit as st


def _category_columns(data: pd.DataFrame) -> list[str]:
    """Treat identifiers such as GenotypeName as labels, even when numeric."""
    label_words = ("id", "name", "genotype", "date", "month", "year", "shape", "colour", "color", "pattern")
    return [
        column
        for column in data.columns
        if not pd.api.types.is_numeric_dtype(data[column])
        or any(word in column.lower() for word in label_words)
    ]


def show_chart(data: pd.DataFrame, chart_id: int) -> None:
    """Offer interactive visualizations for a query result."""
    if data.empty:
        return

    categories = _category_columns(data)
    all_numeric = list(data.select_dtypes(include="number").columns)
    numeric = [column for column in all_numeric if column not in categories]

    if len(data) == 1 and numeric:
        metrics = st.columns(min(len(numeric), 4))
        for area, column in zip(metrics, numeric[:4]):
            value = data.iloc[0][column]
            area.metric(column, f"{value:,.3f}" if isinstance(value, float) else f"{value:,}")
        return

    with st.expander("Graphical representation", expanded=True):
        chart_type = st.selectbox(
            "Chart type", ("Bar", "Line", "Scatter plot", "Frequency"), key=f"{chart_id}_chart_type"
        )

        if chart_type in ("Bar", "Line"):
            if not categories or not numeric:
                st.info("Bar and line charts need a category column and a numeric measure.")
                return
            x_column = st.selectbox("Category (X-axis)", categories, key=f"{chart_id}_chart_x")
            y_column = st.selectbox("Measure (Y-axis)", numeric, key=f"{chart_id}_chart_y")
            chart_data = data[[x_column, y_column]].dropna().head(50).set_index(x_column)
            if len(data) > 50:
                st.caption("Showing the first 50 rows in the graph; the full result remains in the table.")
            plot_data = chart_data.reset_index()
            mark = "bar" if chart_type == "Bar" else {"type": "line", "point": True}
            st.vega_lite_chart(
                plot_data,
                {
                    "mark": mark,
                    "encoding": {
                        "x": {"field": x_column, "type": "nominal", "title": x_column, "sort": None},
                        "y": {"field": y_column, "type": "quantitative", "title": y_column},
                        "tooltip": [
                            {"field": x_column, "type": "nominal"},
                            {"field": y_column, "type": "quantitative"},
                        ],
                    },
                    "height": 420,
                },
                use_container_width=True,
            )

        elif chart_type == "Scatter plot":
            if len(all_numeric) < 2:
                st.info("A scatter plot needs at least two numeric columns in the query result.")
                return
            x_column = st.selectbox("X-axis", all_numeric, key=f"{chart_id}_scatter_x")
            y_options = [column for column in all_numeric if column != x_column]
            y_column = st.selectbox("Y-axis", y_options, key=f"{chart_id}_scatter_y")
            st.vega_lite_chart(
                data[[x_column, y_column]].dropna().head(500),
                {
                    "mark": {"type": "point", "filled": True, "size": 70},
                    "encoding": {
                        "x": {"field": x_column, "type": "quantitative", "title": x_column},
                        "y": {"field": y_column, "type": "quantitative", "title": y_column},
                        "tooltip": [
                            {"field": x_column, "type": "quantitative"},
                            {"field": y_column, "type": "quantitative"},
                        ],
                    },
                    "height": 420,
                },
                use_container_width=True,
            )

        else:  # Frequency
            if not categories:
                st.info("A frequency graph needs a category column, such as FruitShape or FlowerColour.")
                return
            category = st.selectbox("Category to count", categories, key=f"{chart_id}_frequency_category")
            frequencies = data[category].fillna("Missing").astype(str).value_counts().head(30)
            frequency_data = frequencies.rename_axis(category).reset_index(name="Frequency")
            st.vega_lite_chart(
                frequency_data,
                {
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": category, "type": "nominal", "title": category, "sort": "-y"},
                        "y": {"field": "Frequency", "type": "quantitative"},
                        "tooltip": [
                            {"field": category, "type": "nominal"},
                            {"field": "Frequency", "type": "quantitative"},
                        ],
                    },
                    "height": 420,
                },
                use_container_width=True,
            )
