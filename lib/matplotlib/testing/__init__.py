from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import inspect
import warnings
from contextlib import contextmanager
import shutil
import tempfile

import matplotlib
from matplotlib.cbook import is_string_like, iterable
from matplotlib import rcParams, rcdefaults, use


def _is_list_like(obj):
    """Returns whether the obj is iterable and not a string"""
    return not is_string_like(obj) and iterable(obj)


def is_called_from_pytest():
    """Returns whether the call was done from pytest"""
    return getattr(matplotlib, '_called_from_pytest', False)


def xfail(msg=""):
    """Explicitly fail an currently-executing test with the given message."""
    __tracebackhide__ = True
    if is_called_from_pytest():
        import pytest
        pytest.xfail(msg)
    else:
        from .nose import knownfail
        knownfail(msg)


def skip(msg=""):
    """Skip an executing test with the given message."""
    __tracebackhide__ = True
    if is_called_from_pytest():
        import pytest
        pytest.skip(msg)
    else:
        from nose import SkipTest
        raise SkipTest(msg)


# stolen from pytest
def getrawcode(obj, trycall=True):
    """Return code object for given function."""
    try:
        return obj.__code__
    except AttributeError:
        obj = getattr(obj, 'im_func', obj)
        obj = getattr(obj, 'func_code', obj)
        obj = getattr(obj, 'f_code', obj)
        obj = getattr(obj, '__code__', obj)
        if trycall and not hasattr(obj, 'co_firstlineno'):
            if hasattr(obj, '__call__') and not inspect.isclass(obj):
                x = getrawcode(obj.__call__, trycall=False)
                if hasattr(x, 'co_firstlineno'):
                    return x
        return obj


def copy_metadata(src_func, tgt_func):
    """Replicates metadata of the function. Returns target function."""
    tgt_func.__dict__.update(src_func.__dict__)
    tgt_func.__doc__ = src_func.__doc__
    tgt_func.__module__ = src_func.__module__
    tgt_func.__name__ = src_func.__name__
    if hasattr(src_func, '__qualname__'):
        tgt_func.__qualname__ = src_func.__qualname__
    if not hasattr(tgt_func, 'compat_co_firstlineno'):
        tgt_func.compat_co_firstlineno = getrawcode(src_func).co_firstlineno
    return tgt_func


# stolen from pandas
@contextmanager
def assert_produces_warning(expected_warning=Warning, filter_level="always",
                            clear=None):
    """
    Context manager for running code that expects to raise (or not raise)
    warnings.  Checks that code raises the expected warning and only the
    expected warning. Pass ``False`` or ``None`` to check that it does *not*
    raise a warning. Defaults to ``exception.Warning``, baseclass of all
    Warnings. (basically a wrapper around ``warnings.catch_warnings``).

    >>> import warnings
    >>> with assert_produces_warning():
    ...     warnings.warn(UserWarning())
    ...
    >>> with assert_produces_warning(False):
    ...     warnings.warn(RuntimeWarning())
    ...
    Traceback (most recent call last):
        ...
    AssertionError: Caused unexpected warning(s): ['RuntimeWarning'].
    >>> with assert_produces_warning(UserWarning):
    ...     warnings.warn(RuntimeWarning())
    Traceback (most recent call last):
        ...
    AssertionError: Did not see expected warning of class 'UserWarning'.

    ..warn:: This is *not* thread-safe.
    """
    with warnings.catch_warnings(record=True) as w:

        if clear is not None:
            # make sure that we are clearning these warnings
            # if they have happened before
            # to guarantee that we will catch them
            if not _is_list_like(clear):
                clear = [clear]
            for m in clear:
                try:
                    m.__warningregistry__.clear()
                except:
                    pass

        saw_warning = False
        warnings.simplefilter(filter_level)
        yield w
        extra_warnings = []
        for actual_warning in w:
            if (expected_warning and issubclass(actual_warning.category,
                                                expected_warning)):
                saw_warning = True
            else:
                extra_warnings.append(actual_warning.category.__name__)
        if expected_warning:
            assert saw_warning, ("Did not see expected warning of class %r."
                                 % expected_warning.__name__)
        assert not extra_warnings, ("Caused unexpected warning(s): %r."
                                    % extra_warnings)


def set_font_settings_for_testing():
    rcParams['font.family'] = 'DejaVu Sans'
    rcParams['text.hinting'] = False
    rcParams['text.hinting_factor'] = 8


def setup():
    # The baseline images are created in this locale, so we should use
    # it during all of the tests.
    import locale
    import warnings
    from matplotlib.backends import backend_agg, backend_pdf, backend_svg

    try:
        locale.setlocale(locale.LC_ALL, str('en_US.UTF-8'))
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, str('English_United States.1252'))
        except locale.Error:
            warnings.warn(
                "Could not set locale to English/United States. "
                "Some date-related tests may fail")

    use('Agg', warn=False)  # use Agg backend for these tests

    # These settings *must* be hardcoded for running the comparison
    # tests and are not necessarily the default values as specified in
    # rcsetup.py
    rcdefaults()  # Start with all defaults

    set_font_settings_for_testing()


@contextmanager
def closed_tempfile(suffix='', text=None):
    """
    Context manager which yields the path to a closed temporary file with the
    suffix `suffix`. The file will be deleted on exiting the context. An
    additional argument `text` can be provided to have the file contain `text`.
    """
    with tempfile.NamedTemporaryFile(
        'w+t', suffix=suffix, delete=False
    ) as test_file:
        file_name = test_file.name
        if text is not None:
            test_file.write(text)
            test_file.flush()
    yield file_name
    shutil.rmtree(file_name, ignore_errors=True)
