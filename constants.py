# python3
"""
UTILITY_FUNCTIONS :
    no cambiar orden
    'percent' en nombre desactiva actualizar rangos min max segun selected feature
"""
TAG = "PanEuropeo"

UTILITY_FUNCTIONS = [
    {
        "name": "bipiecewiselinear_percent",
        "description": "bi-piecewise-linear percentages",
        "numvars": 2,
        "params": {"a=0": {"min": 0, "max": 100, "value": 10}, "b=1": {"min": 0, "max": 100, "value": 50}},
    },
    {
        "name": "bipiecewiselinear",
        "description": "bi-piecewise-linear values",
        "numvars": 2,
        "params": {"a=0": {"min": 0, "max": 100, "value": 50}, "b=1": {"min": 0, "max": 100, "value": 50}},
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
    {"name": "minmax", "description": "min-max", "numvars": 0, "params": {}},
    {"name": "maxmin", "description": "max-min", "numvars": 0, "params": {}},
]

METHODS = [method["name"] for method in UTILITY_FUNCTIONS]

# for uf in UTILITY_FUNCTIONS:
#     print(f"Utility function: {uf['name']}")
#     for text, values in uf["params"].items():
#         print(text, values["min"], values["value"], values["max"])
