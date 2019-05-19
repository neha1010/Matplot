import contextlib
from distutils.version import StrictVersion
import functools
import inspect
import os
from pathlib import Path
import shutil
import string
import sys
import unittest
import warnings

import matplotlib as mpl
import matplotlib.style
import matplotlib.units
import matplotlib.testing
from matplotlib import cbook
from matplotlib import ft2font
from matplotlib import pyplot as plt
from matplotlib import ticker
from .compare import compare_images, make_test_filename, _skip_if_uncomparable
from .exceptions import ImageComparisonFailure


@contextlib.contextmanager
def _cleanup_cm():
    orig_units_registry = matplotlib.units.registry.copy()
    try:
        with warnings.catch_warnings(), matplotlib.rc_context():
            yield
    finally:
        matplotlib.units.registry.clear()
        matplotlib.units.registry.update(orig_units_registry)
        plt.close("all")


class CleanupTestCase(unittest.TestCase):
    """A wrapper for unittest.TestCase that includes cleanup operations."""
    @classmethod
    def setUpClass(cls):
        cls._cm = _cleanup_cm().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._cm.__exit__(None, None, None)


def cleanup(style=None):
    """
    A decorator to ensure that any global state is reset before
    running a test.

    Parameters
    ----------
    style : str, dict, or list, optional
        The style(s) to apply.  Defaults to ``["classic",
        "_classic_test_patch"]``.
    """

    # If cleanup is used without arguments, *style* will be a callable, and we
    # pass it directly to the wrapper generator.  If cleanup if called with an
    # argument, it is a string naming a style, and the function will be passed
    # as an argument to what we return.  This is a confusing, but somewhat
    # standard, pattern for writing a decorator with optional arguments.

    def make_cleanup(func):
        if inspect.isgeneratorfunction(func):
            @functools.wraps(func)
            def wrapped_callable(*args, **kwargs):
                with _cleanup_cm(), matplotlib.style.context(style):
                    yield from func(*args, **kwargs)
        else:
            @functools.wraps(func)
            def wrapped_callable(*args, **kwargs):
                with _cleanup_cm(), matplotlib.style.context(style):
                    func(*args, **kwargs)

        return wrapped_callable

    if callable(style):
        result = make_cleanup(style)
        # Default of mpl_test_settings fixture and image_comparison too.
        style = ["classic", "_classic_test_patch"]
        return result
    else:
        return make_cleanup


def check_freetype_version(ver):
    if ver is None:
        return True

    if isinstance(ver, str):
        ver = (ver, ver)
    ver = [StrictVersion(x) for x in ver]
    found = StrictVersion(ft2font.__freetype_version__)

    return ver[0] <= found <= ver[1]


def _checked_on_freetype_version(required_freetype_version):
    import pytest
    reason = ("Mismatched version of freetype. "
              "Test requires '%s', you have '%s'" %
              (required_freetype_version, ft2font.__freetype_version__))
    return pytest.mark.xfail(
        not check_freetype_version(required_freetype_version),
        reason=reason, raises=ImageComparisonFailure, strict=False)


def remove_ticks_and_titles(figure):
    figure.suptitle("")
    null_formatter = ticker.NullFormatter()
    for ax in figure.get_axes():
        ax.set_title("")
        ax.xaxis.set_major_formatter(null_formatter)
        ax.xaxis.set_minor_formatter(null_formatter)
        ax.yaxis.set_major_formatter(null_formatter)
        ax.yaxis.set_minor_formatter(null_formatter)
        try:
            ax.zaxis.set_major_formatter(null_formatter)
            ax.zaxis.set_minor_formatter(null_formatter)
        except AttributeError:
            pass


def _raise_on_image_difference(expected, actual, tol):
    __tracebackhide__ = True

    err = compare_images(expected, actual, tol, in_decorator=True)
    if err:
        for key in ["actual", "expected"]:
            err[key] = os.path.relpath(err[key])
        raise ImageComparisonFailure(
            'images not close (RMS %(rms).3f):\n\t%(actual)s\n\t%(expected)s '
             % err)


