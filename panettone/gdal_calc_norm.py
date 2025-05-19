#!python
# fmt: off
"""
<pre><code>
<!-- BEGIN_ARGPARSE_DOCSTRING -->
usage: gdal_calc_norm.py [-h] [-i INFILE] [-o OUTFILE]  
                         [-m {minmax,maxmin,stepup,stepdown,bipiecewiselinear,bipiecewiselinear_percent,stepdown_percent,stepup_percent}]  
                         [-min MINIMUM] [-max MAXIMUM] [-n [NODATAVALUE]]  
                         [-f FORMAT]  
                         [-t {Byte,UInt16,Int16,UInt32,Int32,UInt64,Int64,Float32,Float64,CInt16,CInt32,CFloat32,CFloat64}]  
                         [-p min_x max_y max_x min_y] [-r]  
                         [params ...]  

Raster normalization utility, wrapping on osgeo_utils.gdal_calc with a set of
predefined normalization methods. Run `gdal_calc.py --help` for more
information.

positional arguments:
  params                Float numbers according to the normalizing method.
                        None: for minmax, maxmin; One for stepup, stepdown;
                        Two for bipiecewiselinear, bipiecewiselinear_percent,
                        see also method (default: None)

options:
  -h, --help            show this help message and exit
  -i INFILE, --infile INFILE
                        Input file (default: infile.tif)
  -o OUTFILE, --outfile OUTFILE
                        Output file (default: outfile.tif)
  -m {minmax,maxmin,stepup,stepdown,bipiecewiselinear,bipiecewiselinear_percent,stepdown_percent,stepup_percent}, --method {minmax,maxmin,stepup,stepdown,bipiecewiselinear,bipiecewiselinear_percent,stepdown_percent,stepup_percent}
                        Method to normalize the input, see also params
                        (default: minmax)
  -min MINIMUM, --minimum MINIMUM
                        Minimun value for minmax/maxmin (else the value is
                        calculated from the WHOLE input raster). (default:
                        None)
  -max MAXIMUM, --maximum MAXIMUM
                        Maximum value for minmax/maxmin (else the value is
                        calculated from the WHOLE input raster). (default:
                        None)
  -n [NODATAVALUE], --NoDataValue [NODATAVALUE]
                        output nodata value (send none for default datatype
                        specific, see `from osgeo_utils.gdal_calc import
                        DefaultNDVLookup`) (default: 0)
  -f FORMAT, --format FORMAT
                        Output format (send null to infer from file, see `from
                        osgeo_utils.auxiliary.util import GetOutputDriverFor`)
                        (default: GTiff)
  -t {Byte,UInt16,Int16,UInt32,Int32,UInt64,Int64,Float32,Float64,CInt16,CInt32,CFloat32,CFloat64}, --type {Byte,UInt16,Int16,UInt32,Int32,UInt64,Int64,Float32,Float64,CInt16,CInt32,CFloat32,CFloat64}
                        Output datatype (default: Float32)
  -p min_x max_y max_x min_y, --projwin min_x max_y max_x min_y
                        An optional list of 4 coordinates defining the
                        projection window, if not provided the whole raster is
                        calculated (default: None)
  -r, --return_dataset  Return dataset (for scripting -additional keyword
                        arguments are passed to gdal_calc.Calc) instead of
                        return code (default: False)

documentation at
https://fire2a.github.io/fire2a-lib/fire2a/gdal_calc_norm.html
<!-- END_ARGPARSE_DOCSTRING -->

Sample script usage:
    from fire2a.raster.gdal_calc_norm import main
    ds = main(["-r", ... other keyword arguments are passed to gdal_calc.Calc

function osgeo_utils.gdal_calc.Calc(
    calc: Union[str, Sequence[str]],
    outfile: Union[str, os.PathLike, NoneType] = None,
    NoDataValue: Optional[numbers.Number] = None,
    type: Union[int, str, NoneType] = None,
    format: Optional[str] = None,
    creation_options: Optional[Sequence[str]] = None,
    allBands: str = '',
    overwrite: bool = False,
    hideNoData: bool = False,
    projectionCheck: bool = False,
    color_table: Union[osgeo.gdal.ColorTable,
    ForwardRef('ColorPalette'), str, os.PathLike, Sequence[str], NoneType] = None,
    extent: Optional[osgeo_utils.auxiliary.extent_util.Extent] = None,
    projwin: Union[Tuple, osgeo_utils.auxiliary.rectangle.GeoRectangle, NoneType] = None,
    user_namespace: Optional[Dict] = None,
    debug: bool = False,
    quiet: bool = False, **input_files)

/usr/bin/gdal_calc.py
/usr/lib/python3/dist-packages/osgeo_utils/gdal_calc.py
</code></pre>
"""
# fmt: on
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from osgeo.gdal import Dataset, GA_ReadOnly, Open
from osgeo_utils.auxiliary.util import GetOutputDriverFor
from osgeo_utils.gdal_calc import Calc, GDALDataTypeNames


