# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from collections import OrderedDict

from matplotlib.externals import six
from matplotlib.externals.six.moves import zip

import warnings

import numpy as np

from matplotlib.path import Path
from matplotlib import rcParams
import matplotlib.font_manager as font_manager
from matplotlib.mathtext import MathTextParser
import matplotlib.dviread as dviread
from matplotlib.font_manager import FontProperties, get_font
from matplotlib.transforms import Affine2D
from matplotlib.externals.six.moves.urllib.parse import quote as urllib_quote

import freetypy as ft


class TextToPath(object):
    """
    A class that convert a given text to a path using ttf fonts.
    """

    FONT_SCALE = 100.
    DPI = 72

    def __init__(self):
        """
        Initialization
        """
        self.mathtext_parser = MathTextParser('path')
        self.tex_font_map = None

        from matplotlib.cbook import maxdict
        self._ps_fontd = maxdict(50)

        self._texmanager = None

        self._adobe_standard_encoding = None

    def _get_adobe_standard_encoding(self):
        enc_name = dviread.find_tex_file('8a.enc')
        enc = dviread.Encoding(enc_name)
        return dict([(c, i) for i, c in enumerate(enc.encoding)])

    def _get_font(self, prop):
        """
        find a ttf font.
        """
        fname = font_manager.findfont(prop)
        font = get_font(fname)
        font.set_char_size(
            self.FONT_SCALE, self.FONT_SCALE, self.DPI, self.DPI)

        return font

    def _get_hinting_flag(self):
        return ft.LOAD.NO_HINTING

    def _get_char_id(self, font, ccode):
        """
        Return a unique id for the given font and character-code set.
        """
        char_id = urllib_quote('%s-%x' % (font.get_postscript_name(), ccode))
        return char_id

    def _get_char_id_ps(self, font, ccode):
        """
        Return a unique id for the given font and character-code set (for tex).
        """
        ps_name = font.get_postscript_name()
        char_id = urllib_quote('%s-%d' % (ps_name, ccode))
        return char_id

    def glyph_to_path(self, glyph, currx=0.):
        """
        convert the glyph to vertices and codes.
        """
        verts, codes = glyph.outline.to_points_and_codes()
        verts = np.array(verts)
        codes = np.array(codes)
        if currx != 0.0:
            verts[:, 0] += currx
        return verts, codes

    def get_text_width_height_descent(self, s, prop, ismath):
        if rcParams['text.usetex']:
            texmanager = self.get_texmanager()
            fontsize = prop.get_size_in_points()
            w, h, d = texmanager.get_text_width_height_descent(s, fontsize,
                                                               renderer=None)
            return w, h, d

        fontsize = prop.get_size_in_points()
        scale = float(fontsize) / self.FONT_SCALE

        if ismath:
            prop = prop.copy()
            prop.set_size(self.FONT_SCALE)

            width, height, descent, trash, used_characters = \
                self.mathtext_parser.parse(s, 72, prop)
            return width * scale, height * scale, descent * scale

        font = self._get_font(prop)
        font.set_char_size(self.FONT_SCALE, self.FONT_SCALE, self.DPI, self.DPI)
        layout = ft.Layout(font, s)
        w = layout.layout_bbox.width * scale
        h = layout.ink_bbox.height * scale
        d = -layout.ink_bbox.y_min * scale
        return w, h, d

    def get_text_path(self, prop, s, ismath=False, usetex=False):
        """
        convert text *s* to path (a tuple of vertices and codes for
        matplotlib.path.Path).

        *prop*
          font property

        *s*
          text to be converted

        *usetex*
          If True, use matplotlib usetex mode.

        *ismath*
          If True, use mathtext parser. Effective only if usetex == False.


        """
        if not usetex:
            if not ismath:
                font = self._get_font(prop)
                glyph_info, glyph_map, rects = self.get_glyphs_with_font(
                                                    font, s)
            else:
                glyph_info, glyph_map, rects = self.get_glyphs_mathtext(
                                                    prop, s)
        else:
            glyph_info, glyph_map, rects = self.get_glyphs_tex(prop, s)

        verts, codes = [], []

        for glyph_id, xposition, yposition, scale in glyph_info:
            verts1, codes1 = glyph_map[glyph_id]
            if len(verts1):
                verts1 = np.array(verts1) * scale + [xposition, yposition]
                verts.extend(verts1)
                codes.extend(codes1)

        for verts1, codes1 in rects:
            verts.extend(verts1)
            codes.extend(codes1)

        return verts, codes

    def get_glyphs_with_font(self, font, s, glyph_map=None,
                             return_new_glyphs_only=False):
        """
        convert the string *s* to vertices and codes using the
        provided ttf font.
        """

        if glyph_map is None:
            glyph_map = OrderedDict()

        if return_new_glyphs_only:
            glyph_map_new = OrderedDict()
        else:
            glyph_map_new = glyph_map

        layout = ft.Layout(font, s)

        result = []
        for gind, c, pos in zip(np.asarray(layout.glyph_indices), s,
                                np.asarray(layout.points)):
            ccode = ord(c)
            char_id = self._get_char_id(font, ccode)
            if char_id not in glyph_map:
                glyph = font.load_glyph(gind, ft.LOAD.NO_HINTING)
                glyph_map_new[char_id] = self.glyph_to_path(glyph)
            result.append((char_id, pos[0], pos[1], 1))

        return (result, glyph_map_new, [])

    def get_glyphs_mathtext(self, prop, s, glyph_map=None,
                            return_new_glyphs_only=False):
        """
        convert the string *s* to vertices and codes by parsing it with
        mathtext.
        """

        prop = prop.copy()
        prop.set_size(self.FONT_SCALE)

        width, height, descent, glyphs, rects = self.mathtext_parser.parse(
            s, self.DPI, prop)

        if not glyph_map:
            glyph_map = OrderedDict()

        if return_new_glyphs_only:
            glyph_map_new = OrderedDict()
        else:
            glyph_map_new = glyph_map

        xpositions = []
        ypositions = []
        glyph_ids = []
        sizes = []

        currx, curry = 0, 0
        for font, fontsize, ccode, ox, oy in glyphs:
            char_id = self._get_char_id(font, ccode)
            if char_id not in glyph_map:
                font.set_char_size(self.FONT_SCALE, self.FONT_SCALE, self.DPI, self.DPI)
                glyph = font.load_char_unicode(ccode, ft.LOAD.NO_HINTING)
                glyph_map_new[char_id] = self.glyph_to_path(glyph)

            xpositions.append(ox)
            ypositions.append(oy)
            glyph_ids.append(char_id)
            size = fontsize / self.FONT_SCALE
            sizes.append(size)

        myrects = []
        for ox, oy, w, h in rects:
            vert1 = [(ox, oy), (ox, oy + h), (ox + w, oy + h),
                     (ox + w, oy), (ox, oy), (0, 0)]
            code1 = [Path.MOVETO,
                     Path.LINETO, Path.LINETO, Path.LINETO, Path.LINETO,
                     Path.CLOSEPOLY]
            myrects.append((vert1, code1))

        return (list(zip(glyph_ids, xpositions, ypositions, sizes)),
                glyph_map_new, myrects)

    def get_texmanager(self):
        """
        return the :class:`matplotlib.texmanager.TexManager` instance
        """
        if self._texmanager is None:
            from matplotlib.texmanager import TexManager
            self._texmanager = TexManager()
        return self._texmanager

    def get_glyphs_tex(self, prop, s, glyph_map=None,
                       return_new_glyphs_only=False):
        """
        convert the string *s* to vertices and codes using matplotlib's usetex
        mode.
        """

        # codes are modstly borrowed from pdf backend.

        texmanager = self.get_texmanager()

        if self.tex_font_map is None:
            self.tex_font_map = dviread.PsfontsMap(
                                    dviread.find_tex_file('pdftex.map'))

        if self._adobe_standard_encoding is None:
            self._adobe_standard_encoding = self._get_adobe_standard_encoding()

        fontsize = prop.get_size_in_points()
        if hasattr(texmanager, "get_dvi"):
            dvifilelike = texmanager.get_dvi(s, self.FONT_SCALE)
            dvi = dviread.DviFromFileLike(dvifilelike, self.DPI)
        else:
            dvifile = texmanager.make_dvi(s, self.FONT_SCALE)
            dvi = dviread.Dvi(dvifile, self.DPI)
        with dvi:
            page = next(iter(dvi))

        if glyph_map is None:
            glyph_map = OrderedDict()

        if return_new_glyphs_only:
            glyph_map_new = OrderedDict()
        else:
            glyph_map_new = glyph_map

        glyph_ids, xpositions, ypositions, sizes = [], [], [], []

        # Gather font information and do some setup for combining
        # characters into strings.
        # oldfont, seq = None, []
        for x1, y1, dvifont, glyph, width in page.text:
            font_and_encoding = self._ps_fontd.get(dvifont.texname)
            font_bunch = self.tex_font_map[dvifont.texname]

            if font_and_encoding is None:
                font = get_font(font_bunch.filename)

                for charmap_name, charmap_code in [("ADOBE_CUSTOM",
                                                    1094992451),
                                                   ("ADOBE_STANDARD",
                                                    1094995778)]:
                    try:
                        font.select_charmap(charmap_code)
                    except (ValueError, RuntimeError):
                        pass
                    else:
                        break
                else:
                    charmap_name = ""
                    warnings.warn("No supported encoding in font (%s)." %
                                  font_bunch.filename)

                if charmap_name == "ADOBE_STANDARD" and font_bunch.encoding:
                    enc0 = dviread.Encoding(font_bunch.encoding)
                    enc = dict([(i, self._adobe_standard_encoding.get(c, None))
                                for i, c in enumerate(enc0.encoding)])
                else:
                    enc = dict()
                self._ps_fontd[dvifont.texname] = font, enc

            else:
                font, enc = font_and_encoding

            font_flag = ft.LOAD.TARGET_LIGHT

            char_id = self._get_char_id_ps(font, glyph)

            if char_id not in glyph_map:
                font.set_char_size(self.FONT_SCALE, self.FONT_SCALE,
                                   self.DPI, self.DPI)
                if enc:
                    charcode = enc.get(glyph, None)
                else:
                    charcode = glyph

                if charcode is not None:
                    glyph0 = font.load_char(charcode, load_flags=font_flag)
                else:
                    warnings.warn("The glyph (%d) of font (%s) cannot be "
                                  "converted with the encoding. Glyph may "
                                  "be wrong" % (glyph, font_bunch.filename))

                    glyph0 = font.load_char(glyph, load_flags=font_flag)

                glyph_map_new[char_id] = self.glyph_to_path(glyph0)

            glyph_ids.append(char_id)
            xpositions.append(x1)
            ypositions.append(y1)
            sizes.append(dvifont.size / self.FONT_SCALE)

        myrects = []

        for ox, oy, h, w in page.boxes:
            vert1 = [(ox, oy), (ox + w, oy), (ox + w, oy + h),
                     (ox, oy + h), (ox, oy), (0, 0)]
            code1 = [Path.MOVETO,
                     Path.LINETO, Path.LINETO, Path.LINETO, Path.LINETO,
                     Path.CLOSEPOLY]
            myrects.append((vert1, code1))

        return (list(zip(glyph_ids, xpositions, ypositions, sizes)),
                glyph_map_new, myrects)


