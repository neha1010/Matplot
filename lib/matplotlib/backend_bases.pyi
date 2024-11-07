from enum import Enum, IntEnum
import os
from matplotlib import (
    cbook,
    transforms,
    widgets,
    _api,
)
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backend_managers import ToolManager
from matplotlib.backend_tools import Cursors, ToolBase
from matplotlib.colorbar import Colorbar
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path
from matplotlib.texmanager import TexManager
from matplotlib.text import Text
from matplotlib.transforms import Bbox, BboxBase, Transform, TransformedPath

from collections.abc import Callable, Iterable, Sequence
from typing import Any, IO, Literal, NamedTuple, TypeVar
from numpy.typing import ArrayLike
from .typing import ColorType, LineStyleType, CapStyleType, JoinStyleType

def register_backend(
    format: str, backend: str | type[FigureCanvasBase], description: str | None = ...
) -> None: ...
def get_registered_canvas_class(format: str) -> type[FigureCanvasBase]: ...

class RendererBase:
    def __init__(self) -> None: ...
    def open_group(self, s: str, gid: str | None = ...) -> None: ...
    def close_group(self, s: str) -> None: ...
    def draw_path(
        self,
        gc: GraphicsContextBase,
        path: Path,
        transform: Transform,
        rgbFace: ColorType | None = ...,
    ) -> None: ...
    def draw_markers(
        self,
        gc: GraphicsContextBase,
        marker_path: Path,
        marker_trans: Transform,
        path: Path,
        trans: Transform,
        rgbFace: ColorType | None = ...,
    ) -> None: ...
    def draw_path_collection(
        self,
        gc: GraphicsContextBase,
        master_transform: Transform,
        paths: Sequence[Path],
        all_transforms: Sequence[ArrayLike],
        offsets: ArrayLike | Sequence[ArrayLike],
        offset_trans: Transform,
        facecolors: ColorType | Sequence[ColorType],
        edgecolors: ColorType | Sequence[ColorType],
        linewidths: float | Sequence[float],
        linestyles: LineStyleType | Sequence[LineStyleType],
        antialiaseds: bool | Sequence[bool],
        urls: str | Sequence[str],
        offset_position: Any,
    ) -> None: ...
    def draw_quad_mesh(
        self,
        gc: GraphicsContextBase,
        master_transform: Transform,
        meshWidth,
        meshHeight,
        coordinates: ArrayLike,
        offsets: ArrayLike | Sequence[ArrayLike],
        offsetTrans: Transform,
        facecolors: Sequence[ColorType],
        antialiased: bool,
        edgecolors: Sequence[ColorType] | ColorType | None,
    ) -> None: ...
    def draw_gouraud_triangles(
        self,
        gc: GraphicsContextBase,
        triangles_array: ArrayLike,
        colors_array: ArrayLike,
        transform: Transform,
    ) -> None: ...
    def get_image_magnification(self) -> float: ...
    def draw_image(
        self,
        gc: GraphicsContextBase,
        x: float,
        y: float,
        im: ArrayLike,
        transform: transforms.Affine2DBase | None = ...,
    ) -> None: ...
    def option_image_nocomposite(self) -> bool: ...
    def option_scale_image(self) -> bool: ...
    def draw_tex(
        self,
        gc: GraphicsContextBase,
        x: float,
        y: float,
        s: str,
        prop: FontProperties,
        angle: float,
        *,
        mtext: Text | None = ...
    ) -> None: ...
    def draw_text(
        self,
        gc: GraphicsContextBase,
        x: float,
        y: float,
        s: str,
        prop: FontProperties,
        angle: float,
        ismath: bool | Literal["TeX"] = ...,
        mtext: Text | None = ...,
    ) -> None: ...
    def get_text_width_height_descent(
        self, s: str, prop: FontProperties, ismath: bool | Literal["TeX"]
    ) -> tuple[float, float, float]: ...
    def flipy(self) -> bool: ...
    def get_canvas_width_height(self) -> tuple[float, float]: ...
    def get_texmanager(self) -> TexManager: ...
    def new_gc(self) -> GraphicsContextBase: ...
    def points_to_pixels(self, points: ArrayLike) -> ArrayLike: ...
    def start_rasterizing(self) -> None: ...
    def stop_rasterizing(self) -> None: ...
    def start_filter(self) -> None: ...
    def stop_filter(self, filter_func) -> None: ...

