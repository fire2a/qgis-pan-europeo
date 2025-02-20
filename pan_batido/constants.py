TAG = "PanEuropeo"

UTILITY_FUNCTIONS = [
    {"name": "minmax", "description": "min-max", "numvars": 0, "params": {}},
    {"name": "maxmin", "description": "max-min", "numvars": 0, "params": {}},
    {
        "name": "bipiecewiselinear",
        "description": "bi-piecewise-linear values",
        "numvars": 2,
        "params": {"a": {"min": 0, "max": 100, "value": 50}, "b": {"min": 0, "max": 100, "value": 50}},
    },
    {
        "name": "bipiecewiselinear_percent",
        "description": "bi-piecewise-linear percentages",
        "numvars": 2,
        "params": {"a": {"min": 0, "max": 100, "value": 50}, "b": {"min": 0, "max": 100, "value": 50}},
    },
    {
        "name": "stepup",
        "description": "step up value",
        "numvars": 1,
        "params": {"threshold": {"min": 0, "max": 100, "value": 50}},
    },
    {
        "name": "stepup_percent",
        "description": "step up percentage",
        "numvars": 1,
        "params": {"threshold": {"min": 0, "max": 100, "value": 50}},
    },
    {
        "name": "stepdown",
        "description": "step down value",
        "numvars": 1,
        "params": {"threshold": {"min": 0, "max": 100, "value": 50}},
    },
    {
        "name": "stepdown_percent",
        "description": "step down percentage",
        "numvars": 1,
        "params": {"threshold": {"min": 0, "max": 100, "value": 50}},
    },
]

METHODS = [method["name"] for method in UTILITY_FUNCTIONS]
