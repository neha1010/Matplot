r"""

.. redirect-from:: /tutorials/text/mathtext

.. _mathtext:

Writing mathematical expressions
================================

Matplotlib implements a lightweight TeX expression parser and layout engine and
*Mathtext* is the subset of Tex markup that this engine supports. Note that
Matplotlib can also render all text directly using TeX if :rc:`text.usetex` is
*True*; see :ref:`usetex` for more details.   Mathtext support is available
if :rc:`text.usetex` is *False*.

Any string can be processed as Mathtext by placing the string inside a pair of
dollar signs ``'$'``. Mathtext often contains many backslashes ``'\'``; so that
the backslashes do not need to be escaped, Mathtext is often written using raw
strings. For example:
"""

import matplotlib.pyplot as plt

fig = plt.figure(figsize=(3, 3), linewidth=1, edgecolor='black')
fig.text(.2, .7, "plain text: alpha > beta")
fig.text(.2, .5, "Mathtext: $\\alpha > \\beta$")
fig.text(.2, .3, r"raw string Mathtext: $\alpha > \beta$")

# %%
# .. seealso::
#
#   :doc:`Mathtext example </gallery/text_labels_and_annotations/mathtext_demo>`
#
# TeX does *not* need to be installed to use Mathtext because Matplotlib ships
# with the Mathtext parser and engine. The Mathtext layout engine is a fairly
# direct adaptation of the layout algorithms in Donald Knuth's TeX. To render
# mathematical text using a different TeX engine, see :ref:`usetex`.
#
# .. note::
#   To generate html output in documentation that will exactly match the output
#   generated by ``mathtext``, use the `matplotlib.sphinxext.mathmpl` Sphinx
#   extension.
#
#
# Special characters
# ------------------
#
# Mathtext must be placed between a pair of (US) dollar signs ``'$'``. A literal
# dollar symbol ``'$'`` in a string containing Mathtext must be escaped using a
# backslash: ``'\$'``. A string may contain multiple pairs of dollar signs,
# resulting in multiple Mathtext expressions. Strings with an odd number of
# dollar signs are rendered solely as plain text.

fig = plt.figure(figsize=(3, 3), linewidth=1, edgecolor='black')
fig.suptitle("Number of unescaped $")
fig.text(.1, .7, r"odd: $ \alpha $ = $1")
fig.text(.1, .5, r"even: $ \beta $= $ 2 $")
fig.text(.1, .3, r'odd: $ \gamma $= \$3 $')
fig.text(.1, .1, r'even: $ \delta $ = $ \$4 $')

