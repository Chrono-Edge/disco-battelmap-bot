import re
import math
import string
import itertools
from typing import Generator, Tuple, Optional, Set, List, Dict, Any, Literal

from wand.image import Image
from wand.color import Color
from wand.drawing import Drawing

POS_RE = re.compile(r"^([A-Z]{1,4})(\d+)$")


### Made by txlyre


def label_generator() -> Generator[str, None, None]:
    """Generates labels in alphabetical order (A, B, C..., Z, AA, AB...)."""
    for label_length in itertools.count(1):
        for letters in itertools.product(string.ascii_uppercase, repeat=label_length):
            yield "".join(letters)


def label2index(label_to_find: str) -> int:
    """Converts a label (e.g., 'A', 'AA', 'B3') to a zero-based index.

    Args:
        label_to_find: The label string to convert.

    Returns:
        The zero-based index of the label.
    """
    index = 0
    for generated_label in label_generator():
        if label_to_find == generated_label:
            break
        index += 1
    return index


class Direction:
    """Defines named tuples for common directions."""

    L: Tuple[int, int] = (-1, 0)  # Left
    R: Tuple[int, int] = (1, 0)  # Right
    U: Tuple[int, int] = (0, -1)  # Up
    D: Tuple[int, int] = (0, 1)  # Down

    UL: Tuple[int, int] = (-1, -1)  # Up-Left
    UR: Tuple[int, int] = (1, -1)  # Up-Right
    DL: Tuple[int, int] = (-1, 1)  # Down-Left
    DR: Tuple[int, int] = (1, 1)  # Down-Right


class BadCoords(Exception):
    """Exception raised for invalid coordinates."""
    pass


class AlreadyOccupied(Exception):
    """Exception raised when attempting to place a token on an occupied cell."""
    pass


class OutOfBounds(Exception):
    """Exception raised when coordinates are out of board boundaries."""
    pass