def calc(
    func,
    outfile="outfile.tif",
    infile="infile.tif",
    band=1,
    NoDataValue=None,
    overwrite=True,
    type="Float32",
    format="GTiff",
    projwin=None,
    minimum=None,
    maximum=None,
    threshold=None,
    a=None,
    b=None,
    r=None,
    **kwargs,
) -> Dataset:
    """This is the wrapper function for the gdal_calc.Calc utility.

    Although the normalization functions are symbolic strings defined in the main, passed as the `func` argument. Make sure to check them before using this function directly.

    All extra keyword arguments are passed to the gdal_calc.Calc function."""
    if isinstance(infile, Path):
        infile = str(infile)
    if isinstance(outfile, Path):
        outfile = str(outfile)
    if "method" in kwargs:
        if kwargs["method"] in ["minmax", "maxmin", "bipiecewiselinear_percent", "stepup_percent", "stepdown_percent"]:
            if minimum is None and maximum is None:
                minimum, maximum = get_file_minmax(infile)
                print(f"{minimum=}, {maximum=}")
            if minimum is None:
                minimum, _ = get_file_minmax(infile)
                print(f"{minimum=}")
            if maximum is None:
                _, maximum = get_file_minmax(infile)
                print(f"{maximum=}")
        # drop before passing to Calc
        del kwargs["method"]
    # if not projwin:
    #     info = locals().get("info", read_raster(infile, data=False)[1])
    #     projwin, _ = get_projwin(info["Transform"], info["RasterXSize"], info["RasterYSize"])
    #     print(f"{projwin=}")

    # get a the parameter values of the calc function
    code_obj = func.__code__
    local_var_names = code_obj.co_varnames[: code_obj.co_nlocals]
    func_vars = []
    for var in local_var_names:
        func_vars += [locals().get(var)]
    if "r" in local_var_names:
        func_vars[-1] = (maximum - minimum) / 100
    print(f"{dict(zip(local_var_names,func_vars))=}")
    print(f"{local_var_names=}")
    print(f"{func_vars=}")

    dataset = Calc(
        calc=func(*func_vars),
        outfile=outfile,
        A=infile,
        A_band=band,
        NoDataValue=NoDataValue,
        overwrite=overwrite,
        type=type,
        format=format,
        projwin=projwin,
        **kwargs,
    )
    dataset.FlushCache()

    return dataset


