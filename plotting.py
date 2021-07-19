import math
from bokeh.plotting import figure, curdoc
from bokeh.io import show, output_notebook
from bokeh.models import (
    ColumnDataSource,
    CrosshairTool,
    Select,
    CustomJS,
)
from bokeh.models.tools import HoverTool
from bokeh.transform import transform, dodge
from bokeh.layouts import layout, column, row
from bokeh.embed import components
import numpy as np


def plotPareto(df_mc, df_res, exp_vol, exp_ret, idx):
    """
    This function will plot pareto front
    """
    # filter df_mc
    df_mc = df_mc[df_mc["EV"] <= df_res["EV"].max()]
    p = figure(plot_width=600, plot_height=300)
    # add a circle renderer with a size, color, and alpha
    source0 = ColumnDataSource(df_mc * 100)
    source = ColumnDataSource(df_res * 100)
    p.circle(
        x="EV",
        y="ER",
        source=source0,
        size=2,
        color="grey",
        alpha=0.95,
        name="Monte Carlo Simulation",
        legend_label="Monte Carlo Simulation",
    )
    p.circle(
        x="EV",
        y="ER",
        source=source,
        size=5,
        color="red",
        alpha=0.9,
        name="Pareto Front",
        legend_label="Pareto Solution",
    )
    if idx != -1:
        p.scatter(
            df_res.loc[idx, "EV"] * 100,
            df_res.loc[idx, "ER"] * 100,
            size=15,
            color="blue",
            alpha=0.9,
            name="Selected Solution",
            legend_label="Selected Solution",
            marker="triangle",
        )
    p.scatter(
        exp_vol * 100,
        exp_ret * 100,
        size=15,
        color="magenta",
        line_color="black",
        alpha=0.9,
        name="Current Position",
        legend_label="Current Position",
        marker="square",
    )
    hover = HoverTool(
        tooltips=[("Index", "@index"), ("Return", "@ER"), ("Volitility", "@EV")],
        names=["Pareto Front"],
        mode="mouse",
    )
    p.tools.append(hover)
    p.xaxis.axis_label = "Expected Volitility (%)"
    p.yaxis.axis_label = "Expected Return (%)"
    p.legend.location = "bottom_right"
    crosshair = CrosshairTool(dimensions="both")
    p.add_tools(crosshair)
    p.axis.axis_label_text_font_size = "11pt"
    p.axis.axis_label_text_font_style = "bold italic"
    return p


def plotWeights(unformatted_df, idx):
    stocks = unformatted_df["Stock"].tolist()
    if idx == -1:
        weights = ["Portfolio Weights (%)"]
        data = {
            "stocks": stocks,
            "Portfolio Weights (%)": unformatted_df["Portfolio Weights (%)"].tolist(),
        }
        source = ColumnDataSource(data=data)
        # find maximum
        mx = (
            int(np.array(unformatted_df["Portfolio Weights (%)"].tolist()).max() / 10)
            * 10
            + 10
        )
        p = figure(
            x_range=stocks, y_range=(0, mx), title="", plot_width=600, plot_height=300
        )
        p.vbar(
            x=dodge("stocks", 0, range=p.x_range),
            top="Portfolio Weights (%)",
            width=0.2,
            source=source,
            color="magenta",
            legend_label="Portfolio",
        )
    else:
        weights = ["Portfolio Weights (%)", "Weights of Selected Solution (%)"]
        data = {
            "stocks": stocks,
            "Portfolio Weights (%)": unformatted_df["Portfolio Weights (%)"].tolist(),
            "Weights of Selected Solution (%)": unformatted_df[
                "Weights of Selected Solution (%)"
            ].tolist(),
        }
        source = ColumnDataSource(data=data)
        mx = mx = (
            int(
                np.array(
                    unformatted_df["Portfolio Weights (%)"].tolist()
                    + unformatted_df["Weights of Selected Solution (%)"].tolist()
                ).max()
                / 10
            )
            * 10
            + 10
        )
        p = figure(
            x_range=stocks, y_range=(0, mx), title="", plot_width=600, plot_height=300
        )
        p.vbar(
            x=dodge("stocks", -0.15, range=p.x_range),
            top="Portfolio Weights (%)",
            width=0.2,
            source=source,
            color="magenta",
            legend_label="Portfolio",
        )
        p.vbar(
            x=dodge("stocks", 0.15, range=p.x_range),
            top="Weights of Selected Solution (%)",
            width=0.2,
            source=source,
            color="blue",
            legend_label="Selected",
        )
    p.xaxis.axis_label = "Stock"
    p.yaxis.axis_label = "Weight (%)"
    p.x_range.range_padding = 0.1
    p.xgrid.grid_line_color = None
    p.legend.location = "top_left"
    p.legend.orientation = "horizontal"
    p.xaxis.major_label_orientation = math.pi / 2
    p.add_layout(p.legend[0], "above")
    p.axis.axis_label_text_font_size = "11pt"
    p.axis.axis_label_text_font_style = "bold italic"
    return p