class GraphicsContextBase:
    def __init__(self) -> None: ...
    def copy_properties(self, gc: GraphicsContextBase) -> None: ...
    def restore(self) -> None: ...
    def get_alpha(self) -> float: ...
    def get_antialiased(self) -> int: ...
    def get_capstyle(self) -> Literal["butt", "projecting", "round"]: ...
    def get_clip_rectangle(self) -> Bbox | None: ...
    def get_clip_path(
        self,
    ) -> tuple[TransformedPath, Transform] | tuple[None, None]: ...
    def get_dashes(self) -> tuple[float, ArrayLike | None]: ...
    def get_forced_alpha(self) -> bool: ...
    def get_joinstyle(self) -> Literal["miter", "round", "bevel"]: ...
    def get_linewidth(self) -> float: ...
    def get_rgb(self) -> tuple[float, float, float, float]: ...
    def get_url(self) -> str | None: ...
    def get_gid(self) -> int | None: ...
    def get_snap(self) -> bool | None: ...
    def set_alpha(self, alpha: float) -> None: ...
    def set_antialiased(self, b: bool) -> None: ...
    def set_capstyle(self, cs: CapStyleType) -> None: ...
    def set_clip_rectangle(self, rectangle: Bbox | None) -> None: ...
    def set_clip_path(self, path: TransformedPath | None) -> None: ...
    def set_dashes(self, dash_offset: float, dash_list: ArrayLike | None) -> None: ...
    def set_foreground(self, fg: ColorType, isRGBA: bool = ...) -> None: ...
    def set_joinstyle(self, js: JoinStyleType) -> None: ...
    def set_linewidth(self, w: float) -> None: ...
    def set_url(self, url: str | None) -> None: ...
    def set_gid(self, id: int | None) -> None: ...
    def set_snap(self, snap: bool | None) -> None: ...
    def set_hatch(self, hatch: str | None) -> None: ...
    def get_hatch(self) -> str | None: ...
    def get_hatch_path(self, density: float = ...) -> Path: ...
    def get_hatch_color(self) -> ColorType: ...
    def set_hatch_color(self, hatch_color: ColorType) -> None: ...
    def get_hatch_linewidth(self) -> float: ...
    def set_hatch_linewidth(self, hatch_linewidth: float) -> None: ...
    def get_sketch_params(self) -> tuple[float, float, float] | None: ...
    def set_sketch_params(
        self,
        scale: float | None = ...,
        length: float | None = ...,
        randomness: float | None = ...,
    ) -> None: ...

class TimerBase:
    callbacks: list[tuple[Callable, tuple, dict[str, Any]]]
    def __init__(
        self,
        interval: int | None = ...,
        callbacks: list[tuple[Callable, tuple, dict[str, Any]]] | None = ...,
    ) -> None: ...
    def __del__(self) -> None: ...
    def start(self, interval: int | None = ...) -> None: ...
    def stop(self) -> None: ...
    @property
    def interval(self) -> int: ...
    @interval.setter
    def interval(self, interval: int) -> None: ...
    @property
    def single_shot(self) -> bool: ...
    @single_shot.setter
    def single_shot(self, ss: bool) -> None: ...
    def add_callback(self, func: Callable, *args, **kwargs) -> Callable: ...
    def remove_callback(self, func: Callable, *args, **kwargs) -> None: ...

class Event:
    name: str
    canvas: FigureCanvasBase
    guiEvent: Any
    def __init__(
        self, name: str, canvas: FigureCanvasBase, guiEvent: Any | None = ...
    ) -> None: ...

class DrawEvent(Event):
    renderer: RendererBase
    def __init__(
        self, name: str, canvas: FigureCanvasBase, renderer: RendererBase
    ) -> None: ...

class ResizeEvent(Event):
    width: int
    height: int
    def __init__(self, name: str, canvas: FigureCanvasBase) -> None: ...

class CloseEvent(Event): ...

class LocationEvent(Event):
    x: int
    y: int
    inaxes: Axes | None
    xdata: float | None
    ydata: float | None
    def __init__(
        self,
        name: str,
        canvas: FigureCanvasBase,
        x: int,
        y: int,
        guiEvent: Any | None = ...,
        *,
        modifiers: Iterable[str] | None = ...,
    ) -> None: ...

class MouseButton(IntEnum):
    LEFT: int
    MIDDLE: int
    RIGHT: int
    BACK: int
    FORWARD: int

