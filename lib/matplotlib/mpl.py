"""
.. note:: Deprecated in 1.3
"""
import warnings
from matplotlib import MatplotlibDeprecationWarning as mplDeprecation
warnings.warn(
    "matplotlib.mpl is deprecated and will be removed in version 1.4."
    "Please use `import matplotlib as mpl` instead", mplDeprecation)
from matplotlib import artist
from matplotlib import axis
from matplotlib import axes
from matplotlib.utils import _cbook
from matplotlib import collections
from matplotlib import colors
from matplotlib import colorbar
from matplotlib import contour
from matplotlib import dates
from matplotlib import figure
from matplotlib import finance
from matplotlib import font_manager
from matplotlib import image
from matplotlib import legend
from matplotlib import lines
from matplotlib import mlab
from matplotlib import cm
from matplotlib import patches
from matplotlib import quiver
from matplotlib import rcParams
from matplotlib import table
from matplotlib import text
from matplotlib import ticker
from matplotlib import transforms
from matplotlib import units
from matplotlib import widgets
