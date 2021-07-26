from datetime import datetime, timedelta
import yfinance as yf
import numpy as np
import pandas as pd
from pymoo.model.problem import FunctionalProblem
from pymoo.algorithms.nsga2 import NSGA2
from pymoo.factory import get_sampling, get_crossover, get_mutation
from pymoo.factory import get_termination
from pymoo.optimize import minimize
from pymoo.model.problem import ConstraintsAsPenaltyProblem
from functools import reduce


def gethistory(stock):
    """
    Get stock histories for the last 365 days (day close prices)
    """
    ticker = yf.Ticker(stock)
    tmp = ticker.history(start=(datetime.now() - timedelta(365)).date(), interval="1d")
    tmp.index = pd.to_datetime(tmp.index, utc=True)
    tmp.index = tmp.index.tz_convert("US/Eastern")
    return tmp[["Close"]].rename(columns={"Close": stock}), tmp


def getPercentChange(portfolio, df):
    """
    Calculate log of daily percentage change
    """
    tmp = df.copy()
    for item in portfolio:
        # Log of percentage change
        tmp[item] = tmp[item].pct_change().apply(lambda x: np.log(1 + x))
    return tmp


def getStats(portfolio, df_pct):
    """
    Get statistics, correlation and covariance matrices. Variabnce of log of percentage change
    """
    tmp = pd.DataFrame()
    tmp["Mean"] = df_pct.mean()
    tmp["Var"] = df_pct.var()
    tmp["Std"] = df_pct.std()
    tmp["Volitility"] = tmp["Std"].apply(lambda x: x * np.sqrt(df_pct.shape[0]))
    tmp["ER"] = tmp["Mean"].apply(lambda x: x * df_pct.shape[0])
    Corr = df_pct.corr()
    Cov = df_pct.cov() * df_pct.shape[0]
    return tmp, Corr, Cov


def expected_return(weights, df_stat):
    """
    Calculate expected portfolio return
    """
    return np.sum(df_stat["ER"] * weights)


def expected_vol(weights, Cov):
    """
    Calculate expected portfolio volitility
    """
    return np.sqrt(np.dot(weights.T, np.dot(Cov, weights)))


def getMC(portfolio, df_pct, df_stat, Cov, n=5000):
    """
    MonteCarlo simulation
    """
    W = []  # weights
    ER = []  # expected return
    EV = []  # expected volitility
    SR = []  # sharpe
    for i in range(n):
        # generate weights
        weights = np.array(np.random.random(len(portfolio)))
        weights = weights / np.sum(weights)
        W.append(weights)
        # ER
        er = expected_return(weights, df_stat)
        ER.append(er)
        # EV
        ev = expected_vol(weights, Cov)
        EV.append(ev)
        SR.append(er / ev)

    df_mc = pd.DataFrame({"EV": EV, "ER": ER, "SR": SR})
    return df_mc


def Optimize(portfolio, df_stat, Cov, population=100, generations=1000, verbose=False):
    """
    Multiobjective optimization
    """
    # Define the problem
    def expected_return(x):
        return -np.sum(df_stat["ER"] * x)

    def expected_vol(x):
        return np.sqrt(np.dot(x.T, np.dot(Cov, x)))

    objs = [expected_return, expected_vol]

    constr_eq = [lambda x: 1 - x.sum()]
    problem = FunctionalProblem(
        len(portfolio),
        objs,
        constr_eq=constr_eq,
        constr_eq_eps=2e-02,
        xl=np.zeros(len(portfolio)),
        xu=np.ones(len(portfolio)),
    )
    # Define algorithm
    algorithm = NSGA2(
        pop_size=population,
        n_offsprings=30,
        sampling=get_sampling("real_random"),
        crossover=get_crossover("real_sbx", prob=0.9, eta=15),
        mutation=get_mutation("real_pm", eta=20),
        eliminate_duplicates=True,
    )
    # Termination criterion
    termination = get_termination("n_gen", generations)
    # perform optimization
    print("Optimization in progress ...!")
    res = minimize(
        problem, algorithm, termination, seed=1, save_history=True, verbose=verbose
    )
    # return results
    print("Optimization finished!")
    df_res = pd.DataFrame(res.F, columns=["ER", "EV"])
    df_res["ER"] = df_res["ER"] * -1
    df_res["SR"] = df_res["ER"] / df_res["EV"]
    return df_res, res.X