class MouseEvent(LocationEvent):
    button: MouseButton | Literal["up", "down"] | None
    key: str | None
    step: float
    dblclick: bool
    def __init__(
        self,
        name: str,
        canvas: FigureCanvasBase,
        x: int,
        y: int,
        button: MouseButton | Literal["up", "down"] | None = ...,
        key: str | None = ...,
        step: float = ...,
        dblclick: bool = ...,
        guiEvent: Any | None = ...,
        *,
        buttons: Iterable[MouseButton] | None = ...,
        modifiers: Iterable[str] | None = ...,
    ) -> None: ...

class PickEvent(Event):
    mouseevent: MouseEvent
    artist: Artist
    def __init__(
        self,
        name: str,
        canvas: FigureCanvasBase,
        mouseevent: MouseEvent,
        artist: Artist,
        guiEvent: Any | None = ...,
        **kwargs
    ) -> None: ...

class KeyEvent(LocationEvent):
    key: str | None
    def __init__(
        self,
        name: str,
        canvas: FigureCanvasBase,
        key: str | None,
        x: int = ...,
        y: int = ...,
        guiEvent: Any | None = ...,
    ) -> None: ...

class FigureCanvasBase:
    required_interactive_framework: str | None

    @_api.classproperty
    def manager_class(cls) -> type[FigureManagerBase]: ...
    events: list[str]
    fixed_dpi: None | float
    filetypes: dict[str, str]

    @_api.classproperty
    def supports_blit(cls) -> bool: ...

    figure: Figure
    manager: None | FigureManagerBase
    widgetlock: widgets.LockDraw
    mouse_grabber: None | Axes
    toolbar: None | NavigationToolbar2
    def __init__(self, figure: Figure | None = ...) -> None: ...
    @property
    def callbacks(self) -> cbook.CallbackRegistry: ...
    @property
    def button_pick_id(self) -> int: ...
    @property
    def scroll_pick_id(self) -> int: ...
    @classmethod
    def new_manager(cls, figure: Figure, num: int | str) -> FigureManagerBase: ...
    def is_saving(self) -> bool: ...
    def blit(self, bbox: BboxBase | None = ...) -> None: ...
    def inaxes(self, xy: tuple[float, float]) -> Axes | None: ...
    def grab_mouse(self, ax: Axes) -> None: ...
    def release_mouse(self, ax: Axes) -> None: ...
    def set_cursor(self, cursor: Cursors) -> None: ...
    def draw(self, *args, **kwargs) -> None: ...
    def draw_idle(self, *args, **kwargs) -> None: ...
    @property
    def device_pixel_ratio(self) -> float: ...
    def get_width_height(self, *, physical: bool = ...) -> tuple[int, int]: ...
    @classmethod
    def get_supported_filetypes(cls) -> dict[str, str]: ...
    @classmethod
    def get_supported_filetypes_grouped(cls) -> dict[str, list[str]]: ...
    def print_figure(
        self,
        filename: str | os.PathLike | IO,
        dpi: float | None = ...,
        facecolor: ColorType | Literal["auto"] | None = ...,
        edgecolor: ColorType | Literal["auto"] | None = ...,
        orientation: str = ...,
        format: str | None = ...,
        *,
        bbox_inches: Literal["tight"] | Bbox | None = ...,
        pad_inches: float | None = ...,
        bbox_extra_artists: list[Artist] | None = ...,
        backend: str | None = ...,
        **kwargs
    ) -> Any: ...
    @classmethod
    def get_default_filetype(cls) -> str: ...
    def get_default_filename(self) -> str: ...
    _T = TypeVar("_T", bound=FigureCanvasBase)
    def mpl_connect(self, s: str, func: Callable[[Event], Any]) -> int: ...
    def mpl_disconnect(self, cid: int) -> None: ...
    def new_timer(
        self,
        interval: int | None = ...,
        callbacks: list[tuple[Callable, tuple, dict[str, Any]]] | None = ...,
    ) -> TimerBase: ...
    def flush_events(self) -> None: ...
    def start_event_loop(self, timeout: float = ...) -> None: ...
    def stop_event_loop(self) -> None: ...

