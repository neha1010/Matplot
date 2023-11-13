``violinplot`` now accepts color arguments
-------------------------------------------

The ``~.Axes.violinplot`` constructor now accepts ``color``, ``facecolor``, and
``edgecolor`` as input arguments. This means that users can set the color of
violinplots as they make them, rather than setting the color of individual objects
afterwards. It is possible to pass a single color to be used for all violins, or pass
a sequence of colors.