def _make_image_comparator(func=None,
                           baseline_images=None, *, extension=None, tol=0,
                           remove_text=False, savefig_kwargs=None):
    """
    Image comparison base helper.

    This helper provides *just* the comparison-related functionality and avoids
    any code that would be specific to any testing framework.
    """
    if func is None:
        return functools.partial(
            _make_image_comparator,
            baseline_images=baseline_images, extension=extension, tol=tol,
            remove_text=remove_text, savefig_kwargs=savefig_kwargs)

    if savefig_kwargs is None:
        savefig_kwargs = {}

    baseline_dir, result_dir = _image_directories(func)

    def _copy_baseline(baseline):
        baseline_path = baseline_dir / baseline
        orig_expected_path = baseline_path.with_suffix(f'.{extension}')
        if extension == 'eps' and not orig_expected_path.exists():
            orig_expected_path = orig_expected_path.with_suffix('.pdf')
        expected_fname = make_test_filename(
            result_dir / orig_expected_path.name, 'expected')
        try:
            # os.symlink errors if the target already exists.
            with contextlib.suppress(OSError):
                os.remove(expected_fname)
            try:
                os.symlink(orig_expected_path, expected_fname)
            except OSError:  # On Windows, symlink *may* be unavailable.
                shutil.copyfile(orig_expected_path, expected_fname)
        except OSError as err:
            raise ImageComparisonFailure(
                f"Missing baseline image {expected_fname} because the "
                f"following file cannot be accessed: "
                f"{orig_expected_path}") from err
        return expected_fname

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        __tracebackhide__ = True
        _skip_if_uncomparable(extension)

        func(*args, **kwargs)

        fignums = plt.get_fignums()
        assert len(fignums) == len(baseline_images), (
            "Test generated {} images but there are {} baseline images"
            .format(len(fignums), len(baseline_images)))
        for baseline_image, fignum in zip(baseline_images, fignums):
            fig = plt.figure(fignum)
            if remove_text:
                remove_ticks_and_titles(fig)
            actual_path = ((result_dir / baseline_image)
                           .with_suffix(f'.{extension}'))
            kwargs = savefig_kwargs.copy()
            if extension == 'pdf':
                kwargs.setdefault('metadata',
                                  {'Creator': None, 'Producer': None,
                                   'CreationDate': None})
            fig.savefig(actual_path, **kwargs)
            expected_path = _copy_baseline(baseline_image)
            _raise_on_image_difference(expected_path, actual_path, tol)

    return wrapper


def _pytest_image_comparison(baseline_images, extensions, tol,
                             freetype_version, remove_text, savefig_kwargs,
                             style):
    """
    Decorate function with image comparison for pytest.

    This function creates a decorator that wraps a figure-generating function
    with image comparison code. Pytest can become confused if we change the
    signature of the function, so we indirectly pass anything we need via the
    `mpl_image_comparison_parameters` fixture and extra markers.
    """
    import pytest

    def decorator(func):
        @functools.wraps(func)
        # Parameter indirection; see docstring above and comment below.
        @pytest.mark.usefixtures('mpl_image_comparison_parameters')
        @pytest.mark.parametrize('extension', extensions)
        @pytest.mark.baseline_images(baseline_images)
        # END Parameter indirection.
        @pytest.mark.style(style)
        @_checked_on_freetype_version(freetype_version)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            __tracebackhide__ = True
            # Parameter indirection:
            # This is hacked on via the mpl_image_comparison_parameters fixture
            # so that we don't need to modify the function's real signature for
            # any parametrization. Modifying the signature is very very tricky
            # and likely to confuse pytest.
            baseline_images, extension = func.parameters

            matplotlib.testing.set_font_settings_for_testing()
            comparator = _make_image_comparator(
                func,
                baseline_images=baseline_images, extension=extension, tol=tol,
                remove_text=remove_text, savefig_kwargs=savefig_kwargs)
            comparator(*args, **kwargs)

        return wrapper

    return decorator


def image_comparison(baseline_images, extensions=None, tol=0,
                     freetype_version=None, remove_text=False,
                     savefig_kwarg=None,
                     # Default of mpl_test_settings fixture and cleanup too.
                     style=("classic", "_classic_test_patch")):
    """
    Compare images generated by the test with those specified in
    *baseline_images*, which must correspond, else an `ImageComparisonFailure`
    exception will be raised.

    Parameters
    ----------
    baseline_images : list or None
        A list of strings specifying the names of the images generated by
        calls to `.Figure.savefig`.

        If *None*, the test function must use the ``baseline_images`` fixture,
        either as a parameter or with `pytest.mark.usefixtures`. This value is
        only allowed when using pytest.

    extensions : None or list of str
        The list of extensions to test, e.g. ``['png', 'pdf']``.

        If *None*, defaults to all supported extensions: png, pdf, and svg.

        When testing a single extension, it can be directly included in the
        names passed to *baseline_images*.  In that case, *extensions* must not
        be set.

        In order to keep the size of the test suite from ballooning, we only
        include the ``svg`` or ``pdf`` outputs if the test is explicitly
        exercising a feature dependent on that backend (see also the
        `check_figures_equal` decorator for that purpose).

    tol : float, default: 0
        The RMS threshold above which the test is considered failed.

    freetype_version : str or tuple
        The expected freetype version or range of versions for this test to
        pass.

    remove_text : bool
        Remove the title and tick text from the figure before comparison.  This
        is useful to make the baseline images independent of variations in text
        rendering between different versions of FreeType.

        This does not remove other, more deliberate, text, such as legends and
        annotations.

    savefig_kwarg : dict
        Optional arguments that are passed to the savefig method.

    style : str, dict, or list
        The optional style(s) to apply to the image test. The test itself
        can also apply additional styles if desired. Defaults to ``["classic",
        "_classic_test_patch"]``.
    """

    if baseline_images is not None:
        # List of non-empty filename extensions.
        baseline_exts = [*filter(None, {Path(baseline).suffix[1:]
                                        for baseline in baseline_images})]
        if baseline_exts:
            if extensions is not None:
                raise ValueError(
                    "When including extensions directly in 'baseline_images', "
                    "'extensions' cannot be set as well")
            if len(baseline_exts) > 1:
                raise ValueError(
                    "When including extensions directly in 'baseline_images', "
                    "all baselines must share the same suffix")
            extensions = baseline_exts
            baseline_images = [  # Chop suffix out from baseline_images.
                Path(baseline).stem for baseline in baseline_images]
    if extensions is None:
        # Default extensions to test, if not set via baseline_images.
        extensions = ['png', 'pdf', 'svg']
    return _pytest_image_comparison(
        baseline_images=baseline_images, extensions=extensions, tol=tol,
        freetype_version=freetype_version, remove_text=remove_text,
        savefig_kwargs=savefig_kwarg, style=style)