class Token:
    """Represents a game token with an image, dimensions, and data.

    Attributes:
        image (Image): The image representing the token.
        dimension (int): The dimension of the token (1x1, 2x2, etc. in grid cells).
        label (Optional[str]): An optional label for the token (displayed on the board).
        properties (Dict[str, Any]): A dictionary to store arbitrary token data.
        hidden (bool): Whether the token is hidden on the board (default: False).
    """

    def __init__(self, image: Image, dimension: int = 1, label: Optional[str] = None, **data: Any):
        """Initializes a Token object.

        Args:
            image: The Wand Image object for the token.
            dimension: The size of the token in grid units (default: 1).
            label: An optional text label for the token (default: None).
            **data:  Arbitrary keyword arguments to be stored as token properties.
        """
        self.image: Image = image
        self.dimension: int = dimension
        self.label: Optional[str] = label
        self.properties: Dict[str, Any] = data

        self._game_board: Optional['Board'] = None
        self._grid_x: int = 0
        self._grid_y: int = 0

        self.hidden: bool = False

    def __repr__(self) -> str:
        """Returns a string representation of the Token."""
        if not self._game_board:
            return "<Token>"
        return f"<Token {self._game_board} {self.pos}>"

    def __str__(self) -> str:
        """Returns a user-friendly string representation of the Token."""
        return repr(self)

    def __setattr__(self, key: str, value: Any) -> None:
        """Sets an attribute, recording changes to properties in history."""
        if key in ("image", "dimension", "label", "properties", "_game_board", "_grid_x", "_grid_y", "hidden"):
            self.__dict__[key] = value
            return

        if key in self.properties:
            self.record(HistoryRecord.UPDATE, key=key, new=value, old=self.properties[key])
        else:
            self.record(HistoryRecord.UPDATE, key=key, new=value)

        self.properties[key] = value

    def __getattr__(self, key: str) -> Any:
        """Gets an attribute, primarily accessing properties."""
        return self.properties[key]

    def _set_image(self, image_data: Image) -> None:
        """Internal method to set and resize the token's image.

        Args:
            image_data: The image data (Image object, bytes, or filename).
        """
        if isinstance(image_data, bytes):
            self.image = Image(blob=image_data)
        elif isinstance(image_data, str):
            self.image = Image(filename=image_data)
        else:
            self.image = image_data

        expected_size = self._game_board.cell_size * self.dimension  # type: ignore # _game_board can't be None here

        if self.image.size[0] != expected_size or self.image.size[1] != expected_size:
            if isinstance(image_data, Image):
                self.image = self.image.clone()  # Clone to avoid modifying original image

            self.image.liquid_rescale(expected_size, expected_size)

    def _set_board(self, board: 'Board') -> None:
        """Internal method to associate the token with a game board.

        Args:
            board: The Board object to associate with.
        """
        self._game_board = board
        self._set_image(self.image)

    @property
    def coords(self) -> Tuple[int, int]:
        """Returns the token's grid coordinates (x, y)."""
        return self._grid_x, self._grid_y

    @property
    def pos(self) -> str:
        """Returns the token's position in algebraic notation (e.g., 'A1')."""
        label_x = next(itertools.islice(label_generator(), self._grid_x, None)).upper()
        label_y = self._game_board.grid_height - self._grid_y  # type: ignore # _game_board can't be None here
        return label_x + str(label_y)

    def record(self, action: int, **fields: Any) -> None:
        """Records an action in the game board's history.

        Args:
            action: The action type (from HistoryRecord constants).
            **fields: Additional data to record with the action.
        """
        if self._game_board:
            self._game_board.record(self, action, **fields)

    def hide(self) -> None:
        """Hides the token on the board."""
        if not self.hidden:
            self.hidden = True
            self.record(HistoryRecord.HIDE)

    def unhide(self) -> None:
        """Unhides the token, making it visible on the board."""
        if self.hidden:
            self.hidden = False
            self.record(HistoryRecord.UNHIDE)

    def remove(self) -> None:
        """Removes the token from the board."""
        self.record(HistoryRecord.REMOVE)
        if self._game_board:
            self._game_board.tokens.remove(self)
        self._game_board = None

    def move(self, pos: str, record: bool = True) -> None:
        """Moves the token to a new position on the board.

        Args:
            pos: The target position in algebraic notation (e.g., 'B2') or coordinates (tuple).
            record: Whether to record the move in history (default: True).

        Raises:
            OutOfBounds: If the target position is outside the board boundaries.
        """
        if isinstance(pos, tuple):
            target_x, target_y = pos
        else:
            target_x, target_y = self._game_board.pos2coords(
                pos)  # type: ignore # _game_board can't be None when token is on board

        if self.dimension > 1:
            if target_x + self.dimension > self._game_board.grid_width:  # type: ignore
                raise OutOfBounds
            if target_y + self.dimension > self._game_board.grid_height:  # type: ignore
                raise OutOfBounds

        if record:
            self.record(HistoryRecord.MOVE, ox=self._grid_x, oy=self._grid_y, x=target_x, y=target_y)

        self._grid_x = target_x
        self._grid_y = target_y

    def step(self, direction: Tuple[int, int], steps: int = 1) -> None:
        """Moves the token in a given direction for a specified number of steps.

        Keeps token within board boundaries.

        Args:
            direction: A tuple representing the direction (from Direction class).
            steps: The number of steps to take (default: 1).
        """
        current_x = self._grid_x
        current_y = self._grid_y

        for _ in range(steps):
            current_x += direction[0]

            if current_x < 0:
                current_x = 0
            if current_x >= self._game_board.grid_width:  # type: ignore
                current_x = self._game_board.grid_width - 1  # type: ignore

            if self.dimension > 1:
                if current_x + self.dimension > self._game_board.grid_width:  # type: ignore
                    current_x = self._game_board.grid_width - self.dimension  # type: ignore

            current_y += direction[1]

            if current_y < 0:
                current_y = 0
            if current_y >= self._game_board.grid_height:  # type: ignore
                current_y = self._game_board.grid_height - 1  # type: ignore

            if self.dimension > 1:
                if current_y + self.dimension > self._game_board.grid_height:  # type: ignore
                    current_y = self._game_board.grid_height - self.dimension  # type: ignore

        self.move((current_x, current_y))


