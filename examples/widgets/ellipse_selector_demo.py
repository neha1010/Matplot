"""
=====================
Ellipse Selector Demo
=====================

Interactively selecting data in a region of interest in an image by drawing an ellipse.

This example plots an image. You can then draw an ellipse shaped selection. To draw,
click and drag to an extent within the image and then release.
"""

import numpy as np

from matplotlib.patches import Ellipse
from matplotlib.widgets import EllipseSelector


class EllipseROIStats(object):
    """
    Select a region of an image using 'EllipseSelector' and extract the data.
    
    The extents and center of the ellipse drawn are used to create a patch 
    in the same area as the selector object. The patch is the then used to 
    generate a mask that can be used to extract data.

    Parameters
    ----------
    axis: `~matplotlib.axes.Axes`: Axes to interact with
    fig: `~matplotlib.figure.Figure`: Figure on which to draw
    fig_shape: `~matplotlib.ndarray`: Array containing image dimensions
    img_data: `~matplotlib.ndarray`: Image array
    """

    def __init__(self, axis, fig, fig_shape, img_data):
        self.ax = axis
        self.fig = fig

        lineprop = dict(color = 'black', linestyle="-.", linewidth=2, alpha=1.0)
        state_mods = dict(move=' ', clear='escape')
        self.ellipse_roi = EllipseSelector(self.ax, onselect=self.on_select,
                                           drawtype='line', lineprops=lineprop,
                                           state_modifier_keys=state_mods,
                                           interactive=True)
        self.fig_shape = fig_shape
        self.img = img_data


    def on_select(self, eclick, erelease):
        "eclick and erelease are matplotlib events at press and release."

        # Starting and ending column indicies
        self.x_start = eclick.xdata
        self.x_end = erelease.xdata

        # Starting and ending row indicies
        self.y_start = eclick.ydata
        self.y_end = erelease.ydata

        # Keep user from changing the points
        # chosen.
        extents = [self.x_start, self.x_end, \
                   self.y_start, self.y_end]
        self.ellipse_roi.draw_shape(extents)

        # Parameters of the ellipse drawn
        width = self.x_end - self.x_start
        height = self.y_end - self.y_start
        center = self.ellipse_roi.center

        # Instantiate a Patch object that matches
        # that of the drawn ellipse.
        ellipse = Ellipse(xy=center, width=width, height=height)
        ellipse.set_fill(False)

        # Attributes of the Ellipse-patch object
        self.transform = ellipse.get_patch_transform()
        self.ellipse_path = ellipse.get_path()

        # Place elliptical patch in the region of the image
        # it was drawn
        self.ax.add_patch(ellipse)

        # Generate a set of x and y coordinates that
        # will be used to fill a mask image.
        m, n = self.fig_shape
        x, y = np.meshgrid(np.arange(m), np.arange(n))
        x, y = x.flatten(), y.flatten()
        points = np.vstack((x, y)).T

        # Check if each point in the coordinates given
        # fall within the elliptical path drawn
        self.mask = self.ellipse_path.contains_points \
            (points, self.transform).reshape((m,n))

        self.masked_vals = self.img[self.mask]
    
    def toggle_selector(self, event):
        if (event.key == "enter") and self.ellipse_roi.active:

            self.ax.lines.clear()
            self.ax.patches.clear()
            self.fig.canvas.draw_idle()
            
            mean = np.mean(self.masked_vals)
            median = np.median(self.masked_vals)
            std = np.std(self.masked_vals)
            print(f'mean:   {mean}\n')
            print(f'median: {median}\n')
            print(f'std.:   {std}\n')

        if event.key in ['Q', 'q'] and not self.ellipse_roi.active:
            print('\nEllipseSelector deactivated.\n')
            self.ellipse_roi.set_active(False)
            
        if event.key in ['A', 'a'] and not self.ellipse_roi.active:
            print('\nEllipseSelector activated.\n')
            self.ellipse_roi.set_active(True)



if __name__ == '__main__':
    import matplotlib.pyplot as plt

    # Fixing random state for reproducibility
    np.random.seed(18492187)
    
    random_im = np.random.rand(48, 48)

    fig, axis = plt.subplots(1, 1, figsize=(7, 7))

    shown_fig = axis.imshow(random_im, interpolation='bilinear')
    fig_shape = random_im.shape

    selector = EllipseROIStats(axis, fig, fig_shape, random_im)
            

    shown_fig.figure.canvas.mpl_connect('key_press_event', \
                                        selector.toggle_selector)
    axis.set_title("Press enter to show descriptive statistics.")

    plt.show()