def check_figures_equal(*, extensions=("png", "pdf", "svg"), tol=0):
    """
    Decorator for test cases that generate and compare two figures.

    The decorated function must take two keyword arguments, *fig_test*
    and *fig_ref*, and draw the test and reference images on them.
    After the function returns, the figures are saved and compared.

    This decorator should be preferred over `image_comparison` when possible in
    order to keep the size of the test suite from ballooning.

    Parameters
    ----------
    extensions : list, default: ["png", "pdf", "svg"]
        The extensions to test.
    tol : float
        The RMS threshold above which the test is considered failed.

    Examples
    --------
    Check that calling `.Axes.plot` with a single argument plots it against
    ``[0, 1, 2, ...]``::

        @check_figures_equal()
        def test_plot(fig_test, fig_ref):
            fig_test.subplots().plot([1, 3, 5])
            fig_ref.subplots().plot([0, 1, 2], [1, 3, 5])

    """
    ALLOWED_CHARS = set(string.digits + string.ascii_letters + '_-[]()')
    KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
    def decorator(func):
        import pytest

        _, result_dir = _image_directories(func)
        old_sig = inspect.signature(func)

        if not {"fig_test", "fig_ref"}.issubset(old_sig.parameters):
            raise ValueError("The decorated function must have at least the "
                             "parameters 'fig_ref' and 'fig_test', but your "
                             f"function has the signature {old_sig}")

        @pytest.mark.parametrize("ext", extensions)
        def wrapper(*args, **kwargs):
            ext = kwargs['ext']
            _skip_if_uncomparable(ext)
            if 'ext' not in old_sig.parameters:
                kwargs.pop('ext')
            request = kwargs['request']
            if 'request' not in old_sig.parameters:
                kwargs.pop('request')

            file_name = "".join(c for c in request.node.name
                                if c in ALLOWED_CHARS)
            try:
                fig_test = plt.figure("test")
                fig_ref = plt.figure("reference")
                func(*args, fig_test=fig_test, fig_ref=fig_ref, **kwargs)
                test_image_path = result_dir / (file_name + "." + ext)
                ref_image_path = result_dir / (file_name + "-expected." + ext)
                fig_test.savefig(test_image_path)
                fig_ref.savefig(ref_image_path)
                _raise_on_image_difference(
                    ref_image_path, test_image_path, tol=tol
                )
            finally:
                plt.close(fig_test)
                plt.close(fig_ref)

        parameters = [
            param
            for param in old_sig.parameters.values()
            if param.name not in {"fig_test", "fig_ref"}
        ]
        if 'ext' not in old_sig.parameters:
            parameters += [inspect.Parameter("ext", KEYWORD_ONLY)]
        if 'request' not in old_sig.parameters:
            parameters += [inspect.Parameter("request", KEYWORD_ONLY)]
        new_sig = old_sig.replace(parameters=parameters)
        wrapper.__signature__ = new_sig

        # reach a bit into pytest internals to hoist the marks from
        # our wrapped function
        new_marks = getattr(func, "pytestmark", []) + wrapper.pytestmark
        wrapper.pytestmark = new_marks

        return wrapper

    return decorator


def _image_directories(func):
    """
    Compute the baseline and result image directories for testing *func*.

    For test module ``foo.bar.test_baz``, the baseline directory is at
    ``foo/bar/baseline_images/test_baz`` and the result directory at
    ``$(pwd)/result_images/test_baz``.  The result directory is created if it
    doesn't exist.
    """
    module_path = Path(sys.modules[func.__module__].__file__)
    baseline_dir = module_path.parent / "baseline_images" / module_path.stem
    result_dir = Path().resolve() / "result_images" / module_path.stem
    result_dir.mkdir(parents=True, exist_ok=True)
    return baseline_dir, result_dir
