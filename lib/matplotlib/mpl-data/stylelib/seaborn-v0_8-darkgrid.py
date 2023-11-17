import ast
from pathlib import Path


__mpl_style__ = {
    **ast.literal_eval(Path(__file__).with_name("_seaborn-v0_8-common.py").read_text()),
    "axes.grid": True,
    "axes.facecolor": "#EAEAF2",
    "axes.edgecolor": "white",
    "axes.linewidth": 0,
    "grid.color": "white",
    "xtick.major.size": 0,
    "ytick.major.size": 0,
    "xtick.minor.size": 0,
    "ytick.minor.size": 0,
}