def key_press_handler(
    event: KeyEvent,
    canvas: FigureCanvasBase | None = ...,
    toolbar: NavigationToolbar2 | None = ...,
) -> None: ...
def button_press_handler(
    event: MouseEvent,
    canvas: FigureCanvasBase | None = ...,
    toolbar: NavigationToolbar2 | None = ...,
) -> None: ...

class NonGuiException(Exception): ...

class FigureManagerBase:
    canvas: FigureCanvasBase
    num: int | str
    key_press_handler_id: int | None
    button_press_handler_id: int | None
    toolmanager: ToolManager | None
    toolbar: NavigationToolbar2 | ToolContainerBase | None
    def __init__(self, canvas: FigureCanvasBase, num: int | str) -> None: ...
    @classmethod
    def create_with_canvas(
        cls, canvas_class: type[FigureCanvasBase], figure: Figure, num: int | str
    ) -> FigureManagerBase: ...
    @classmethod
    def start_main_loop(cls) -> None: ...
    @classmethod
    def pyplot_show(cls, *, block: bool | None = ...) -> None: ...
    def show(self) -> None: ...
    def destroy(self) -> None: ...
    def full_screen_toggle(self) -> None: ...
    def resize(self, w: int, h: int) -> None: ...
    def get_window_title(self) -> str: ...
    def set_window_title(self, title: str) -> None: ...

cursors = Cursors

class _Mode(str, Enum):
    NONE: str
    PAN: str
    ZOOM: str

class NavigationToolbar2:
    toolitems: tuple[tuple[str, ...] | tuple[None, ...], ...]
    UNKNOWN_SAVED_STATUS: object
    canvas: FigureCanvasBase
    mode: _Mode
    def __init__(self, canvas: FigureCanvasBase) -> None: ...
    def set_message(self, s: str) -> None: ...
    def draw_rubberband(
        self, event: Event, x0: float, y0: float, x1: float, y1: float
    ) -> None: ...
    def remove_rubberband(self) -> None: ...
    def home(self, *args) -> None: ...
    def back(self, *args) -> None: ...
    def forward(self, *args) -> None: ...
    def mouse_move(self, event: MouseEvent) -> None: ...
    def pan(self, *args) -> None: ...

    class _PanInfo(NamedTuple):
        button: MouseButton
        axes: list[Axes]
        cid: int
    def press_pan(self, event: Event) -> None: ...
    def drag_pan(self, event: Event) -> None: ...
    def release_pan(self, event: Event) -> None: ...
    def zoom(self, *args) -> None: ...

    class _ZoomInfo(NamedTuple):
        button: MouseButton
        start_xy: tuple[float, float]
        axes: list[Axes]
        cid: int
        cbar: Colorbar
    def press_zoom(self, event: Event) -> None: ...
    def drag_zoom(self, event: Event) -> None: ...
    def release_zoom(self, event: Event) -> None: ...
    def push_current(self) -> None: ...
    subplot_tool: widgets.SubplotTool
    def configure_subplots(self, *args): ...
    def save_figure(self, *args) -> str | None | object: ...
    def update(self) -> None: ...
    def set_history_buttons(self) -> None: ...

class ToolContainerBase:
    toolmanager: ToolManager
    def __init__(self, toolmanager: ToolManager) -> None: ...
    def add_tool(self, tool: ToolBase, group: str, position: int = ...) -> None: ...
    def trigger_tool(self, name: str) -> None: ...
    def add_toolitem(
        self,
        name: str,
        group: str,
        position: int,
        image: str,
        description: str,
        toggle: bool,
    ) -> None: ...
    def toggle_toolitem(self, name: str, toggled: bool) -> None: ...
    def remove_toolitem(self, name: str) -> None: ...
    def set_message(self, s: str) -> None: ...

class _Backend:
    backend_version: str
    FigureCanvas: type[FigureCanvasBase] | None
    FigureManager: type[FigureManagerBase]
    mainloop: None | Callable[[], Any]
    @classmethod
    def new_figure_manager(cls, num: int | str, *args, **kwargs) -> FigureManagerBase: ...
    @classmethod
    def new_figure_manager_given_figure(cls, num: int | str, figure: Figure) -> FigureManagerBase: ...
    @classmethod
    def draw_if_interactive(cls) -> None: ...
    @classmethod
    def show(cls, *, block: bool | None = ...) -> None: ...
    @staticmethod
    def export(cls) -> type[_Backend]: ...

class ShowBase(_Backend):
    def __call__(self, block: bool | None = ...) -> None: ...
