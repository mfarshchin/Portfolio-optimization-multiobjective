from flask import Flask, render_template, request, redirect, jsonify
from optimization import *
from plotting import *

app = Flask(__name__)
portfolio = {}
optimization_results = []
histories = []
df_stat = []
Selected_idx = [-1]


@app.route("/Home", methods=["GET", "POST"])
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("Home.html")
    else:
        userInputs = []
        Selected_idx = [-1]
        form = request.form
        for key, value in form.items():
            if key.startswith("cell"):
                userInputs.append(value)
        portfolio.clear()
        for i in range(0, len(userInputs), 2):
            portfolio[userInputs[i].strip()] = int(userInputs[i + 1].strip())
        return render_template("Redirect.html")  # this page will show


@app.route("/Progress")
def Progress():
    # perform optimization
    tmp, stk_hst, df_st = process_portfolio(portfolio)
    optimization_results.append(tmp)
    print(optimization_results)
    histories.append(stk_hst)
    df_stat.append(df_st)
    return jsonify("")


@app.route("/Results", methods=["GET", "POST"])
def Results():
    if request.method == "GET":
        out = optimization_results[-1]
        if len(Selected_idx) == 1:
            idx = -1
        else:
            idx = Selected_idx.pop()
        df, unformatted_df = Solutions(
            out["df_res"],
            out["X"],
            portfolio,
            out["allocation"],
            out["allocated_weights"],
            idx,
        )

        # add optimization plot to the Results page
        plot = plotPareto(
            out["df_mc"], out["df_res"], out["exp_vol"], out["exp_ret"], idx
        )
        plot.sizing_mode = "scale_width"
        plot_script, plot_div = components(plot)

        # add weights plot to the page
        w_plot = plotWeights(unformatted_df, idx)
        w_plot.sizing_mode = "scale_width"
        w_plot_script, w_plot_div = components(w_plot)

        # add stock price history layout plot
        stocks_histories = histories[-1]
        # print(stocks_histories.keys())
        n_layout = get_layout(stocks_histories)
        n_layout_script, n_layout_div = components(n_layout)

        # add plot of expected returns and expected volitilities for stocks in the portfolio
        df_statistics = df_stat[-1]
        e_plot = plotEvEr(df_statistics)
        e_plot.sizing_mode = "scale_width"
        e_plot_script, e_plot_div = components(e_plot)

        kwargs = {
            "plot_script": plot_script,
            "plot_div": plot_div,
            "w_plot_script": w_plot_script,
            "w_plot_div": w_plot_div,
            "n_layout_script": n_layout_script,
            "n_layout_div": n_layout_div,
            "e_plot_script": e_plot_script,
            "e_plot_div": e_plot_div,
        }

        kwargs["title"] = ""
        # add data frame data to the Results page
        kwargs["tables"] = [df.to_html(classes="data")]
        kwargs["titles"] = df.columns.values
        kwargs["row_data"] = list(df.values.tolist())
        kwargs["text_selected"] = idx

        return render_template("Results.html", **kwargs)
    else:
        Selected_idx.append(int(request.form["pareto_idx"].strip()))
        out = optimization_results[-1]
        idx = Selected_idx.pop()
        df, unformatted_df = Solutions(
            out["df_res"],
            out["X"],
            portfolio,
            out["allocation"],
            out["allocated_weights"],
            idx,
        )
        # add optimization plot to the Results page
        plot = plotPareto(
            out["df_mc"], out["df_res"], out["exp_vol"], out["exp_ret"], idx
        )
        plot.sizing_mode = "scale_width"
        plot_script, plot_div = components(plot)

        # add weights plot to the page
        w_plot = plotWeights(unformatted_df, idx)
        w_plot.sizing_mode = "scale_width"
        w_plot_script, w_plot_div = components(w_plot)

        # add stock price history layout plot
        stocks_histories = histories[-1]
        n_layout = get_layout(stocks_histories)
        n_layout_script, n_layout_div = components(n_layout)

        # add plot of expected returns and expected volitilities for stocks in the portfolio
        df_statistics = df_stat[-1]
        e_plot = plotEvEr(df_statistics)
        e_plot.sizing_mode = "scale_width"
        e_plot_script, e_plot_div = components(e_plot)

        kwargs = {
            "plot_script": plot_script,
            "plot_div": plot_div,
            "w_plot_script": w_plot_script,
            "w_plot_div": w_plot_div,
            "n_layout_script": n_layout_script,
            "n_layout_div": n_layout_div,
            "e_plot_script": e_plot_script,
            "e_plot_div": e_plot_div,
        }

        kwargs["title"] = ""
        # add data frame data to the Results page
        kwargs["tables"] = [df.to_html(classes="data")]
        kwargs["titles"] = df.columns.values
        kwargs["row_data"] = list(df.values.tolist())
        kwargs[
            "text_selected"
        ] = idx  # f'Index of currently selected solution is {idx} and this point is shown in the below graph with a blue circle'

        return render_template("Results.html", **kwargs)


@app.route("/About")
def About():
    return render_template("About.html")


@app.route("/Tickers")
def Tickers():
    return render_template("Tickers.html")


if __name__ == "__main__":
    app.run()