class HistoryRecord:
    """Represents a record of an action performed on the game board.

    Constants:
        CREATE (int): Action type for token creation.
        MOVE (int): Action type for token movement.
        HIDE (int): Action type for hiding a token.
        UNHIDE (int): Action type for unhiding a token.
        REMOVE (int): Action type for removing a token.
        UPDATE (int): Action type for updating token properties.
    """
    CREATE: Literal[0] = 0
    MOVE: Literal[1] = 1
    HIDE: Literal[2] = 2
    UNHIDE: Literal[3] = 3
    REMOVE: Literal[4] = 4
    UPDATE: Literal[5] = 5

    def __init__(self, action: int, token: Token, **fields: Any):
        """Initializes a HistoryRecord object.

        Args:
            action: The type of action performed (use HistoryRecord constants).
            token: The Token object affected by the action.
            **fields: Additional data associated with the action (e.g., old/new positions).
        """
        self.action: int = action
        self.token: Token = token
        self.game_board: 'Board' = token._game_board  # type: ignore # token always has board when history is recorded
        self.record_data: Dict[str, Any] = fields

    def __repr__(self) -> str:
        """Returns a string representation of the HistoryRecord."""
        return f"<HistoryRecord {self.action} {self.token} {self.game_board}>"

    def __str__(self) -> str:
        """Returns a user-friendly string representation of the HistoryRecord."""
        return repr(self)

    def do(self) -> None:
        """Applies the action recorded in the HistoryRecord (forward action)."""
        if self.game_board is None:
            return  # Prevent error if board is unexpectedly None

        if self.action == HistoryRecord.CREATE:
            self.token._set_board(self.game_board)
            self.game_board.tokens.add(self.token)
            self.token._grid_x = self.record_data["x"]
            self.token._grid_y = self.record_data["y"]

        elif self.action == HistoryRecord.MOVE:
            self.token._grid_x = self.record_data["x"]
            self.token._grid_y = self.record_data["y"]

        elif self.action == HistoryRecord.HIDE:
            self.token.hide()

        elif self.action == HistoryRecord.UNHIDE:
            self.token.unhide()

        elif self.action == HistoryRecord.REMOVE:
            if self.token in self.game_board.tokens:  # Check if token is still in board's tokens
                self.game_board.tokens.remove(self.token)
            self.token._game_board = None

        elif self.action == HistoryRecord.UPDATE:
            self.token.properties[self.record_data["key"]] = self.record_data["new"]

    def undo(self) -> None:
        """Reverts the action recorded in the HistoryRecord (undo action)."""
        if self.game_board is None:
            return  # Prevent error if board is unexpectedly None

        if self.action == HistoryRecord.CREATE:
            if self.token in self.game_board.tokens:  # Check if token is still in board's tokens
                self.game_board.tokens.remove(self.token)
            self.token._game_board = None

        elif self.action == HistoryRecord.MOVE:
            self.token._grid_x = self.record_data["ox"]
            self.token._grid_y = self.record_data["oy"]

        elif self.action == HistoryRecord.HIDE:
            self.token.unhide()

        elif self.action == HistoryRecord.UNHIDE:
            self.token.hide()

        elif self.action == HistoryRecord.REMOVE:
            self.token._set_board(self.game_board)
            self.game_board.tokens.add(self.token)

        elif self.action == HistoryRecord.UPDATE:
            if "old" not in self.record_data:
                del self.token.properties[self.record_data["key"]]
            else:
                self.token.properties[self.record_data["key"]] = self.record_data["old"]


