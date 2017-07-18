"""
This is artist.py implemented with Traits
"""


from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import six
from collections import OrderedDict, namedtuple

import re
import warnings
import inspect
import numpy as np
import matplotlib
import matplotlib.cbook as cbook
from matplotlib.cbook import mplDeprecation
from matplotlib import docstring, rcParams
from matplotlib.transforms import (Bbox, IdentityTransform, TransformedBbox,
                         TransformedPatchPath, TransformedPath, Transform)
from matplotlib.path import Path
from functools import wraps
from contextlib import contextmanager

from traits import TraitProxy, Perishable, ClipPathTrait

#this is for sticky_edges but im thinking we can just use a tuple trait...?
_XYPair = namedtuple("_XYPair", "x y")

def allow_rasterization(draw):
    """
    Decorator for Artist.draw method. Provides routines
    that run before and after the draw call. The before and after functions
    are useful for changing artist-dependent renderer attributes or making
    other setup function calls, such as starting and flushing a mixed-mode
    renderer.
    """
    @contextmanager
    def with_rasterized(artist, renderer):

        if artist.get_rasterized():
            renderer.start_rasterizing()

        if artist.get_agg_filter() is not None:
            renderer.start_filter()

        try:
            yield
        finally:
            if artist.get_agg_filter() is not None:
                renderer.stop_filter(artist.get_agg_filter())

            if artist.get_rasterized():
                renderer.stop_rasterizing()

    # the axes class has a second argument inframe for its draw method.
    @wraps(draw)
    def draw_wrapper(artist, renderer, *args, **kwargs):
        with with_rasterized(artist, renderer):
            return draw(artist, renderer, *args, **kwargs)

    draw_wrapper._supports_rasterization = True
    return draw_wrapper


class Artist(HasTraits):

    aname = Unicode('Artist')
    zorder = Int(default_value = 0)
    #_prop_order = dict(color=-1)
    prop_order = Dict() #asked thomas question about this asstribute
    # pchanged = Bool(default_value = False)
    stale = Bool(default_value = True)
    stale_callback = Callable(allow_none = True, default_value = True)
    axes = Instance('matplotlib.axes.Axes', allow_none = True, default_value = None)
    figure = Instance('matplotlib.figure.Figure', allow_none = True, default_value = None)
    transform = Instance('matplotlib.transform.Transform', allow_none = True, default_value = None)
    transformSet = Bool(default_value = False )
    visible = Bool(default_value = True)
    animated = Bool(default_value = False)
    alpha = Float(default_value = None ,allow_none = True)
    clipbox = Instance('matplotlib.transforms.Bbox', allow_none = True, default_value = None)
    #clippath
    clipon = Boolean(default_value = True)
    label = Unicode(allow_none = True, default_value = '')
    picker = Union(Float, Boolean, Callable, allow_none = True, default_value = None)
    contains = List(default_value=None)
    rasterized = Perishable(Boolean(allow_none = True, default_value = None))
    agg_filter = Unicode(allow_none = True, default_value = None) #set agg_filter function
    mouseover = Boolean(default_value = False)
    eventson = Boolean(default_value = False)
    oid = Int(allow_none = True, default_value = 0)
    propobservers = Dict(default_value = {}) #this may or may not work o/w leave alone and see what happens
    url = Unicode(allow_none = True,default_value = None)
    gid = Unicode(allow_none = True, default_value = None)
    snap = Perishable(Boolean(allow_none = True, default_value = None))
    sketch = Tuple(Float(), Float(), Float(), default_value = rcParams['path.sketch'])
    path_effects = List(Instance('matplotlib.patheffect._Base'), default_value = rcParams['path.effects'])
    #_XYPair = namedtuple("_XYPair", "x y")
    #sticky_edges is a tuple with lists of floats
    #the first element of this tuple represents x
    #and the second element of sticky_edges represents y
    sticky_edges = Tuple(List(trait=Float()), List(trait=Float()))

    #the axes bounding box in display space
    #TO DO: window_extent -> Bbox([[0, 0], [0, 0]])