text_to_path = TextToPath()


class TextPath(Path):
    """
    Create a path from the text.
    """

    def __init__(self, xy, s, size=None, prop=None,
                 _interpolation_steps=1, usetex=False,
                 *kl, **kwargs):
        """
        Create a path from the text. No support for TeX yet. Note that
        it simply is a path, not an artist. You need to use the
        PathPatch (or other artists) to draw this path onto the
        canvas.

        xy : position of the text.
        s : text
        size : font size
        prop : font property
        """

        if prop is None:
            prop = FontProperties()

        if size is None:
            size = prop.get_size_in_points()

        self._xy = xy
        self.set_size(size)

        self._cached_vertices = None

        self._vertices, self._codes = self.text_get_vertices_codes(
                                            prop, s,
                                            usetex=usetex)

        self._should_simplify = False
        self._simplify_threshold = rcParams['path.simplify_threshold']
        self._has_nonfinite = False
        self._interpolation_steps = _interpolation_steps

    def set_size(self, size):
        """
        set the size of the text
        """
        self._size = size
        self._invalid = True

    def get_size(self):
        """
        get the size of the text
        """
        return self._size

    def _get_vertices(self):
        """
        Return the cached path after updating it if necessary.
        """
        self._revalidate_path()
        return self._cached_vertices

    def _get_codes(self):
        """
        Return the codes
        """
        return self._codes

    vertices = property(_get_vertices)
    codes = property(_get_codes)

    def _revalidate_path(self):
        """
        update the path if necessary.

        The path for the text is initially create with the font size
        of FONT_SCALE, and this path is rescaled to other size when
        necessary.

        """
        if (self._invalid or
            (self._cached_vertices is None)):
            tr = Affine2D().scale(
                    self._size / text_to_path.FONT_SCALE,
                    self._size / text_to_path.FONT_SCALE).translate(*self._xy)
            self._cached_vertices = tr.transform(self._vertices)
            self._invalid = False

    def is_math_text(self, s):
        """
        Returns True if the given string *s* contains any mathtext.
        """
        # copied from Text.is_math_text -JJL

        # Did we find an even number of non-escaped dollar signs?
        # If so, treat is as math text.
        dollar_count = s.count(r'$') - s.count(r'\$')
        even_dollars = (dollar_count > 0 and dollar_count % 2 == 0)

        if rcParams['text.usetex']:
            return s, 'TeX'

        if even_dollars:
            return s, True
        else:
            return s.replace(r'\$', '$'), False

    def text_get_vertices_codes(self, prop, s, usetex):
        """
        convert the string *s* to vertices and codes using the
        provided font property *prop*. Mostly copied from
        backend_svg.py.
        """

        if usetex:
            verts, codes = text_to_path.get_text_path(prop, s, usetex=True)
        else:
            clean_line, ismath = self.is_math_text(s)
            verts, codes = text_to_path.get_text_path(prop, clean_line,
                                                      ismath=ismath)

        return verts, codes