def arg_parser(argv=None):
    """Parse arguments list"""
    from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, ArgumentTypeError
    from typing import Union

    def float_or_none(NoDataValue: str) -> Union[float, str]:
        if NoDataValue.lower() == "none":
            return NoDataValue

        try:
            return float(NoDataValue)
        except ValueError:
            msg = f"wtf Invalid float value for NoDataValue: {NoDataValue}"
            raise ArgumentTypeError(msg)

    parser = ArgumentParser(
        description="Raster normalization utility, wrapping on osgeo_utils.gdal_calc with a set of predefined normalization methods. Run `gdal_calc.py --help` for more information.",
        formatter_class=ArgumentDefaultsHelpFormatter,
        epilog="documentation at https://fire2a.github.io/fire2a-lib/fire2a/raster/gdal_calc_norm.html",
    )
    parser.add_argument(
        "params",
        nargs="*",
        type=float,
        help="Float numbers according to the normalizing method. None: for minmax, maxmin; One for stepup, stepdown; Two for bipiecewiselinear, bipiecewiselinear_percent, see also method",
    )
    parser.add_argument("-i", "--infile", help="Input file", type=Path, default="infile.tif")
    parser.add_argument("-o", "--outfile", help="Output file", type=Path, default="outfile.tif")
    parser.add_argument(
        "-m",
        "--method",
        help="Method to normalize the input, see also params",
        type=str,
        choices=[
            "minmax",
            "maxmin",
            "stepup",
            "stepdown",
            "bipiecewiselinear",
            "bipiecewiselinear_percent",
            "stepdown_percent",
            "stepup_percent",
        ],
        default="minmax",
    )
    parser.add_argument(
        "-min",
        "--minimum",
        help="Minimun value for minmax/maxmin (else the value is calculated from the WHOLE input raster).",
        type=float,
    )
    parser.add_argument(
        "-max",
        "--maximum",
        help="Maximum value for minmax/maxmin (else the value is calculated from the WHOLE input raster).",
        type=float,
    )
    parser.add_argument(
        "-n",
        "--NoDataValue",
        help="Output NoDataValue (Defaults to 0 to be weight summed). To indicate not setting a NoDataValue use --NoDataValue=none (GDAL >= 3.3) 'none' value will indicate not setting a NoDataValue.",
        type=float_or_none,
        metavar="value",
        nargs="?",
        default=0.0,
    )
    parser.add_argument(
        "-f",
        "--format",
        help="Output format (send null to infer from file, see `from osgeo_utils.auxiliary.util import GetOutputDriverFor`)",
        type=str,
        default="GTiff",
    )

    parser.add_argument(
        "-t", "--type", help="Output datatype", type=str, default="Float32", choices=list(map(str, GDALDataTypeNames))
    )
    parser.add_argument(
        "-p",
        "--projwin",
        nargs=4,
        type=float,
        metavar=("min_x", "max_y", "max_x", "min_y"),
        help="An optional list of 4 coordinates defining the projection window, if not provided the whole raster is calculated",
    )
    parser.add_argument(
        "-r",
        "--return_dataset",
        help="Return dataset (for scripting -additional keyword arguments are passed to gdal_calc.Calc) instead of return code",
        action="store_true",
    )
    args = parser.parse_args(argv)
    args.projwin = tuple(args.projwin) if args.projwin else None
    if not args.infile.is_file():
        parser.error("Input file does not exist")
    if args.format is None:
        args.format = GetOutputDriverFor(args.outfile)
    return args


