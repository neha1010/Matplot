import os

import pytest

import matplotlib as mpl
from matplotlib import _c_internal_utils
import matplotlib.pyplot as plt
try:
    from matplotlib.backends import _macosx
except ImportError:
    pytest.skip("These are mac only tests", allow_module_level=True)


pytestmark = [
    pytest.mark.skipif(not _c_internal_utils.display_is_valid(),
                       reason="Display is unavailable")
]


@pytest.mark.backend('macosx')
def test_cached_renderer():
    # Make sure that figures have an associated renderer after
    # a fig.canvas.draw() call
    fig = plt.figure(1)
    fig.canvas.draw()
    assert fig.canvas.get_renderer()._renderer is not None

    fig = plt.figure(2)
    fig.draw_without_rendering()
    assert fig.canvas.get_renderer()._renderer is not None


@pytest.mark.backend('macosx')
def test_savefig_rcparam(monkeypatch, tmp_path):

    def new_choose_save_file(title, directory, filename):
        # Replacement function instead of opening a GUI window
        # Make a new directory for testing the update of the rcParams
        assert directory == str(tmp_path)
        os.makedirs(f"{directory}/test")
        return f"{directory}/test/{filename}"

    monkeypatch.setattr(_macosx, "choose_save_file", new_choose_save_file)
    fig = plt.figure()
    with mpl.rc_context({"savefig.directory": tmp_path}):
        fig.canvas.toolbar.save_figure()
        # Check the saved location got created
        save_file = f"{tmp_path}/test/{fig.canvas.get_default_filename()}"
        assert os.path.exists(save_file)

        # Check the savefig.directory rcParam got updated because
        # we added a subdirectory "test"
        assert mpl.rcParams["savefig.directory"] == f"{tmp_path}/test"


@pytest.mark.backend('macosx')
def test_ipython():
    from matplotlib.testing import ipython_in_subprocess
    ipython_in_subprocess("osx", {(8, 24): "macosx", (7, 0): "MacOSX"})