"""
_______________________________________________________________________________
"""
    #
    # #pchanged default
    # @default("pchanged")
    # def pchanged_default(self):
    #     print("generating default stale value")
    #     return True
    # #pchanged validate
    # @validate("pchanged")
    # def pchanged_validate(self, proposal):
    #     print("cross validating %r" % proposal.value")
    #     return proposal.value
    # #pchanged observer
    # @observe("pchanged", type = change)
    # def pchanged_observe(self, change):
    #     print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #stale default
    @default("stale")
    def stale_default(self):
        print("generating default stale value")
        return True
    #stale validate
    @validate("stale")
    def stale_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #stale observer
    @observe("stale", type = change)
    def stale_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #stale_callback default
    @default("stale_callback")
    def stale_callback_default(self):
        print("generating default stale_callback value")
        return None
    #stale_callback validate
    @validate("stale_callback")
    def stale_callback_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #stale_callback observer
    @observe("stale_callback", type = change)
    def stale_callback_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #axes default
    @default("axes")
    def axes_default(self):
        print("generating default axes value")
        return None
    #axes validate
    @validate("axes")
    def axes_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #axes observer
    @observe("axes", type = change)
    def axes_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #figure default
    @default("figure")
    def figure_default(self):
        print("generating default figure value")
        return None
    #figure validate
    @validate("figure")
    def figure_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #figure observer
    @observe("figure", type = change)
    def figure_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #transform default
    @default("transform")
    def transform_default(self):
        print("generating default transform value")
        return None
    #transform validate
    @validate("transform")
    def transform_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #transform observer
    @observe("transform", type = change)
    def transform_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #transformSet default
    @default("transformSet")
    def transformSet_default(self):
        print("generating default transformSet value")
        return False
    #transformSet validate
    @validate("transformSet")
    def transformSet_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #transformSet observer
    @observe("transformSet", type = change)
    def transformSet_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #visible default
    @default("visible")
    def visible_default(self):
        print("generating default visible value")
        return True
    #visible validate
    @validate("visible")
    def visible_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #visible observer
    @observe("visible", type = change)
    def visible_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #animated default
    @default("animated")
    def animated_default(self):
        print("generating default animated value")
        return False
    #animated validate
    @validate("animated")
    def animated_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #animated observer
    @observe("animated", type = change)
    def animated_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #alpha default
    @default("alpha")
    def alpha_default(self):
        print("generating default alpha value")
        return None
    #alpha validate
    @validate("alpha")
    def alpha_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #alpha observer
    @observe("alpha", type = change)
    def alpha_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #clipbox default
    @default("clipbox")
    def clipbox_default(self):
        print("generating default clipbox value")
        return None
    #clipbox validate
    @validate("clipbox")
    def clipbox_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #clipbox observer
    @observe("clipbox", type = change)
    def clipbox_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #To do: create either a clippath trait or modify the get and set functions
    #for now i have comments down for default, validate and observer decortors
    #clippath default
    @default("clippath")
    def clippath_default(self):
        print("generating default clippath value")
        return None
    #clippath validate
    @validate("clippath")
    def clippath_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #clippath observer
    @observe("clippath", type = change)
    def clippath_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #clipon default
    @default("clipon")
    def clipon_default(self):
        print("generating default clipon value")
        return True
    #clipon validate
    @validate("clipon")
    def clipon_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #clipon observer
    @observe("clipon", type = change)
    def clipon_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #label default
    @default("label")
    def label_default(self):
        print("generating default label value")
        return None
    #label validate
    @validate("label")
    def label_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #label observer
    @observe("label", type = change)
    def label_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #picker default
    @default("picker")
    def picker_default(self):
        print("generating default picker value")
        return None
    #picker validate
    @validate("picker")
    def picker_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #picker observer
    @observe("picker", type = change)
    def picker_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #contains default
    @default("contains")
    def contains_default(self):
        print("generating default contains value")
        return None
    #contains validate
    @validate("contains")
    def contains_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #contains observer
    @observe("contains", type = change)
    def contains_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #rasterized default
    @default("rasterized")
    def rasterized_default(self):
        print("generating default rasterized value")
        return None
    #rasterized validate
    @validate("rasterized")
    def rasterized_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #rasterized observer
    @observe("rasterized", type = change)
    def rasterized_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #agg_filter default
    @default("agg_filter")
    def agg_filter_default(self):
        print("generating default agg_filter value")
        return None
    #agg_filter validate
    @validate("agg_filter")
    def agg_filter_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #agg_filter observer
    @observe("agg_filter", type = change)
    def agg_filter_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #mouseover default
    @default("mouseover")
    def mouseover_default(self):
        print("generating default mouseover value")
        return False
    #mouseover validate
    @validate("mouseover")
    def mouseover_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #mouseover observer
    @observe("mouseover", type = change)
    def mouseover_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #eventson default
    @default("eventson")
    def eventson_default(self):
        print("generating default eventson value")
        return False
    #eventson validate
    @validate("eventson")
    def eventson_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #eventson observer
    @observe("eventson", type = change)
    def eventson_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #oid default
    @default("oid")
    def oid_default(self):
        print("generating default oid (observer id) value")
        return 0
    #oid validate
    @validate("oid")
    def oid_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #oid observer
    @observe("oid", type = change)
    def oid_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #propobservers default
    @default("propobservers")
    def propobservers_default(self):
        print("generating default propobservers value")
        return {}
    #propobservers validate
    @validate("propobservers")
    def propobservers_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #propobservers observer
    @observe("propobservers", type = change)
    def propobservers_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #url default
    @default("url")
    def url_default(self):
        print("generating default url value")
        return None
    #url validate
    @validate("url")
    def url_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #url observer
    @observe("url", type = change)
    def url_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #gid default
    @default("gid")
    def gid_default(self):
        print("generating default gid (group id) value")
        return None
    #gid validate
    @validate("gid")
    def gid_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #gid observer
    @observe("gid", type = change)
    def gid_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #snap default
    @default("snap")
    def snap_default(self):
        print("generating default snap value")
        return None
    #snap validate
    @validate("snap")
    def snap_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #snap observer
    @observe("snap", type = change)
    def snap_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    """
    This may not work, I may or may not have to work around rcParams['path.sketch']
    but I am not sure yet
    """

    #sketch default
    @default("sketch")
    def sketch_default(self):
        print("generating default sketch value")
        return rcParams['path.sketch']
    #sketch validate
    @validate("sketch")
    def sketch_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #sketch observer
    @observe("sketch", type = change)
    def sketch_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

        """
        same note as sketch:
        This may not work, I may or may not have to work around rcParams['path.effects']
        but I am not sure yet
        """

    #path_effects default
    @default("path_effects")
    def path_effects_default(self):
        print("generating default path_effects value")
        return rcParams['path.effects']
    #path_effects validate
    @validate("path_effects")
    def path_effects_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #path_effects observer
    @observe("path_effects", type = change)
    def path_effects_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    """
    Note: This may or may not work, I have to work around the
    _XYPair([], [])
    """

    #sticky_edges default
    @default("sticky_edges")
    def sticky_edges_default(self):
        print("generating default sticky_edges value")
        #(x,y) where x & yare both List(trait=Float())
        #Tuple(List(trait=Float()), List(trait=Float()))
        return ([], [])
    #sticky_edges validate
    @validate("sticky_edges")
    def sticky_edges_validate(self, proposal):
        print("cross validating %r" % proposal.value")
        return proposal.value
    #sticky_edges observer
    @observe("sticky_edges", type = change)
    def sticky_edges_observe(self, change):
        print("observed a change from %r to %r" % (change.old, change.new))

"""
_______________________________________________________________________________
"""

    #ARTIST FUNCTIONS

    def __init__(self):
        pass

    def __getstate__(self):
        pass

"""
These following functions are copied and pasted from the original Artist class.
This is because I feel as if they can be altered to their respective traits.
"""

    def have_units(self):
        ax = self.axes
        if ax is None or ax.xaxis is None:
            return False
        return ax.xaxis.have_units() or ax.yaxis.have_units()

    def convert_xunits(self, x):
        """For artists in an axes, if the xaxis has units support,
        convert *x* using xaxis unit type
        """
        ax = getattr(self, 'axes', None)
        if ax is None or ax.xaxis is None:
            return x
        return ax.xaxis.convert_units(x)

    def convert_yunits(self, y):
        """For artists in an axes, if the yaxis has units support,
        convert *y* using yaxis unit type
        """
        ax = getattr(self, 'axes', None)
        if ax is None or ax.yaxis is None:
            return y
        return ax.yaxis.convert_units(y)

    def get_window_extent(self,renderer):
        """
        Get the axes bounding box in display space.
        Subclasses should override for inclusion in the bounding box
        "tight" calculation. Default is to return an empty bounding
        box at 0, 0.

        Be careful when using this function, the results will not update
        if the artist window extent of the artist changes.  The extent
        can change due to any changes in the transform stack, such as
        changing the axes limits, the figure size, or the canvas used
        (as is done when saving a figure).  This can lead to unexpected
        behavior where interactive figures will look fine on the screen,
        but will save incorrectly.
        """
        return Bbox([[0, 0], [0, 0]])

    def add_callback(self,func):
        """
        Adds a callback function that will be called whenever one of
        the :class:`Artist`'s properties changes.

        Returns an *id* that is useful for removing the callback with
        :meth:`remove_callback` later.
        """
        oid = self._oid
        self._propobservers[oid] = func
        self._oid += 1
        return oid

    def remove_callback(self,oid):
        """
        Remove a callback based on its *id*.

        .. seealso::

            :meth:`add_callback`
               For adding callbacks

        """
        try:
            del self._propobservers[oid]
        except KeyError:
            pass

    # I am not sure if I need this? I feel as if migrating to traitlets and using
    #observers will be able to help eliminate pchanged() without losing integrity
    #of the following callbacks when a property is changed
    #Note: For now we will keep this function
    def pchanged(self):
        """
        Fire an event when property changed, calling all of the
        registered callbacks.
        """
        for oid, func in six.iteritems(self._propobservers):
            func(self)

    def is_transform_set(self):
        """
        Returns *True* if :class:`Artist` has a transform explicitly
        set.
        """
        return self._transformSet

    def hitlist(self, event):
        """
        List the children of the artist which contain the mouse event *event*.
        """
        L = []
        try:
            hascursor, info = self.contains(event)
            if hascursor:
                L.append(self)
        except:
            import traceback
            traceback.print_exc()
            print("while checking", self.__class__)

        for a in self.get_children():
            L.extend(a.hitlist(event))
        return L

    # Note sure if this is how to go about a contains mouseevent function
    def contains(self, mouseevent):
        """Test whether the artist contains the mouse event.

        Returns the truth value and a dictionary of artist specific details of
        selection, such as which points are contained in the pick radius.  See
        individual artists for details.
        """
        if callable(self._contains):
            return self._contains(self, mouseevent)
        warnings.warn("'%s' needs 'contains' method" % self.__class__.__name__)
        return False, {}

    def pickable(self):
        'Return *True* if :class:`Artist` is pickable.'
        return (self.figure is not None and
                self.figure.canvas is not None and
                self._picker is not None)

    def pick(self, mouseevent):
        """
        Process pick event

        each child artist will fire a pick event if *mouseevent* is over
        the artist and the artist has picker set
        """
        # Pick self
        if self.pickable():
            picker = self.get_picker()
            if callable(picker):
                inside, prop = picker(self, mouseevent)
            else:
                inside, prop = self.contains(mouseevent)
            if inside:
                self.figure.canvas.pick_event(mouseevent, self, **prop)

        # Pick children
        for a in self.get_children():
            # make sure the event happened in the same axes
            ax = getattr(a, 'axes', None)
            if (mouseevent.inaxes is None or ax is None
                    or mouseevent.inaxes == ax):
                # we need to check if mouseevent.inaxes is None
                # because some objects associated with an axes (e.g., a
                # tick label) can be outside the bounding box of the
                # axes and inaxes will be None
                # also check that ax is None so that it traverse objects
                # which do no have an axes property but children might
                a.pick(mouseevent)

    # I think this function can be rid of with the movement to traitlets
    def is_figure_set(self):
        """
        Returns True if the artist is assigned to a
        :class:`~matplotlib.figure.Figure`.
        """
        return self.figure is not None

    # need to look into this
    def get_transformed_clip_path_and_affine(self):
        '''
        Return the clip path with the non-affine part of its
        transformation applied, and the remaining affine part of its
        transformation.
        '''
        if self._clippath is not None:
            return self._clippath.get_transformed_path_and_affine()
        return None, None
