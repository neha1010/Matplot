from .artist import Artist
from .axes import Axes
from .backend_bases import RendererBase
from .patches import Rectangle
from .path import Path
from .text import Text
from .transforms import Bbox
from .typing import ColorType

from collections.abc import Sequence
from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from pandas import DataFrame
else:
    DataFrame = None

class Cell(Rectangle):
    PAD: float
    def __init__(
        self,
        xy: tuple[float, float],
        width: float,
        height: float,
        *,
        edgecolor: ColorType = ...,
        facecolor: ColorType = ...,
        fill: bool = ...,
        text: str = ...,
        loc: Literal["left", "center", "right"] = ...,
        fontproperties: dict[str, Any] | None = ...,
        visible_edges: str | None = ...
    ) -> None: ...
    def get_text(self) -> Text: ...
    def set_fontsize(self, size: float) -> None: ...
    def get_fontsize(self) -> float: ...
    def auto_set_font_size(self, renderer: RendererBase) -> float: ...
    def get_text_bounds(
        self, renderer: RendererBase
    ) -> tuple[float, float, float, float]: ...
    def get_required_width(self, renderer: RendererBase) -> float: ...
    def set_text_props(self, **kwargs) -> None: ...
    @property
    def visible_edges(self) -> str: ...
    @visible_edges.setter
    def visible_edges(self, value: str | None) -> None: ...
    def get_path(self) -> Path: ...

CustomCell = Cell

class Table(Artist):
    codes: dict[str, int]
    FONTSIZE: float
    AXESPAD: float
    def __init__(
        self, ax: Axes, loc: str | None = ..., bbox: Bbox | None = ..., **kwargs
    ) -> None: ...
    def add_cell(self, row: int, col: int, *args, **kwargs) -> Cell: ...
    def __setitem__(self, position: tuple[int, int], cell: Cell) -> None: ...
    def __getitem__(self, position: tuple[int, int]) -> Cell: ...
    @property
    def edges(self) -> str | None: ...
    @edges.setter
    def edges(self, value: str | None) -> None: ...
    def draw(self, renderer) -> None: ...
    def get_children(self) -> list[Artist]: ...
    def get_window_extent(self, renderer: RendererBase | None = ...) -> Bbox: ...
    def auto_set_column_width(self, col: int | Sequence[int]) -> None: ...
    def auto_set_font_size(self, value: bool = ...) -> None: ...
    def scale(self, xscale: float, yscale: float) -> None: ...
    def set_fontsize(self, size: float) -> None: ...
    def get_celld(self) -> dict[tuple[int, int], Cell]: ...

def table(
    ax: Axes,
    cellText: Sequence[Sequence[str]] | DataFrame | None = ...,
    cellColours: Sequence[Sequence[ColorType]] | None = ...,
    cellLoc: Literal["left", "center", "right"] = ...,
    colWidths: Sequence[float] | None = ...,
    rowLabels: Sequence[str] | None = ...,
    rowColours: Sequence[ColorType] | None = ...,
    rowLoc: Literal["left", "center", "right"] = ...,
    colLabels: Sequence[str] | None = ...,
    colColours: Sequence[ColorType] | None = ...,
    colLoc: Literal["left", "center", "right"] = ...,
    loc: str = ...,
    bbox: Bbox | None = ...,
    edges: str = ...,
    **kwargs
) -> Table: ...
