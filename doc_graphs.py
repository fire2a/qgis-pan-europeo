#!python3
"""
module to make sample matplotlib graphs for the documentation
showcasing all utility functions
                    "min-max",
                    "max-min",
                    "bi-piecewise-linear values",
                    "bi-piecewise-linear percentage",
                    "step up value",
                    "step up percentage",
                    "step down value",
                    "step down percentage",
"""
import matplotlib.pyplot as plt
import numpy as np


def utility_functions(fig):
    """keep manually in sync with pan_batido/view/view.py:utility_functions()"""
    # fig, ax = plt.subplots(1, 3)
    fig.suptitle("Utility Functions")
    fig.supxlabel("observations")
    fig.supylabel("utility")
    fig.set_layout_engine("constrained")
    ax = [fig.add_subplot(131), fig.add_subplot(132), fig.add_subplot(133)]

    # min-max & max-min
    x = np.linspace(0, 1, 100)
    y1 = x
    y2 = 1 - x
    ax[0].plot(x, y1, label="min-max")
    ax[0].plot(x, y2, label="max-min")
    ax[0].legend(["min-max", "max-min"])
    ax[0].set_xticks([0, 1])
    ax[0].set_xticklabels(["min", "max"])

    # step up
    y3 = np.piecewise(x, [x < 0.25, x >= 0.25], [0, 1])
    y4 = np.piecewise(x, [x >= 0.75, x < 0.75], [0, 1])
    ax[1].plot(x, y3, label="step up")
    ax[1].plot(x, y4, label="step down")
    ax[1].legend(["step up", "step down"])
    ax[1].set_xticks([0, 0.25, 0.75, 1])
    ax[1].set_xticklabels(["", "threshold", "threshold", ""])

    # bi-piecewise-linear values
    y5 = np.piecewise(x, [x < 0.25, (x >= 0.25) & (x < 0.75), x >= 0.75], [0, lambda x: (x - 0.25) / 0.5, 1])
    y6 = np.piecewise(x, [x < 0.25, (x >= 0.25) & (x < 0.75), x >= 0.75], [1, lambda x: (-x + 0.75) / 0.5, 0])
    ax[2].plot(x, y5, label="bi-piecewise-linear a<b")
    ax[2].plot(x, y6, label="bi-piecewise-linear a>b")
    ax[2].legend(["bi-piecewise-linear a<b", "bi-piecewise-linear a>b"])
    ax[2].set_xticks([0, 0.25, 0.75, 1])
    ax[2].set_xticklabels(["", "a", "b", ""])


def special_case(fig):
    # fig, ax = plt.subplots()
    ax = fig.add_subplot(111)
    x = np.linspace(0, 1, 100)
    y = np.piecewise(x, [x < 0.75, x >= 0.75], [lambda x: x / 0.75, 1])
    ax.plot(x, y, label="bi-piecewise-linear a=0 & b")
    ax.set_xticks([0, 0.75])
    ax.set_xticklabels(["a=0", "b"])
    ax.legend(["bi-piecewise-linear a=0 & b"])
    fig.supxlabel("ordered observations")
    fig.supylabel("utility")
    # plt.show()


if __name__ == "__main__":
    fig = plt.figure()
    utility_functions(fig)
    plt.show()
    del fig
    fig = plt.figure()
    special_case(fig)
    plt.show()
    del fig
