import plotly.graph_objects as go

from aml_etl.dashboard.theme import (
    BORDER_COLOR,
    FAINT_COLOR,
    FONT_FAMILY,
    GRID_COLOR,
    MUTED_COLOR,
    TEXT_COLOR,
)

TRANSPARENT = "rgba(0,0,0,0)"
FIGURE_HEIGHT = 300


def style_figure(figure: go.Figure) -> go.Figure:
    figure.update_layout(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font={"family": FONT_FAMILY, "size": 12, "color": MUTED_COLOR},
        margin={"l": 48, "r": 12, "t": 12, "b": 40},
        height=FIGURE_HEIGHT,
        showlegend=False,
        separators=", ",
        hoverlabel={"font": {"family": FONT_FAMILY, "color": TEXT_COLOR}, "bgcolor": "#ffffff"},
        bargap=0.25,
    )
    axis = {
        "gridcolor": GRID_COLOR,
        "linecolor": BORDER_COLOR,
        "zeroline": False,
        "tickfont": {"size": 11, "color": FAINT_COLOR},
        "title_font": {"size": 11, "color": FAINT_COLOR},
    }
    figure.update_xaxes(showgrid=False, **axis)
    figure.update_yaxes(showgrid=True, **axis)
    return figure
