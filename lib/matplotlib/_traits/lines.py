"""
matplotlib.lines.Line2D refactored in traitlets
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import six
import warnings
import numpy as np


# from .artist import Artist
from matplotlib import artist, colors as mcolors, docstring, rcParams
from .artist import Artist, allow_rasterization
import matplotlib.artist as b_artist
print('matplotlib.artist b_artist: ', b_artist)


# import matplotlib._traits.artist as artist
# from matplotlib._traits.artist import Artist, allow_rasterization
from .cbook import (
    iterable, is_numlike, ls_mapper, ls_mapper_r, STEP_LOOKUP_MAP)
from matplotlib.markers import MarkerStyle
from matplotlib.path import Path
from matplotlib.transforms import Bbox, TransformedPath, IdentityTransform
# Imported here for backward compatibility, even though they don't
# really belong.
from numpy import ma
from . import _path
from matplotlib.markers import (
    CARETLEFT, CARETRIGHT, CARETUP, CARETDOWN,
    CARETLEFTBASE, CARETRIGHTBASE, CARETUPBASE, CARETDOWNBASE,
    TICKLEFT, TICKRIGHT, TICKUP, TICKDOWN)

from traitlets import HasTraits, Any, Instance, Unicode, Float, Bool

#for monkey patching into base lines
import matplotlib.lines.Line2D as b_Line2D



def _get_dash_pattern(style):
    """Convert linestyle -> dash pattern
    """
    # go from short hand -> full strings
    if isinstance(style, six.string_types):
        style = ls_mapper.get(style, style)
    # un-dashed styles
    if style in ['solid', 'None']:
        offset, dashes = None, None
    # dashed styles
    elif style in ['dashed', 'dashdot', 'dotted']:
        offset = 0
        dashes = tuple(rcParams['lines.{}_pattern'.format(style)])
    #
    elif isinstance(style, tuple):
        offset, dashes = style
    else:
        raise ValueError('Unrecognized linestyle: %s' % str(style))

    # normalize offset to be positive and shorter than the dash cycle
    if dashes is not None and offset is not None:
        dsum = sum(dashes)
        if dsum:
            offset %= dsum

    return offset, dashes

def _scale_dashes(offset, dashes, lw):
    if not rcParams['lines.scale_dashes']:
        return offset, dashes

    scaled_offset = scaled_dashes = None
    if offset is not None:
        scaled_offset = offset * lw
    if dashes is not None:
        scaled_dashes = [x * lw if x is not None else None
                         for x in dashes]

    return scaled_offset, scaled_dashes

def segment_hits(cx, cy, x, y, radius):
    """
    Determine if any line segments are within radius of a
    point. Returns the list of line segments that are within that
    radius.
    """
    # Process single points specially
    if len(x) < 2:
        res, = np.nonzero((cx - x) ** 2 + (cy - y) ** 2 <= radius ** 2)
        return res

    # We need to lop the last element off a lot.
    xr, yr = x[:-1], y[:-1]

    # Only look at line segments whose nearest point to C on the line
    # lies within the segment.
    dx, dy = x[1:] - xr, y[1:] - yr
    Lnorm_sq = dx ** 2 + dy ** 2  # Possibly want to eliminate Lnorm==0
    u = ((cx - xr) * dx + (cy - yr) * dy) / Lnorm_sq
    candidates = (u >= 0) & (u <= 1)
    #if any(candidates): print "candidates",xr[candidates]

    # Note that there is a little area near one side of each point
    # which will be near neither segment, and another which will
    # be near both, depending on the angle of the lines.  The
    # following radius test eliminates these ambiguities.
    point_hits = (cx - x) ** 2 + (cy - y) ** 2 <= radius ** 2
    #if any(point_hits): print "points",xr[candidates]
    candidates = candidates & ~(point_hits[:-1] | point_hits[1:])

    # For those candidates which remain, determine how far they lie away
    # from the line.
    px, py = xr + u * dx, yr + u * dy
    line_hits = (cx - px) ** 2 + (cy - py) ** 2 <= radius ** 2
    #if any(line_hits): print "lines",xr[candidates]
    line_hits = line_hits & candidates
    points, = point_hits.ravel().nonzero()
    lines, = line_hits.ravel().nonzero()
    #print points,lines
    return np.concatenate((points, lines))

def _mark_every_path(markevery, tpath, affine, ax_transform):
    """
    Helper function that sorts out how to deal the input
    `markevery` and returns the points where markers should be drawn.

    Takes in the `markevery` value and the line path and returns the
    sub-sampled path.
    """
    # pull out the two bits of data we want from the path
    codes, verts = tpath.codes, tpath.vertices

    def _slice_or_none(in_v, slc):
        '''
        Helper function to cope with `codes` being an
        ndarray or `None`
        '''
        if in_v is None:
            return None
        return in_v[slc]

    # if just a float, assume starting at 0.0 and make a tuple
    if isinstance(markevery, float):
        markevery = (0.0, markevery)
    # if just an int, assume starting at 0 and make a tuple
    elif isinstance(markevery, int):
        markevery = (0, markevery)
    # if just an numpy int, assume starting at 0 and make a tuple
    elif isinstance(markevery, np.integer):
        markevery = (0, markevery.item())

    if isinstance(markevery, tuple):
        if len(markevery) != 2:
            raise ValueError('`markevery` is a tuple but its '
                'len is not 2; '
                'markevery=%s' % (markevery,))
        start, step = markevery
        # if step is an int, old behavior
        if isinstance(step, int):
            #tuple of 2 int is for backwards compatibility,
            if not(isinstance(start, int)):
                raise ValueError('`markevery` is a tuple with '
                    'len 2 and second element is an int, but '
                    'the first element is not an int; '
                    'markevery=%s' % (markevery,))
            # just return, we are done here

            return Path(verts[slice(start, None, step)],
                        _slice_or_none(codes, slice(start, None, step)))

        elif isinstance(step, float):
            if not (isinstance(start, int) or
                    isinstance(start, float)):
                raise ValueError('`markevery` is a tuple with '
                    'len 2 and second element is a float, but '
                    'the first element is not a float or an '
                    'int; '
                    'markevery=%s' % (markevery,))
            #calc cumulative distance along path (in display
            # coords):
            disp_coords = affine.transform(tpath.vertices)
            delta = np.empty((len(disp_coords), 2),
                             dtype=float)
            delta[0, :] = 0.0
            delta[1:, :] = (disp_coords[1:, :] -
                                disp_coords[:-1, :])
            delta = np.sum(delta**2, axis=1)
            delta = np.sqrt(delta)
            delta = np.cumsum(delta)
            #calc distance between markers along path based on
            # the axes bounding box diagonal being a distance
            # of unity:
            scale = ax_transform.transform(
                np.array([[0, 0], [1, 1]]))
            scale = np.diff(scale, axis=0)
            scale = np.sum(scale**2)
            scale = np.sqrt(scale)
            marker_delta = np.arange(start * scale,
                                     delta[-1],
                                     step * scale)
            #find closest actual data point that is closest to
            # the theoretical distance along the path:
            inds = np.abs(delta[np.newaxis, :] -
                            marker_delta[:, np.newaxis])
            inds = inds.argmin(axis=1)
            inds = np.unique(inds)
            # return, we are done here
            return Path(verts[inds],
                        _slice_or_none(codes, inds))
        else:
            raise ValueError('`markevery` is a tuple with '
                'len 2, but its second element is not an int '
                'or a float; '
                'markevery=%s' % (markevery,))

    elif isinstance(markevery, slice):
        # mazol tov, it's already a slice, just return
        return Path(verts[markevery],
                    _slice_or_none(codes, markevery))

    elif iterable(markevery):
        #fancy indexing
        try:
            return Path(verts[markevery],
                    _slice_or_none(codes, markevery))

        except (ValueError, IndexError):
            raise ValueError('`markevery` is iterable but '
                'not a valid form of numpy fancy indexing; '
                'markevery=%s' % (markevery,))
    else:
        raise ValueError('Value of `markevery` is not '
            'recognized; '
            'markevery=%s' % (markevery,))





class Line2D(HasTraits, b_artist.Artist):
    """
    A line - the line can have both a solid linestyle connecting all
    the vertices, and a marker at each vertex.  Additionally, the
    drawing of the solid line is influenced by the drawstyle, e.g., one
    can create "stepped" lines in various styles.
    """

    # remain the same throughout
    lineStyles = _lineStyles = {  # hidden names deprecated
        '-':    '_draw_solid',
        '--':   '_draw_dashed',
        '-.':   '_draw_dash_dot',
        ':':    '_draw_dotted',
        'None': '_draw_nothing',
        ' ':    '_draw_nothing',
        '':     '_draw_nothing',
    }

    #remain the same
    _drawStyles_l = {
        'default':    '_draw_lines',
        'steps-mid':  '_draw_steps_mid',
        'steps-pre':  '_draw_steps_pre',
        'steps-post': '_draw_steps_post',
    }

    #remain the same
    _drawStyles_s = {
        'steps': '_draw_steps_pre',
    }

    # drawStyles should now be deprecated.
    drawStyles = {}
    drawStyles.update(_drawStyles_l)
    drawStyles.update(_drawStyles_s)
    # Need a list ordered with long names first:
    drawStyleKeys = list(_drawStyles_l) + list(_drawStyles_s)

    # Referenced here to maintain API.  These are defined in
    # MarkerStyle
    markers = MarkerStyle.markers
    filled_markers = MarkerStyle.filled_markers
    fillStyles = MarkerStyle.fillstyles

    zorder = 2
    validCap = ('butt', 'round', 'projecting')
    validJoin = ('miter', 'round', 'bevel')

    xdata=Instance('numpy.array', allow_none=True,default_value=None) #not sure about this line

    ydata=Instance('numpy.array', allow_none=True,default_value=None) #not sure about this line

    linewidth=Float(allow_none=True, default_value=None)

    linestyle=Instance('matplotlib.text.Text', allow_none=True, default_value=None)

    color=Unicode(allow_none=True, default_value=None)
    #color=Instance('matplotlib.text.Text', allow_none=True,default_value=None)

    marker=Instance('matplotlib.markers',allow_none=True, default_value=None)

    markersize=Float(allow_none=True,default_value=True)

    markeredgewidth=Float(allow_none=True,default_value=None)

    # same for color because I am not sure if the color is Unicode or Python String; assume Unicode first for testing
    markerfacecolor=Unicode(allow_none=True, default_value=None)
    #markerfacecolor=Instance('matplotlib.text.Text', allow_none=True,default_value=None)

    # same applies for the alternative face color
    markerfacecoloralt=Unicode(allow_none=True, default_value=None)
    #markerfacecoloralt=Instance('matplotlib.text.Text', allow_none=True,default_value=None)

    # this gets passed into marker so I want to assume same for color however only accepts the following strings: ['full' | 'left' | 'right' | 'bottom' | 'top' | 'none']
    fillstyle=Unicode(allow_none=True, default_value=None)
    # fillstyle=Instance('matplotlib.text.Text', allow_none=True,default_value=None)
    antialiased=Bool(default_value=False)

    # accepts: ['butt' | 'round' | 'projecting']
    dash_capstyle=Unicode(allow_none=True, default_value=None)
    # dash_capstyle=Instance('matplotlib.text.Text', allow_none=True,default_value=None)

    # accepts: ['butt' | 'round' | 'projecting']
    solid_capstyle=Unicode(allow_none=True, default_value=None)
    # solid_capstyle=Instance('matplotlib.text.Text', allow_none=True,default_value=None)

    # accepts: ['miter' | 'round' | 'bevel']
    dash_joinstyle=Unicode(allow_none=True, default_value=None)
    # dash_joinstyle=Instance('matplotlib.text.Text', allow_none=True,default_value=None)

    # accepts: ['miter' | 'round' | 'bevel']
    solid_joinstyle=Unicode(allow_none=True, default_value=None)
    # solid_joinstyle=Instance('matplotlib.text.Text', allow_none=True,default_value=None)

    pickradius=Int(allow_none=True, default_value=5)

    # accepts: ['default' | 'steps' | 'steps-pre' | 'steps-mid' | 'steps-post']
    drawstyle=Unicode(allow_none=True, default_value=None)
    # drawstyle=Instance('matplotlib.text.Text', allow_none=True,default_value=None)

    # for this one I want to attempt at using the ANY trait
    markevery=Any(allow_none=True, default_value=None)

    #only found once in the original lines code so not sure what to do with this
    # verticalOffset = None

    ind_offset = Int(allow_none=True,default_value=0)

    # xorig = np.asarray([])
    xorig = Instance('numpy.asarray', allow_none=True,default_value=[]) #not sure on this line ay have to declare default value in default decorator

    # yorig = np.asarray([])
    yorig = Instance('numpy.asarray', allow_none=True,default_value=[]) #not sure on this line ay have to declare default value in default decorator

    # invalidx = True
    invalidx=Bool(default_value=True)
    # invalidy = True
    invalidy=Bool(default_value=True)


    # for x, y, & xy I am not sure if these following lines of code are correct, I may just leave them alone come testing time
    # x = None
    x=Instance('numpy.asarray', allow_none=True,default_value=None) # not sure on this line
    # y = None
    y=Instance('numpy.asarray', allow_none=True,default_value=None) # not sure on this line
    # xy = None


    # path = None
    path=Instance('matplotlib.path.Path', allow_none=True, default_value=None)
    # transformed_path = None
    transformed_path=Instance('matplotlib.transforms.TransformedPath', allow_none=True, default_value=None)
    # subslice = False
    subslice=Bool(default_value=False)

    # x_filled = None # used in subslicing; only x is needed
    #not sure if this line below will work or not
    x_filled=Instance('np.array', allow_none=True, default_value=None)

    # TODO: Not sure how to handle these, I am going to try Unicode & Text Instance
    # scaled dash + offset
    # dashSeq = None
    # dashOffset = 0
    dashOffset=Int(allow_none=True, default_value=None)
    # unscaled dash + offset
    # this is needed scaling the dash pattern by linewidth
    # us_dashSeq = None
    # us_dashOffset = 0
    us_dashOffset=Int(allow_none=True, default_value=None)



    set_data(xdata, ydata)

    # not sure how much this will have to be refactored
    def __str__(self):
        if self._label != "":
            return "Line2D(%s)" % (self._label)
        elif self._x is None:
            return "Line2D()"
        elif len(self._x) > 3:
            return "Line2D((%g,%g),(%g,%g),...,(%g,%g))"\
                % (self._x[0], self._y[0], self._x[0],
                   self._y[0], self._x[-1], self._y[-1])
        else:
            return "Line2D(%s)"\
                % (",".join(["(%g,%g)" % (x, y) for x, y
                             in zip(self._x, self._y)]))

    #this will have to be edited according to the traits
    def __init__(self, **kwargs):
        """
        Create a :class:`~matplotlib.lines.Line2D` instance with *x*
        and *y* data in sequences *xdata*, *ydata*.

        The kwargs are :class:`~matplotlib.lines.Line2D` properties:

        %(Line2D)s
        """

        #initialize Artist in Line2D
        Artist.__init__(self)
        print("Artist: ", Artist)

"""
________________________________________________________________________________
END OF INIT FUNCTION
"""

    # NOTE: NOT SURE IF xdata & ydata are needed
    #xdata default
    # @default("xdata")
    # def _xdata_default(self):
    #     print("xdata: generating default value")
    #     return None
    #xdata validate
    @validate("xdata")
    def _xdata_validate(self, proposal):
        print("xdata: cross validating %r" % proposal.value)
        #convert sequences to numpy arrays
        if not iterable(proposal.value):
            raise RuntimeError('xdata must be a sequence')
        return proposal.value
    #xdata observer
    @observe("xdata", type="change")
    def _xdata_observe(self, change):
        print("xdata: observed a change from %r to %r" % (change.old, change.new))

    #ydata default
    # @default("ydata")
    # def _ydata_default(self):
    #     print("ydata: generating default value")
    #     return None
    #ydata validate
    @validate("ydata")
    def _ydata_validate(self, proposal):
        print("ydata: cross validating %r" % proposal.value)
        #convert sequences to numpy arrays
        if not iterable(proposal.value):
            raise RuntimeError('ydata must be a sequence')
        return proposal.value
    #ydata observer
    @observe("ydata", type="change")
    def _ydata_observe(self, change):
        print("ydata: observed a change from %r to %r" % (change.old, change.new))

    #linewidth default
    # @default("linewidth")
    # def _linewidth_default(self):
    #     print("linewidth: generating default value")
    #     return None
    #linewidth validate
    @validate("linewidth")
    def _linewidth_validate(self, proposal):
        print("linewidth: cross validating %r" % proposal.value)
        if proposal.value is None:
            return rcParams['lines.linewidth']
        #to assure we are dealing with a FLOAT
        proposal.value=float(proposal.value) #watch out for recursion on this line
        return proposal.value
    #linewidth observer
    @observe("linewidth", type="change")
    def _linewidth_observe(self, change):
        print("linewidth: observed a change from %r to %r" % (change.old, change.new))

    #linestyle default
    # @default("linestyle")
    # def _linestyle_default(self):
    #     print("linestyle: generating default value")
    #     return None
    #linestyle validate
    @validate("linestyle")
    def _linestyle_validate(self, proposal):
        print("linestyle: cross validating %r" % proposal.value)
        if proposal.value is None:
            return rcParams['lines.linestyle']

        if isinstance(proposal.value, six.string_types):
            # ds, ls = self._split_drawstyle_linestyle(linestyle)
            # if ds is not None and drawstyle is not None and ds != drawstyle:
            #     raise ValueError("Inconsistent drawstyle ({0!r}) and "
            #                      "linestyle ({1!r})".format(drawstyle,
            #                                                 linestyle)
            #                      )
            ds, ls = self._split_drawstyle_linestyle(proposal.value)
            if ds is not None and self.drawstyle is not None and ds != drawstyle:
                raise ValueError("Inconsistent drawstyle ({0!r}) and "
                                 "linestyle ({1!r})".format(self.drawstyle,
                                                            proposal.value)
                                 )
            # linestyle = ls

            if ds is not None:
                # drawstyle = ds
                self.drawstyle = ds
                return proposal.value
        # return proposal.value
    #linestyle observer
    @observe("linestyle", type="change")
    def _linestyle_observe(self, change):
        print("linestyle: observed a change from %r to %r" % (change.old, change.new))

    #color default
    # @default("color")
    # def _color_default(self):
    #     print("color: generating default value")
    #     return None
    #color validate
    @validate("color")
    def _color_validate(self, proposal):
        print("color: cross validating %r" % proposal.value)
        if proposal.value is None:
            return rcParams['lines.color']
        return proposal.value
    #color observer
    @observe("color", type="change")
    def _color_observe(self, change):
        print("color: observed a change from %r to %r" % (change.old, change.new))

    #marker default
    # @default("marker")
    # def _marker_default(self):
    #     print("marker : generating default value")
    #     return None
    #marker validate
    @validate("marker")
    def _marker_validate(self, proposal):
        print("marker: cross validating %r" % proposal.value)
        if proposal.value is None:
            return rcParams['lines.marker']
        return proposal.value
    #marker observer
    @observe("marker", type="change")
    def _marker_observe(self, change):
        print("marker: observed a change from %r to %r" % (change.old, change.new))

    #markersize default
    # @default("markersize")
    # def _markersize_default(self):
    #     print("markersize : generating default value")
    #     return None
    #markersize validate
    @validate("markersize")
    def _markersize_validate(self, proposal):
        print("markersize: cross validating %r" % proposal.value)
        if proposal.value is None:
            return rcParams['lines.markersize']
        return proposal.value
    #markersize observer
    @observe("markersize", type="change")
    def _markersize_observe(self, change):
        print("markersize: observed a change from %r to %r" % (change.old, change.new))

    #markeredgewidth default
    # @default("markeredgewidth")
    # def _markeredgewidth_default(self):
        # print("markeredgewidth : generating default value")
        # return None
    #markeredgewidth validate
    @validate("markeredgewidth")
    def _markeredgewidth_validate(self, proposal):
        print("markeredgewidth: cross validating %r" % proposal.value)
        return proposal.value
    #markeredgewidth observer
    @observe("markeredgewidth", type="change")
    def _markeredgewidth_observe(self, change):
        print("markeredgewidth: observed a change from %r to %r" % (change.old, change.new))

    #markerfacecolor default
    # @default("markerfacecolor")
    # def _markerfacecolor_default(self):
        # print("markerfacecolor: generating default value")
        # return None
    #markerfacecolor validate
    @validate("markerfacecolor")
    def _markerfacecolor_validate(self, proposal):
        print("markerfacecolor: cross validating %r" % proposal.value)
        return proposal.value
    #markerfacecolor observer
    @observe("markerfacecolor", type="change")
    def _markerfacecolor_observe(self, change):
        print("markerfacecolor: observed a change from %r to %r" % (change.old, change.new))

    #markerfacecoloralt default
    # @default("markerfacecoloralt")
    # def _markerfacecoloralt_default(self):
        # print("markerfacecoloralt: generating default value")
        # return None
    #markerfacecoloralt validate
    @validate("markerfacecoloralt")
    def _markerfacecoloralt_validate(self, proposal):
        print("markerfacecoloralt: cross validating %r" % proposal.value)
        return proposal.value
    #markerfacecoloralt observer
    @observe("markerfacecoloralt", type="change")
    def _markerfacecoloralt_observe(self, change):
        print("markerfacecoloralt: observed a change from %r to %r" % (change.old, change.new))

    #fillstyle default
    # @default("fillstyle")
    # def _fillstyle_default(self):
        # print("fillstyle : generating default value")
        # return None
    #fillstyle validate
    @validate("fillstyle")
    def _fillstyle_validate(self, proposal):
        print("fillstyle: cross validating %r" % proposal.value)
        return proposal.value
    #fillstyle observer
    @observe("fillstyle", type="change")
    def _fillstyle_observe(self, change):
        print("fillstyle: observed a change from %r to %r" % (change.old, change.new))

    #antialiased default
    # @default("antialiased")
    # def _antialiased_default(self):
        # print("antialiased : generating default value")
        # return False
    #antialiased validate
    @validate("antialiased")
    def _antialiased_validate(self, proposal):
        print("antialiased: cross validating %r" % proposal.value)
        if proposal.value is None:
            return rcParams['lines.antialiased']
        return proposal.value
    #antialiased observer
    @observe("antialiased", type="change")
    def _antialiased_observe(self, change):
        print("antialiased: observed a change from %r to %r" % (change.old, change.new))

    #dash_capstyle default
    # @default("dash_capstyle")
    # def _dash_capstyle_default(self):
        # print("dash_capstyle : generating default value")
        # return None
    #dash_capstyle validate
    @validate("dash_capstyle")
    def _dash_capstyle_validate(self, proposal):
        print("dash_capstyle: cross validating %r" % proposal.value)
        if proposal.value is None:
            return rcParams['lines.dash_capstyle']
        return proposal.value
    #dash_capstyle observer
    @observe("dash_capstyle", type="change")
    def _dash_capstyle_observe(self, change):
        print("dash_capstyle: observed a change from %r to %r" % (change.old, change.new))

    #solid_capstyle default
    # @default("solid_capstyle")
    # def _solid_capstyle_default(self):
        # print("solid_capstyle : generating default value")
        # return None
    #solid_capstyle validate
    @validate("solid_capstyle")
    def _solid_capstyle_validate(self, proposal):
        print("solid_capstyle: cross validating %r" % proposal.value)
        if proposal.value is None:
            return rcParams['lines.solid_capstyle']
        return proposal.value
    #solid_capstyle observer
    @observe("solid_capstyle", type="change")
    def _solid_capstyle_observe(self, change):
        print("solid_capstyle: observed a change from %r to %r" % (change.old, change.new))

    #dash_joinstyle default
    # @default("dash_joinstyle")
    # def _dash_joinstyle_default(self):
        # print("dash_joinstyle : generating default value")
        # return None
    #dash_joinstyle validate
    @validate("dash_joinstyle")
    def _dash_joinstyle_validate(self, proposal):
        print("dash_joinstyle: cross validating %r" % proposal.value)
        if proposal.value is None:
            return rcParams['lines.dash_joinstyle']
        return proposal.value
    # observer
    @observe("dash_joinstyle", type="change")
    def __dash_joinstyleobserve(self, change):
        print(": observed a change from %r to %r" % (change.old, change.new))

    #solid_joinstyle default
    # @default("solid_joinstyle")
    # def _solid_joinstyle_default(self):
        # print("solid_joinstyle : generating default value")
        # return None
    #solid_joinstyle validate
    @validate("solid_joinstyle")
    def _solid_joinstyle_validate(self, proposal):
        print("solid_joinstyle: cross validating %r" % proposal.value)
        if proposal.value is None:
            return rcParams['lines.solid_joinstyle']
        return proposal.value
    #solid_joinstyle observer
    @observe("solid_joinstyle", type="change")
    def _solid_joinstyle_observe(self, change):
        print("solid_joinstyle: observed a change from %r to %r" % (change.old, change.new))

    #pickradius default
    # @default("pickradius")
    # def _pickradius_default(self):
        # print("pickradius : generating default value")
        # return 5
    #pickradius validate
    @validate("pickradius")
    def _pickradius_validate(self, proposal):
        print("pickradius: cross validating %r" % proposal.value)
        return proposal.value
    #pickradius observer
    @observe("pickradius", type="change")
    def _pickradius_observe(self, change):
        print("pickradius: observed a change from %r to %r" % (change.old, change.new))

    #drawstyle default
    # @default("drawstyle")
    # def _drawstyle_default(self):
        # print("drawstyle : generating default value")
        # return None
    #drawstyle validate
    @validate("drawstyle")
    def _drawstyle_validate(self, proposal):
        print("drawstyle: cross validating %r" % proposal.value)
        if proposal.value is None:
            return 'default'
        return proposal.value
    #drawstyle observer
    @observe("drawstyle", type="change")
    def _drawstyle_observe(self, change):
        print("drawstyle: observed a change from %r to %r" % (change.old, change.new))

    #markevery default
    # @default("markevery")
    # def _markevery_default(self):
        # print("markevery : generating default value")
        # return None
    #markevery validate
    @validate("markevery")
    def _markevery_validate(self, proposal):
        print("markevery: cross validating %r" % proposal.value)
        return proposal.value
    #markevery observer
    @observe("markevery", type="change")
    def _markevery_observe(self, change):
        print("markevery: observed a change from %r to %r" % (change.old, change.new))

    # TODO: figure out what to do with this!!!!!
    #verticalOffset default
    # @default("verticalOffset")
    # def _verticalOffset_default(self):
        # print("verticalOffset: generating default value")
        # return False
    #verticalOffset validate
    # @validate("verticalOffset")
    # def _verticalOffset_validate(self, proposal):
        # print("verticalOffset: cross validating %r" % proposal.value)
        # return proposal.value
    #verticalOffset observer
    # @observe("verticalOffset", type="change")
    # def _verticalOffset_observe(self, change):
        # print("verticalOffset: observed a change from %r to %r" % (change.old, change.new))

    #ind_offset default
    # @default("ind_offset")
    # def _ind_offset_default(self):
        # print("ind_offset: generating default value")
        # return 0
    #ind_offset validate
    @validate("ind_offset")
    def _ind_offset_validate(self, proposal):
        print("ind_offset: cross validating %r" % proposal.value)
        return proposal.value
    #ind_offset observer
    @observe("ind_offset", type="change")
    def _ind_offset_observe(self, change):
        print("ind_offset: observed a change from %r to %r" % (change.old, change.new))

    #xorig default
    # @default("xorig")
    # def _xorig_default(self):
        # print("xorig: generating default value")
        # return None
    #xorig validate
    @validate("xorig")
    def _xorig_validate(self, proposal):
        print("xorig: cross validating %r" % proposal.value)
        return proposal.value
    #xorig observer
    @observe("xorig", type="change")
    def _xorig_observe(self, change):
        print("xorig: observed a change from %r to %r" % (change.old, change.new))

    #yorig default
    # @default("yorig")
    # def _yorig_default(self):
        # print("yorig: generating default value")
        # return None
    #yorig validate
    @validate("yorig")
    def _yorig_validate(self, proposal):
        print("yorig: cross validating %r" % proposal.value)
        return proposal.value
    #yorig observer
    @observe("yorig", type="change")
    def _yorig_observe(self, change):
        print("yorig: observed a change from %r to %r" % (change.old, change.new))

    #invalidx default
    # @default("invalidx")
    # def _invalidx_default(self):
    #     print("invalidx: generating default value")
    #     return True
    #invalidx validate
    @validate("invalidx")
    def _invalidx_validate(self, proposal):
        print("invalidx: cross validating %r" % proposal.value)
        return proposal.value
    #invalidx observer
    @observe("invalidx", type="change")
    def _invalidx_observe(self, change):
        print(": observed a change from %r to %r" % (change.old, change.new))

    #invalidy default
    # @default("invalidy")
    # def _invalidy_default(self):
        # print("invalidy: generating default value")
        # return True
    #invalidy validate
    @validate("invalidy")
    def _invalidy_validate(self, proposal):
        print("invalidy: cross validating %r" % proposal.value)
        return proposal.value
    #invalidy observer
    @observe("invalidy", type="change")
    def _invalidy_observe(self, change):
        print("invalidy: observed a change from %r to %r" % (change.old, change.new))

    #x default
    # @default("x")
    # def _x_default(self):
        # print("x: generating default value")
        # return None
    #x validate
    @validate("x")
    def _x_validate(self, proposal):
        print("x: cross validating %r" % proposal.value)
        return proposal.value
    #x observer
    @observe("x", type="change")
    def _x_observe(self, change):
        print("x: observed a change from %r to %r" % (change.old, change.new))

    #y default
    # @default("y")
    # def _y_default(self):
        # print("y: generating default value")
        # return None
    #y validate
    @validate("y")
    def _y_validate(self, proposal):
        print("y: cross validating %r" % proposal.value)
        return proposal.value
    #y observer
    @observe("y", type="change")
    def _y_observe(self, change):
        print("y: observed a change from %r to %r" % (change.old, change.new))

    #path default
    # @default("path")
    # def _path_default(self):
        # print("path: generating default value")
        # return None
    #path validate
    @validate("path")
    def _path_validate(self, proposal):
        print("path: cross validating %r" % proposal.value)
        return proposal.value
    #path observer
    @observe("path", type="change")
    def _path_observe(self, change):
        print("path: observed a change from %r to %r" % (change.old, change.new))

    #transformed_path default
    # @default("transformed_path")
    # def _transformed_path_default(self):
        # print("transformed_path: generating default value")
        # return None
    #transformed_path validate
    @validate("transformed_path")
    def _transformed_path_validate(self, proposal):
        print("transformed_path: cross validating %r" % proposal.value)
        return proposal.value
    #transformed_path observer
    @observe("transformed_path", type="change")
    def _transformed_path_observe(self, change):
        print("transformed_path: observed a change from %r to %r" % (change.old, change.new))

    #subslice default
    # @default("subslice")
    # def _subslice_default(self):
        # print("subslice: generating default value")
        # return None
    #subslice validate
    @validate("subslice")
    def _subslice_validate(self, proposal):
        print("subslice: cross validating %r" % proposal.value)
        return proposal.value
    #subslice observer
    @observe("subslice", type="change")
    def _subslice_observe(self, change):
        print("subslice: observed a change from %r to %r" % (change.old, change.new))

    #x_filled default
    # @default("x_filled")
    # def _x_filled_default(self):
        # print("x_filled: generating default value")
        # return None
    #x_filled validate
    @validate("x_filled")
    def _x_filled_validate(self, proposal):
        print("x_filled: cross validating %r" % proposal.value)
        return proposal.value
    #x_filled observer
    @observe("x_filled", type="change")
    def _x_filled_observe(self, change):
        print("x_filled: observed a change from %r to %r" % (change.old, change.new))






"""
________________________________________________________________________________
"""
    def set_data(self, *args):
        """
        Set the x and y data

        ACCEPTS: 2D array (rows are x, y) or two 1D arrays
        """
        if len(args) == 1:
            x, y = args[0]
        else:
            x, y = args

        self.set_xdata(x)
        self.set_ydata(y)

    def _split_drawstyle_linestyle(self, ls):
        '''Split drawstyle from linestyle string

        If `ls` is only a drawstyle default to returning a linestyle
        of '-'.

        Parameters
        ----------
        ls : str
            The linestyle to be processed

        Returns
        -------
        ret_ds : str or None
            If the linestyle string does not contain a drawstyle prefix
            return None, otherwise return it.

        ls : str
            The linestyle with the drawstyle (if any) stripped.
        '''
        ret_ds = None
        for ds in self.drawStyleKeys:  # long names are first in the list
            if ls.startswith(ds):
                ret_ds = ds
                if len(ls) > len(ds):
                    ls = ls[len(ds):]
                else:
                    ls = '-'
                break

        return ret_ds, ls



"""
________________________________________________________________________________
"""

#for monkey patching
b_Line2D = Line2D()