def get_layout(stocks_histories):
    """
    This function prepares plot of stock daily time histories
    """
    # create a dictionary of the date
    data = dict()
    for key, value in stocks_histories.items():
        key_date = key + "_date"
        value_date = value.index.tolist()
        key_open = key + "_open"
        value_open = value["Open"].tolist()
        key_close = key + "_close"
        value_close = value["Close"].tolist()
        key_high = key + "_high"
        value_high = value["High"].tolist()
        key_low = key + "_low"
        value_low = value["Low"].tolist()
        data[key_date] = value_date
        data[key_open] = value_open
        data[key_close] = value_close
        data[key_high] = value_high
        data[key_low] = value_low
    # add active cases
    data["active_date"] = data[key_date]
    data["active_open"] = data[key_open]
    data["active_close"] = data[key_close]
    data["active_high"] = data[key_high]
    data["active_low"] = data[key_low]
    # add inc and dec cases
    inc_date = []
    inc_open = []
    inc_close = []
    dec_date = []
    dec_open = []
    dec_close = []
    for i in range(len(data["active_open"])):
        if data["active_open"][i] < data["active_close"][i]:
            inc_date.append(data["active_date"][i])
            inc_open.append(data["active_open"][i])
            inc_close.append(data["active_close"][i])
            dec_date.append(math.nan)
            dec_open.append(math.nan)
            dec_close.append(math.nan)
        else:
            dec_date.append(data["active_date"][i])
            dec_open.append(data["active_open"][i])
            dec_close.append(data["active_close"][i])
            inc_date.append(math.nan)
            inc_open.append(math.nan)
            inc_close.append(math.nan)
    data["inc_date"] = inc_date
    data["inc_open"] = inc_open
    data["inc_close"] = inc_close
    data["dec_date"] = dec_date
    data["dec_open"] = dec_open
    data["dec_close"] = dec_close
    source = ColumnDataSource(data=data)
    select = Select(
        title="Select a ticker:", value=key, options=list(stocks_histories.keys())
    )
    select.js_on_change(
        "value",
        CustomJS(
            args=dict(source=source, select=select),
            code="""
      var val_date = select.value + '_date'
      var val_open = select.value + '_open'
      var val_close = select.value + '_close'
      var val_high = select.value + '_high'
      var val_low = select.value + '_low'
      source.data['active_date'] = source.data[val_date]
      source.data['active_open'] = source.data[val_open]
      source.data['active_close'] = source.data[val_close]
      source.data['active_high'] = source.data[val_high]
      source.data['active_low'] = source.data[val_low]
      var inc_date = []
      var inc_open = []
      var inc_close = []
      var dec_date = []
      var dec_open = []
      var dec_close = []
      for (var i=0; i<source.data['active_open'].length; i++){
      if (source.data['active_open'][i] < source.data['active_close'][i]) {
      inc_date.push(source.data['active_date'][i])
      inc_open.push(source.data['active_open'][i])
      inc_close.push(source.data['active_close'][i])
      dec_date.push(Number.NaN)
      dec_open.push(Number.NaN)
      dec_close.push(Number.NaN)
      } else {
      dec_date.push(source.data['active_date'][i])
      dec_open.push(source.data['active_open'][i])
      dec_close.push(source.data['active_close'][i])
      inc_date.push(Number.NaN)
      inc_open.push(Number.NaN)
      inc_close.push(Number.NaN)
      }
      }
      source.data['inc_date'] = inc_date
      source.data['inc_open'] = inc_open
      source.data['inc_close'] = inc_close
      source.data['dec_date'] = dec_date
      source.data['dec_open'] = dec_open
      source.data['dec_close'] = dec_close
      source.change.emit()
      """,
        ),
    )
    p = figure(x_axis_type="datetime", plot_width=600, plot_height=300)
    p.segment(
        "active_date",
        "active_low",
        "active_date",
        "active_high",
        source=source,
        color="grey",
    )
    w = 12 * 60 * 60 * 1000  # half day in ms
    p.vbar(
        "inc_date",
        w,
        "inc_open",
        "inc_close",
        source=source,
        fill_color="green",
        line_color="green",
    )
    p.vbar(
        "dec_date",
        w,
        "dec_open",
        "dec_close",
        source=source,
        fill_color="red",
        line_color="red",
    )
    p.xaxis.major_label_orientation = math.pi / 4
    p.grid.grid_line_alpha = 0.3
    p.xaxis.axis_label = "Date"
    p.yaxis.axis_label = "Price ($)"
    p.axis.axis_label_text_font_size = "11pt"
    p.axis.axis_label_text_font_style = "bold italic"
    crosshair = CrosshairTool(dimensions="both")
    p.add_tools(crosshair)
    p.sizing_mode = "scale_width"
    layout = row(column(select, width=100), p)
    layout.sizing_mode = "scale_width"
    return layout


