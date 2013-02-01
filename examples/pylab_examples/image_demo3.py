#!/usr/bin/env python
from pylab import *
try:
    from PIL import Image
except ImportError:
    raise SystemExit("PIL must be installed to run this example")

import matplotlib.utils as utils

datafile = cbook.get_sample_data('grace_hopper.jpg')
lena = Image.open(datafile)
dpi = rcParams['figure.dpi']
figsize = lena.size[0]/dpi, lena.size[1]/dpi

figure(figsize=figsize)
ax = axes([0,0,1,1], frameon=False)
ax.set_axis_off()
im = imshow(lena)

show()