def process_portfolio(portfolio):
    """
    Process the portfolio and optimize
    """
    df_list = []
    df_list_full = {}
    for key, val in portfolio.items():
        tmp, tmp_full = gethistory(key)
        df_list.append(tmp)
        df_list_full[key] = tmp_full
    df = reduce(lambda x, y: pd.merge(x, y, on="Date"), df_list)

    # find total money invested in each stock
    allocation = []
    for key, value in portfolio.items():
        allocation.append(value * df.iloc[-1][key])

    df_pct = getPercentChange(portfolio, df)

    df_stat, Corr, Cov = getStats(portfolio, df_pct)

    # current weights
    allocated_weights = np.array(allocation) / np.array(allocation).sum()
    # Expected return
    exp_ret = expected_return(allocated_weights, df_stat)
    # Expected volitility
    exp_vol = expected_vol(allocated_weights, Cov)
    # Sharpe ratio
    SR = exp_ret / exp_vol
    # Monte carlo simulation
    df_mc = getMC(portfolio, df_pct, df_stat, Cov, n=5000)
    df_res, X = Optimize(
        portfolio, df_stat, Cov, population=100, generations=1000, verbose=False
    )
    output = {
        "df_mc": df_mc,
        "df_res": df_res,
        "exp_vol": exp_vol,
        "exp_ret": exp_ret,
        "df_pct": df_pct,
        "df_stat": df_pct,
        "Corr": Corr,
        "Cov": Cov,
        "X": X,
        "allocation": allocation,
        "allocated_weights": allocated_weights,
    }
    return (output, df_list_full, df_stat)


def Solutions(df_res, X, portfolio, allocation, allocated_weights, idx):

    if idx == -1:
        main_df = pd.DataFrame(
            {
                "Stock": portfolio.keys(),
                "Quantity": portfolio.values(),
                "Last Price ($)": (
                    np.array(allocation) / np.array(list(portfolio.values()))
                ).round(2),
                "Value ($)": np.array(allocation).astype(int),
                "Portfolio Weights (%)": np.array(allocated_weights * 100).round(1),
            }
        )
        unformatted_df = main_df.copy()
        main_df["Value ($)"] = ["$ " + str(i) for i in main_df["Value ($)"].tolist()]
        main_df["Last Price ($)"] = [
            "$ " + str(i) for i in main_df["Last Price ($)"].tolist()
        ]
        main_df["Portfolio Weights (%)"] = [
            "% " + str(i) for i in main_df["Portfolio Weights (%)"].tolist()
        ]
    else:
        # add selected solution
        selected_solution = X[idx] / X[idx].sum()
        # Sharpe solution
        main_df = pd.DataFrame(
            {
                "Stock": portfolio.keys(),
                "Quantity": portfolio.values(),
                "Last Price ($)": (
                    np.array(allocation) / np.array(list(portfolio.values()))
                ).round(2),
                "Value ($)": np.array(allocation).astype(int),
                "Portfolio Weights (%)": np.array(allocated_weights * 100).round(1),
                "Weights of Selected Solution (%)": np.array(
                    selected_solution * 100
                ).round(1),
                "Values of Selected Solution ($)": np.array(
                    selected_solution * sum(allocation)
                ).astype(int),
            }
        )
        unformatted_df = main_df.copy()
        main_df["Value ($)"] = ["$ " + str(i) for i in main_df["Value ($)"].tolist()]
        main_df["Last Price ($)"] = [
            "$ " + str(i) for i in main_df["Last Price ($)"].tolist()
        ]
        main_df["Values of Selected Solution ($)"] = [
            "$ " + str(i) for i in main_df["Values of Selected Solution ($)"].tolist()
        ]
        main_df["Portfolio Weights (%)"] = [
            "% " + str(i) for i in main_df["Portfolio Weights (%)"].tolist()
        ]
        main_df["Weights of Selected Solution (%)"] = [
            "% " + str(i) for i in main_df["Weights of Selected Solution (%)"].tolist()
        ]
    return main_df, unformatted_df