def plotEvEr(df_statistics):
    stocks = df_statistics.index.tolist()
    """This function will plot expected return and expected volitility of each stock in the portfolio"""
    data = {
        "stocks": stocks,
        "ER": np.array(df_statistics["ER"].tolist()) * 100,
        "EV": np.array(df_statistics["Volitility"].tolist()) * 100,
    }
    source = ColumnDataSource(data=data)
    # find maximum
    mx = int(
        (
            np.array(
                df_statistics["ER"].tolist() + df_statistics["Volitility"].tolist()
            )
            .max()
            .round(1)
            + 0.1
        )
        * 100
    )
    # find minimum
    mn = int(
        (
            np.array(
                df_statistics["ER"].tolist() + df_statistics["Volitility"].tolist()
            )
            .min()
            .round(1)
            - 0.1
        )
        * 100
    )
    p = figure(
        x_range=stocks, y_range=(mn, mx), title="", plot_width=600, plot_height=300
    )
    p.vbar(
        x=dodge("stocks", -0.15, range=p.x_range),
        top="ER",
        width=0.2,
        source=source,
        color="grey",
        legend_label="Expected Return",
    )
    p.vbar(
        x=dodge("stocks", 0.15, range=p.x_range),
        top="EV",
        width=0.2,
        source=source,
        color="orange",
        legend_label="Expected Volitility",
    )
    p.xaxis.axis_label = "Stock"
    p.yaxis.axis_label = "Weight (%)"
    p.x_range.range_padding = 0.1
    p.xgrid.grid_line_color = None
    p.legend.location = "top_left"
    p.legend.orientation = "horizontal"
    p.xaxis.major_label_orientation = math.pi / 2
    p.add_layout(p.legend[0], "above")
    p.axis.axis_label_text_font_size = "11pt"
    p.axis.axis_label_text_font_style = "bold italic"

    return p