# %%
# While Mathtext aims for compatibility with regular TeX, it diverges on when
# special characters need to be escaped. In TeX the dollar sign must be escaped
# ``'\$'`` in non-math text, while in Matplotlib the dollar sign must be
# escaped when writing Mathtext.
#
# These other special characters are also escaped in non-math TeX, while in
# Matplotlib their behavior is dependent on how :rc:`text.usetex` is set::
#
#    # $ % & ~ _ ^ \ { } \( \) \[ \]
#
# See the :ref:`usetex tutorial <usetex>` for more information.
#
#
# Subscripts and superscripts
# ---------------------------
# To make subscripts and superscripts, use the ``'_'`` and ``'^'`` symbols::
#
#     r'$\alpha_i > \beta_i$'
#
# .. math::
#
#     \alpha_i > \beta_i
#
# To display multi-letter subscripts or superscripts correctly,
# you should put them in curly braces ``{...}``::
#
#     r'$\alpha^{ic} > \beta_{ic}$'
#
# .. math::
#
#     \alpha^{ic} > \beta_{ic}
#
# Some symbols automatically put their sub/superscripts under and over the
# operator.  For example, to write the sum of :mathmpl:`x_i` from :mathmpl:`0` to
# :mathmpl:`\infty`, you could do::
#
#     r'$\sum_{i=0}^\infty x_i$'
#
# .. math::
#
#     \sum_{i=0}^\infty x_i
#
# Fractions, binomials, and stacked numbers
# -----------------------------------------
# Fractions, binomials, and stacked numbers can be created with the
# ``\frac{}{}``, ``\binom{}{}`` and ``\genfrac{}{}{}{}{}{}`` commands,
# respectively::
#
#     r'$\frac{3}{4} \binom{3}{4} \genfrac{}{}{0}{}{3}{4}$'
#
# produces
#
# .. math::
#
#     \frac{3}{4} \binom{3}{4} \genfrac{}{}{0pt}{}{3}{4}
#
# Fractions can be arbitrarily nested::
#
#     r'$\frac{5 - \frac{1}{x}}{4}$'
#
# produces
#
# .. math::
#
#     \frac{5 - \frac{1}{x}}{4}
#
# Note that special care needs to be taken to place parentheses and brackets
# around fractions.  Doing things the obvious way produces brackets that are too
# small::
#
#     r'$(\frac{5 - \frac{1}{x}}{4})$'
#
# .. math::
#
#     (\frac{5 - \frac{1}{x}}{4})
#
# The solution is to precede the bracket with ``\left`` and ``\right`` to inform
# the parser that those brackets encompass the entire object.::
#
#     r'$\left(\frac{5 - \frac{1}{x}}{4}\right)$'
#
# .. math::
#
#     \left(\frac{5 - \frac{1}{x}}{4}\right)
#
# Radicals
# --------
# Radicals can be produced with the ``\sqrt[]{}`` command.  For example::
#
#     r'$\sqrt{2}$'
#
# .. math::
#
#     \sqrt{2}
#
# Any base can (optionally) be provided inside square brackets.  Note that the
# base must be a simple expression, and cannot contain layout commands such as
# fractions or sub/superscripts::
#
#     r'$\sqrt[3]{x}$'
#
# .. math::
#
#     \sqrt[3]{x}
#
# .. _mathtext-fonts:
#
# Fonts
# -----
#
# The default font is *italics* for mathematical symbols.
#
# This default can be changed using :rc:`mathtext.default`. For setting rcParams,
# see :ref:`customizing`. For example, setting the default to ``regular`` allows
# you to use the same font for math text and regular non-math text.
#
# To change fonts, e.g., to write "sin" in a Roman font, enclose the text in a
# font command::
#
#     r'$s(t) = \mathcal{A}\mathrm{sin}(2 \omega t)$'
#
# .. math::
#
#     s(t) = \mathcal{A}\mathrm{sin}(2 \omega t)
#
# More conveniently, many commonly used function names that are typeset in
# a Roman font have shortcuts.  So the expression above could be written as
# follows::
#
#     r'$s(t) = \mathcal{A}\sin(2 \omega t)$'
#
# .. math::
#
#     s(t) = \mathcal{A}\sin(2 \omega t)
#
# Here "s" and "t" are variable in italics font (default), "sin" is in Roman
# font, and the amplitude "A" is in calligraphy font.  Note in the example above
# the calligraphy ``A`` is squished into the ``sin``.  You can use a spacing
# command to add a little whitespace between them::
#
#     r's(t) = \mathcal{A}\/\sin(2 \omega t)'
#
# .. Here we cheat a bit: for HTML math rendering, Sphinx relies on MathJax which
#    doesn't actually support the italic correction (\/); instead, use a thin
#    space (\,) which is supported.
#
# .. math::
#
#     s(t) = \mathcal{A}\,\sin(2 \omega t)
#
# Mathtext can use DejaVu Sans (default), DejaVu Serif, Computer Modern fonts
# from (La)TeX, `STIX <http://www.stixfonts.org/>`_ fonts which are designed
# to blend well with Times, or a Unicode font that you provide. The Mathtext
# font can be selected via :rc:`mathtext.fontset`.
#
# The choices available with all fonts are:
#
# ========================= ================================
# Command                   Result
# ========================= ================================
# ``\mathrm{Roman}``        :mathmpl:`\mathrm{Roman}`
# ``\mathit{Italic}``       :mathmpl:`\mathit{Italic}`
# ``\mathtt{Typewriter}``   :mathmpl:`\mathtt{Typewriter}`
# ``\mathcal{CALLIGRAPHY}`` :mathmpl:`\mathcal{CALLIGRAPHY}`
# ========================= ================================
#
# .. rstcheck: ignore-directives=role
# .. role:: math-stix(mathmpl)
#    :fontset: stix
#
# When using the `STIX <http://www.stixfonts.org/>`_ fonts, you also have the
# choice of:
#
# ================================ =========================================
# Command                          Result
# ================================ =========================================
# ``\mathbb{blackboard}``          :math-stix:`\mathbb{blackboard}`
# ``\mathrm{\mathbb{blackboard}}`` :math-stix:`\mathrm{\mathbb{blackboard}}`
# ``\mathfrak{Fraktur}``           :math-stix:`\mathfrak{Fraktur}`
# ``\mathsf{sansserif}``           :math-stix:`\mathsf{sansserif}`
# ``\mathrm{\mathsf{sansserif}}``  :math-stix:`\mathrm{\mathsf{sansserif}}`
# ``\mathbfit{bolditalic}``        :math-stix:`\mathbfit{bolditalic}`
# ================================ =========================================
#
# There are also five global "font sets" to choose from, which are
# selected using the ``mathtext.fontset`` parameter in :ref:`matplotlibrc
# <matplotlibrc-sample>`.
#
# ``dejavusans``: DejaVu Sans
#     .. mathmpl::
#        :fontset: dejavusans
#
#        \mathcal{R} \prod_{i=\alpha}^{\infty} a_i \sin\left(2\pi fx_i\right)
#
# ``dejavuserif``: DejaVu Serif
#     .. mathmpl::
#        :fontset: dejavuserif
#
#        \mathcal{R} \prod_{i=\alpha}^{\infty} a_i \sin\left(2\pi fx_i\right)
#
# ``cm``: Computer Modern (TeX)
#     .. mathmpl::
#        :fontset: cm
#
#        \mathcal{R} \prod_{i=\alpha}^{\infty} a_i \sin\left(2\pi fx_i\right)
#
# ``stix``: STIX (designed to blend well with Times)
#     .. mathmpl::
#        :fontset: stix
#
#        \mathcal{R} \prod_{i=\alpha}^{\infty} a_i \sin\left(2\pi fx_i\right)
#
# ``stixsans``: STIX sans-serif
#     .. mathmpl::
#        :fontset: stixsans
#
#        \mathcal{R} \prod_{i=\alpha}^{\infty} a_i \sin\left(2\pi fx_i\right)
#
# Additionally, you can use ``\mathdefault{...}`` or its alias
# ``\mathregular{...}`` to use the font used for regular text outside of
# Mathtext.  There are a number of limitations to this approach, most notably
# that far fewer symbols will be available, but it can be useful to make math
# expressions blend well with other text in the plot.
#
# For compatibility with popular packages, ``\text{...}`` is available and uses the
# ``\mathrm{...}`` font, but otherwise retains spaces and renders - as a dash
# (not minus).
#
# Custom fonts
# ~~~~~~~~~~~~
# Mathtext also provides a way to use custom fonts for math.  This method is
# fairly tricky to use, and should be considered an experimental feature for
# patient users only.  By setting :rc:`mathtext.fontset` to ``custom``,
# you can then set the following parameters, which control which font file to use
# for a particular set of math characters.
#
# ============================== =================================
# Parameter                      Corresponds to
# ============================== =================================
# ``mathtext.it``                ``\mathit{}`` or default italic
# ``mathtext.rm``                ``\mathrm{}`` Roman (upright)
# ``mathtext.tt``                ``\mathtt{}`` Typewriter (monospace)
# ``mathtext.bf``                ``\mathbf{}`` bold
# ``mathtext.bfit``              ``\mathbfit{}`` bold italic
# ``mathtext.cal``               ``\mathcal{}`` calligraphic
# ``mathtext.sf``                ``\mathsf{}`` sans-serif
# ============================== =================================
#
# Each parameter should be set to a fontconfig font descriptor, as defined in
# :ref:`fonts`. The fonts used should have a Unicode mapping in order to find
# any non-Latin characters, such as Greek.  If you want to use a math symbol
# that is not contained in your custom fonts, you can set
# :rc:`mathtext.fallback` to either ``'cm'``, ``'stix'`` or ``'stixsans'``
# which will cause the Mathtext system to use
# characters from an alternative font whenever a particular
# character cannot be found in the custom font.
#
# Note that the math glyphs specified in Unicode have evolved over time, and
# many fonts may not have glyphs in the correct place for Mathtext.
#
# Accents
# -------
# An accent command may precede any symbol to add an accent above it.  There are
# long and short forms for some of them.
#
# ============================== =================================
# Command                        Result
# ============================== =================================
# ``\acute a`` or ``\'a``        :mathmpl:`\acute a`
# ``\bar a``                     :mathmpl:`\bar a`
# ``\breve a``                   :mathmpl:`\breve a`
# ``\dot a`` or ``\.a``          :mathmpl:`\dot a`
# ``\ddot a`` or ``\''a``        :mathmpl:`\ddot a`
# ``\dddot a``                   :mathmpl:`\dddot a`
# ``\ddddot a``                  :mathmpl:`\ddddot a`
# ``\grave a`` or ``\`a``        :mathmpl:`\grave a`
# ``\hat a`` or ``\^a``          :mathmpl:`\hat a`
# ``\tilde a`` or ``\~a``        :mathmpl:`\tilde a`
# ``\vec a``                     :mathmpl:`\vec a`
# ``\overline{abc}``             :mathmpl:`\overline{abc}`
# ============================== =================================
#
# In addition, there are two special accents that automatically adjust to the
# width of the symbols below:
#
# ============================== =================================
# Command                        Result
# ============================== =================================
# ``\widehat{xyz}``              :mathmpl:`\widehat{xyz}`
# ``\widetilde{xyz}``            :mathmpl:`\widetilde{xyz}`
# ============================== =================================
#
# Care should be taken when putting accents on lower-case i's and j's.  Note
# that in the following ``\imath`` is used to avoid the extra dot over the i::
#
#     r"$\hat i\ \ \hat \imath$"
#
# .. math::
#
#     \hat i\ \ \hat \imath
#
# Symbols
# -------
# You can also use a large number of the TeX symbols, as in ``\infty``,
# ``\leftarrow``, ``\sum``, ``\int``.
#
# .. math_symbol_table::
#
# If a particular symbol does not have a name (as is true of many of the more
# obscure symbols in the STIX fonts), Unicode characters can also be used::
#
#    r'$\u23ce$'