class Board:
    """Represents a game board with tokens and history management.

    Attributes:
        background_image (Image): The background image for the board.
        grid_width (int): Width of the board in grid cells.
        grid_height (int): Height of the board in grid cells.
        cell_size (int): Size of each grid cell in pixels (default: 70).
        padding (int): Padding around the grid in pixels (default: 48).
        font (str): Font file path for text elements (default: "./Arial.ttf").
        grid_font_size (int): Font size for grid labels (default: 28).
        token_label_font_size (int): Font size for token labels (default: 20).
        token_label_outline_width (int): Outline width for token labels (default: 3).
        grid_line_width (int): Line width for grid lines (default: 2).
        tokens (Set[Token]): Set of tokens currently on the board.
        _history (List[HistoryRecord]): List of history records for undo/redo.
        _history_index (int): Current position in the history list.
    """

    def __init__(
            self,
            background_image: Image,
            dimensions: Optional[Tuple[int, int]] = None,
            cell_size: int = 70,
            padding: int = 48,
            font: str = "./Arial.ttf",
            grid_font_size: int = 28,
            token_label_font_size: int = 20,
            token_label_outline_width: int = 3,
            grid_line_width: int = 2,
    ):
        """Initializes a Board object.

        Args:
            background_image: Wand Image object or filename/bytes for the background.
            dimensions: Tuple (width, height) of the board in grid cells. If None, dimensions are derived from background image size and cell_size.
            cell_size: Size of each grid cell in pixels (default: 70).
            padding: Padding around the grid in pixels (default: 48).
            font: Font file path for text elements (default: "./Arial.ttf").
            grid_font_size: Font size for grid labels (default: 28).
            token_label_font_size: Font size for token labels (default: 20).
            token_label_outline_width: Outline width for token labels (default: 3).
            grid_line_width: Line width for grid lines (default: 2).

        Raises:
            ValueError: If board dimensions are less than 2x2.
        """
        if isinstance(background_image, bytes):
            background_image = Image(blob=background_image)
        elif isinstance(background_image, str):
            background_image = Image(filename=background_image)

        if dimensions is not None:
            grid_width, grid_height = dimensions
        else:
            grid_width = background_image.size[0] // cell_size
            grid_height = background_image.size[1] // cell_size

        if grid_width < 2 or grid_height < 2:
            raise ValueError("Board dimensions must be at least 2x2")

        self.grid_width: int = grid_width
        self.grid_height: int = grid_height

        self.cell_size: int = cell_size
        self.padding: int = padding
        self.font: str = font
        self.grid_font_size: int = grid_font_size
        self.grid_line_width: int = grid_line_width
        self.token_label_font_size: int = token_label_font_size
        self.token_label_outline_width: int = token_label_outline_width

        self.pixel_width: int = grid_width * self.cell_size + self.padding * 2
        self.pixel_height: int = grid_height * self.cell_size + self.padding * 2

        background_image.liquid_rescale(self.pixel_width - self.padding * 2, self.pixel_height - self.padding * 2)

        with Image(width=1, height=1) as temp_image:  # Use temp image to get font metrics
            with Drawing() as temp_draw:
                temp_draw.font = self.font
                temp_draw.font_size = self.grid_font_size
                self.font_metrics = temp_draw.get_font_metrics(temp_image, "lorem ipsum")  # type: ignore

                temp_draw.font_size = self.token_label_font_size
                self.label_font_metrics = temp_draw.get_font_metrics(temp_image, "lorem ipsum")  # type: ignore

        self.background_image: Image = background_image

        self.tokens: Set[Token] = set()

        self._history: List[HistoryRecord] = []
        self._history_index: int = -1

    def __repr__(self) -> str:
        """Returns a string representation of the Board."""
        return f"<Board {self.grid_width}x{self.grid_height}>"

    def __str__(self) -> str:
        """Returns a user-friendly string representation of the Board."""
        return repr(self)

    def record(self, token: Token, action: int, **fields: Any) -> None:
        """Records an action to the history.

        Args:
            token: The Token object involved in the action.
            action: The action type (from HistoryRecord constants).
            **fields: Additional data to store with the history record.
        """
        if self._history_index < -1:
            self._history = self._history[: self._history_index + 1]  # Discard redo history
            self._history_index = -1

        self._history.append(HistoryRecord(action, token, **fields))

    def undo(self) -> None:
        """Undoes the last recorded action."""
        if abs(self._history_index) > len(self._history) or not self._history:
            raise OutOfBounds("No more actions to undo.")

        self._history[self._history_index].undo()
        self._history_index -= 1

    def redo(self) -> None:
        """Redoes the last undone action."""
        if self._history_index >= -1:
            raise OutOfBounds("No more actions to redo.")

        self._history_index += 1
        self._history[self._history_index].do()

    def pos2coords(self, pos: str) -> Tuple[int, int]:
        """Converts an algebraic position (e.g., 'A1') to grid coordinates (x, y).

        Args:
            pos: The position string in algebraic notation.

        Returns:
            Tuple[int, int]: The grid coordinates (x, y).

        Raises:
            BadCoords: If the position is invalid or out of bounds.
        """
        match = POS_RE.match(pos.strip().upper())
        if not match:
            raise BadCoords(f"Invalid position format: {pos}")

        label_x_str, label_y_str = match.groups()
        grid_x = label2index(label_x_str)
        grid_y = self.grid_height - int(label_y_str)

        if not (0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height):
            raise BadCoords(f"Position {pos} is out of bounds.")

        return grid_x, grid_y

    def get(self, pos: str) -> Optional[Token]:
        """Retrieves the token at a given position.

        Args:
            pos: The position in algebraic notation or grid coordinates.

        Returns:
            Optional[Token]: The Token at the position, or None if no token is present.
        """
        if isinstance(pos, tuple):
            grid_x, grid_y = pos
        else:
            grid_x, grid_y = self.pos2coords(pos)

        for token in self.tokens:
            token_ox, token_oy = token.coords
            dimension = token.dimension
            if dimension == 1:
                dimension = 0  # Adjust dimension for range check

            start_x = token_ox
            end_x = token_ox + dimension + 1
            start_y = token_oy
            end_y = token_oy + dimension + 1

            if start_x <= grid_x < end_x and start_y <= grid_y < end_y:
                return token
        return None

    def add(self, pos: str, token: Token) -> None:
        """Adds a token to the board at the specified position.

        Args:
            pos: The target position in algebraic notation (e.g., 'C3').
            token: The Token object to add.

        Raises:
            ValueError: If the token is already on a board or in the tokens set.
        """
        if token._game_board is not None or token in self.tokens:
            raise ValueError("Token is already on a board or added to this board.")

        token._set_board(self)
        token.move(pos, record=False)  # Initial move, record=False to be recorded in CREATE action
        self.tokens.add(token)
        token.record(HistoryRecord.CREATE, x=token._grid_x, y=token._grid_y)

    def draw(self, unhide: bool = False) -> Image:
        """Draws the current state of the board as an Image.

        Args:
            unhide: If True, draws hidden tokens as well (default: False).

        Returns:
            Image: The rendered board image.
        """
        board_image = Image(width=self.pixel_width, height=self.pixel_height, pseudo="canvas:")
        board_image.composite(self.background_image, self.padding, self.padding)

        draw_context = Drawing()  # Create Drawing context once
        draw_context.stroke_color = Color("black")
        draw_context.stroke_width = 3
        draw_context.font = self.font
        draw_context.font_size = self.grid_font_size

        # Draw grid lines
        for x in range(self.padding, self.pixel_width, self.cell_size):
            draw_context.line((x, 0), (x, self.pixel_height))
        for y in range(self.padding, self.pixel_height, self.cell_size):
            draw_context.line((0, y), (self.pixel_width, y))

        # Draw column labels (A, B, C...)
        for i, label in zip(range(self.grid_width), label_generator()):
            x_pos = self.padding + 5 + i * self.cell_size
            draw_context.text(x_pos, self.grid_font_size, label)
            draw_context.text(x_pos, self.pixel_height, label)

        # Draw row labels (1, 2, 3...)
        for i, j in zip(reversed(range(self.grid_height)), range(self.grid_height)):
            y_pos = self.padding + self.grid_font_size + i * self.cell_size
            draw_context.text(0, y_pos, str(j + 1))
            draw_context.text(self.pixel_width - self.grid_font_size, y_pos, str(j + 1))

        draw_context(board_image)  # Apply grid and labels

        # Draw tokens
        draw_context.font = self.font  # Reset font for token labels (if different)
        for token in self.tokens:
            if not unhide and token.hidden:
                continue

            token_x, token_y = token.coords
            board_image.composite(
                token.image,
                token_x * self.cell_size + self.padding,
                token_y * self.cell_size + self.padding,
            )

            if token.label is not None:
                max_label_length = math.ceil(
                    self.cell_size / self.label_font_metrics.character_width  # type: ignore
                )
                truncated_label = token.label[:max_label_length]

                draw_context.stroke_color = Color("black")
                draw_context.font_size = self.token_label_font_size + self.token_label_outline_width
                draw_context.text(
                    token_x * self.cell_size + self.padding,
                    token_y * self.cell_size + self.padding + self.cell_size,
                    truncated_label,
                )

                draw_context.stroke_color = Color("white")
                draw_context.font_size = self.token_label_font_size
                draw_context.text(
                    token_x * self.cell_size + self.padding,
                    token_y * self.cell_size + self.padding + self.cell_size,
                    truncated_label,
                )
        draw_context(board_image)  # Apply tokens and labels

        return board_image

    def replay(self, delay: Optional[int] = None, optimize: bool = True) -> Image:
        """Generates an animated GIF replay of the history.

        Args:
            delay: Delay in milliseconds between frames (default: None, no delay).
            optimize: Whether to optimize the GIF layers (default: True).

        Returns:
            Image: The animated GIF image.
        """
        while self._history_index >= -len(self._history):
            self.undo()

        replay_image = self.draw()

        if delay:
            replay_image.delay = int(replay_image.ticks_per_second / 1000 * delay)

        while self._history_index < -1:
            self.redo()
            replay_image.sequence.append(self.draw())

        if delay:
            for frame in replay_image.sequence:
                frame.delay = int(frame.ticks_per_second / 1000 * delay)

        if optimize:
            replay_image.optimize_layers()

        return replay_image