def main(argv=None):
    """
    <pre><code>
    minmax: (A-minimum)/(maximum - minimum)
    maxmin: (A-maximum)/(minimum - maximum)
    stepup: 0*(A<threshold)+1*(A>=threshold)
    stepdown: 1*(A<threshold)+0*(A>=threshold)
    bipiecewiselinear: (A-a)/(b-a) then "0*(A<0)+1*(A>1)"
    bipiecewiselinear_percent: (A-a*r)/(b*r-a*r) then "0*(A<0)+1*(A>1)"
    stepup_percent: 0*(A<threshold*r)+1*(A>=threshold*r)
    stepdown_percent: 1*(A<threshold*r)+0*(A>=threshold*r)

    r : relative delta : data.max() - data.min() / 100
    </code></pre>
    """
    if argv is sys.argv:
        argv = sys.argv[1:]
    args = arg_parser(argv)

    print(f"{args=}")

    if args.method == "minmax":
        del args.params
        func = lambda minimum, maximum: f"(A-{minimum})/({maximum} - {minimum})"
        ds = calc(func, **vars(args))
    elif args.method == "maxmin":
        del args.params
        func = lambda minimum, maximum: f"(A-{maximum})/({minimum} - {maximum})"
        ds = calc(func, **vars(args))
    elif args.method == "stepup":
        threshold = args.params[0]
        del args.params
        func = lambda threshold: f"0*(A<{threshold})+1*(A>={threshold})"
        ds = calc(func, **vars(args), threshold=threshold)
    elif args.method == "stepdown":
        threshold = args.params[0]
        del args.params
        func = lambda threshold: f"1*(A<{threshold})+0*(A>={threshold})"
        ds = calc(func, **vars(args), threshold=threshold)
    elif args.method == "bipiecewiselinear":
        a = args.params[0]
        b = args.params[1]
        del args.params

        keep = args.outfile
        args.outfile = Path(NamedTemporaryFile(suffix=".tif", delete=False).name)
        print(f"{args=}")

        func = lambda a, b: f"(A-{a})/({b}-{a})"
        ds = calc(func, **vars(args), a=a, b=b)

        args.infile = args.outfile
        args.outfile = keep
        print(f"{args=}")

        func = lambda: "0*(A<0)+1*(A>1)+A*((0<=A)&(A<=1))"
        ds = calc(func, **vars(args))
    elif args.method == "bipiecewiselinear_percent":
        """
        rela_delta = data.max() - data.min() / 100
        real_a = rela_delta * a
        real_b = rela_delta * b
        data = (data - real_a) / (real_b - real_a)
        """
        a = args.params[0]
        b = args.params[1]
        del args.params

        keep = args.outfile
        args.outfile = Path(NamedTemporaryFile(suffix=".tif", delete=False).name)
        print(f"{args=}")

        func = lambda a, b, r: f"(A-{a*r})/({b*r}-{a*r})"
        ds = calc(func, **vars(args), a=a, b=b, r=0)

        args.infile = args.outfile
        args.outfile = keep
        print(f"{args=}")

        func = lambda: "0*(A<0)+1*(A>1)+A*((0<=A)&(A<=1))"
        ds = calc(func, **vars(args))
    elif args.method == "stepup_percent":
        threshold = args.params[0]
        del args.params
        func = lambda threshold, r: f"0*(A<{threshold*r})+1*(A>={threshold*r})"
        ds = calc(func, **vars(args), threshold=threshold, r=0)
    elif args.method == "stepdown_percent":
        threshold = args.params[0]
        del args.params
        func = lambda threshold, r: f"1*(A<{threshold*r})+0*(A>={threshold*r})"
        ds = calc(func, **vars(args), threshold=threshold, r=0)
    """
    elif args.method == "":
        del args.method
        func = lambda : f""
        ds = maxmin(func, **vars(args))
    """

    if args.return_dataset:
        return ds

    if isinstance(ds, Dataset):
        return 0
    return 1


def get_file_minmax(filename, force=True):
    # try:
    dataset = Open(filename, GA_ReadOnly)
    # except RuntimeError as e:
    #     if "not recognized as a supported file format" in str(e):
    #         raise FileNotFoundError("not recognized as a supported file format " + filename)
    if dataset is None:
        raise FileNotFoundError(filename)
    raster_band = dataset.GetRasterBand(1)
    rmin = raster_band.GetMinimum()
    rmax = raster_band.GetMaximum()
    if not rmin or not rmax or force:
        (rmin, rmax) = raster_band.ComputeRasterMinMax(True)
    return rmin, rmax


if __name__ == "__main__":
    sys.exit(main(sys.argv))
