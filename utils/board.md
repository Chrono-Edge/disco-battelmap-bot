```markdown
# Boardgame Toolkit Documentation

This document provides documentation for the Python Boardgame Toolkit library.

## Modules

### `boardgame_toolkit.core`

This module contains the core classes and functions for creating and managing game boards and tokens.

## Functions

### `label_generator()`

**Description:**

Generates labels in alphabetical order (A, B, C..., Z, AA, AB...). This is used for generating algebraic notation labels for board positions.

**Returns:**

`Generator[str, None, None]`: A generator that yields labels as strings.

**Examples:**

```python
from boardgame_toolkit.core import label_generator

gen = label_generator()
print(next(gen))  # Output: A
print(next(gen))  # Output: B
print(next(gen))  # Output: C
# ...
print(next(itertools.islice(gen, 25, None))) # Output: Z
print(next(gen))  # Output: AA
print(next(gen))  # Output: AB
```

### `label2index(label_to_find: str) -> int`

**Description:**

Converts a label (e.g., 'A', 'AA', 'B3') to a zero-based index. This is the reverse operation of the `label_generator`, useful for converting algebraic notation column labels to numerical indices.

**Parameters:**

* `label_to_find` (`str`): The label string to convert.

**Returns:**

`int`: The zero-based index of the label.

**Examples:**

```python
from boardgame_toolkit.core import label2index

print(label2index('A'))   # Output: 0
print(label2index('B'))   # Output: 1
print(label2index('Z'))   # Output: 25
print(label2index('AA'))  # Output: 26
print(label2index('AB'))  # Output: 27
```

## Classes

### `Direction`

**Description:**

Defines named tuples as class attributes for common directions, useful for token movement. These are intended to be used as constants.

**Attributes:**

* `L` (`Tuple[int, int]`): Left direction: `(-1, 0)`.
* `R` (`Tuple[int, int]`): Right direction: `(1, 0)`.
* `U` (`Tuple[int, int]`): Up direction: `(0, -1)`.
* `D` (`Tuple[int, int]`): Down direction: `(0, 1)`.
* `UL` (`Tuple[int, int]`): Up-Left direction: `(-1, -1)`.
* `UR` (`Tuple[int, int]`): Up-Right direction: `(1, -1)`.
* `DL` (`Tuple[int, int]`): Down-Left direction: `(-1, 1)`.
* `DR` (`Tuple[int, int]`): Down-Right direction: `(1, 1)`.

**Examples:**

```python
from boardgame_toolkit.core import Direction

# Example usage with Token.step() method (see Token documentation)
```

### `BadCoords(Exception)`

**Description:**

Exception raised when attempting to use invalid coordinates, such as when converting an algebraic position string that is not valid for the current board size.

### `AlreadyOccupied(Exception)`

**Description:**

Exception raised when attempting to place a token on a grid cell that is already occupied by another token. *(Currently not implemented in the provided code but intended for future use)*

### `OutOfBounds(Exception)`

**Description:**

Exception raised when coordinates are out of the board boundaries. This can occur when trying to access a position outside the board's grid or move a token off the board.

### `Token`

**Description:**

Represents a game token with an image, dimensions, and custom properties. Tokens are placed on a `Board` object.

**Attributes:**

* `image` (`Image`): The Wand Image object representing the token's visual appearance.
* `dimension` (`int`): The dimension of the token in grid cells. A dimension of `1` means the token occupies a 1x1 grid cell, `2` means 2x2, and so on. Defaults to `1`.
* `label` (`Optional[str]`): An optional text label for the token, which can be displayed on the board. Defaults to `None`.
* `properties` (`Dict[str, Any]`): A dictionary to store arbitrary token data. You can use this to store game-specific information associated with the token.
* `hidden` (`bool`): A boolean indicating whether the token is hidden on the board. Hidden tokens are not rendered by default in the `Board.draw()` method. Defaults to `False`.

**Methods:**

* `__init__(self, image: Image, dimension: int = 1, label: Optional[str] = None, **data: Any)`
    * **Description:** Initializes a `Token` object.
    * **Parameters:**
        * `image` (`Image`): The Wand Image object for the token.
        * `dimension` (`int`, optional): The size of the token in grid units (default: 1).
        * `label` (`Optional[str]`, optional): An optional text label for the token (default: None).
        * `**data` (`Any`): Arbitrary keyword arguments to be stored as token properties.
* `coords` **property** (`Tuple[int, int]`)
    * **Description:** Returns the token's current grid coordinates (x, y) as a tuple.
* `pos` **property** (`str`)
    * **Description:** Returns the token's position in algebraic notation (e.g., 'A1').
* `record(self, action: int, **fields: Any) -> None`
    * **Description:** Records an action performed on the token in the game board's history. This method is called internally for actions like move, hide, unhide, update, and remove.
    * **Parameters:**
        * `action` (`int`): The action type from `HistoryRecord` constants (e.g., `HistoryRecord.MOVE`, `HistoryRecord.UPDATE`).
        * `**fields` (`Any`): Additional data to record with the action, specific to the action type (e.g., for `MOVE`, you might include `ox`, `oy`, `x`, `y` for old and new coordinates).
* `hide(self) -> None`
    * **Description:** Hides the token on the board. The token will not be visible when the board is drawn until `unhide()` is called. Records a `HistoryRecord.HIDE` action.
* `unhide(self) -> None`
    * **Description:** Unhides the token, making it visible on the board again. Records a `HistoryRecord.UNHIDE` action.
* `remove(self) -> None`
    * **Description:** Removes the token from the board. The token is disassociated from the board and will no longer be drawn or managed by the board. Records a `HistoryRecord.REMOVE` action.
* `move(self, pos: str, record: bool = True) -> None`
    * **Description:** Moves the token to a new position on the board.
    * **Parameters:**
        * `pos` (`str`): The target position in algebraic notation (e.g., 'B2') or as a tuple of coordinates `(x, y)`.
        * `record` (`bool`, optional): Whether to record the move in the game history for undo/redo functionality. Defaults to `True`.
    * **Raises:**
        * `OutOfBounds`: If the target position is outside the board boundaries.
* `step(self, direction: Tuple[int, int], steps: int = 1) -> None`
    * **Description:** Moves the token in a given direction for a specified number of steps. The token will stop at the board boundaries if it would move off the edge.
    * **Parameters:**
        * `direction` (`Tuple[int, int]`): A tuple representing the direction to move, typically one of the constants from the `Direction` class (e.g., `Direction.R` for right, `Direction.UL` for up-left).
        * `steps` (`int`, optional): The number of steps to take in the given direction. Defaults to `1`.

**Examples:**

```python
from wand.image import Image
from boardgame_toolkit.core import Board, Token, Direction

# Create a board (example background image - replace with your image)
with Image(filename='path/to/your/board_background.png') as bg_image:
    board = Board(bg_image, dimensions=(10, 10))

# Create a token (example token image - replace with your image)
with Image(filename='path/to/your/token_image.png') as token_image:
    token1 = Token(token_image, label="Player 1", player_id=1) # Token with a label and custom property
    token2 = Token(token_image, dimension=2, label="Big Token") # 2x2 token

# Add tokens to the board
board.add('A1', token1)
board.add('B2', token2)

# Move token1
token1.move('C3')

# Move token2 2 steps to the right
token2.step(Direction.R, steps=2)

# Access token properties
print(token1.player_id) # Output: 1

# Draw the board with tokens
board_image = board.draw()
board_image.save(filename='board_with_tokens.png')

# Hide token1
token1.hide()
board_image_hidden = board.draw() # token1 will not be visible in this image
board_image_hidden.save(filename='board_hidden_token.png')

# Unhide token1
token1.unhide()
board_image_unhidden = board.draw() # token1 is visible again
board_image_unhidden.save(filename='board_unhidden_token.png')

# Remove token2 from board
token2.remove()
board_image_removed = board.draw() # token2 will not be on the board anymore
board_image_removed.save(filename='board_token_removed.png')
```

### `HistoryRecord`

**Description:**

Represents a record of an action performed on the game board. Used for implementing undo/redo functionality. History records are created and managed by the `Board` and `Token` classes internally. You typically don't need to create `HistoryRecord` objects directly.

**Constants:**

* `CREATE` (`Literal[0]`): Action type for token creation.
* `MOVE` (`Literal[1]`): Action type for token movement.
* `HIDE` (`Literal[2]`): Action type for hiding a token.
* `UNHIDE` (`Literal[3]`): Action type for unhiding a token.
* `REMOVE` (`Literal[4]`): Action type for removing a token.
* `UPDATE` (`Literal[5]`): Action type for updating token properties.

**Methods:**

* `__init__(self, action: int, token: Token, **fields: Any)`
    * **Description:** Initializes a `HistoryRecord` object.
    * **Parameters:**
        * `action` (`int`): The type of action performed (use `HistoryRecord` constants).
        * `token` (`Token`): The `Token` object affected by the action.
        * `**fields` (`Any`): Additional data associated with the action (e.g., old/new positions, property names, etc.).
* `do(self) -> None`
    * **Description:** Applies the action recorded in the `HistoryRecord` (forward action). This is used for redoing actions.
* `undo(self) -> None`
    * **Description:** Reverts the action recorded in the `HistoryRecord` (undo action). This is used for undoing actions.

**Examples:**

```python
# HistoryRecord objects are created and managed by Board and Token internally.
# See Board.undo() and Board.redo() examples for how history is used.
```

### `Board`

**Description:**

Represents a game board with a background image, grid, tokens, and history management for undo/redo.

**Attributes:**

* `background_image` (`Image`): The Wand Image object used as the background for the board.
* `grid_width` (`int`): Width of the board in grid cells (number of columns).
* `grid_height` (`int`): Height of the board in grid cells (number of rows).
* `cell_size` (`int`): Size of each grid cell in pixels.
* `padding` (`int`): Padding around the grid in pixels, used for labels and visual spacing.
* `font` (`str`): File path to the font used for text elements on the board (grid labels, token labels).
* `grid_font_size` (`int`): Font size for grid labels (column letters and row numbers).
* `token_label_font_size` (`int`): Font size for token labels.
* `token_label_outline_width` (`int`): Outline width for token labels, to improve readability against the board background.
* `grid_line_width` (`int`): Line width for grid lines.
* `tokens` (`Set[Token]`): A set containing all `Token` objects currently placed on the board.

**Methods:**

* `__init__(self, background_image: Image, dimensions: Optional[Tuple[int, int]] = None, cell_size: int = 70, padding: int = 48, font: str = "./Arial.ttf", grid_font_size: int = 28, token_label_font_size: int = 20, token_label_outline_width: int = 3, grid_line_width: int = 2)`
    * **Description:** Initializes a `Board` object.
    * **Parameters:**
        * `background_image` (`Image`): Wand Image object or filename/bytes for the background image.
        * `dimensions` (`Optional[Tuple[int, int]]`, optional): Tuple `(width, height)` representing the board dimensions in grid cells. If `None`, dimensions are derived from the background image size and `cell_size`. Defaults to `None`.
        * `cell_size` (`int`, optional): Size of each grid cell in pixels. Defaults to `70`.
        * `padding` (`int`, optional): Padding around the grid in pixels. Defaults to `48`.
        * `font` (`str`, optional): Font file path for text elements. Defaults to `"./Arial.ttf"`.
        * `grid_font_size` (`int`, optional): Font size for grid labels. Defaults to `28`.
        * `token_label_font_size` (`int`, optional): Font size for token labels. Defaults to `20`.
        * `token_label_outline_width` (`int`, optional): Outline width for token labels. Defaults to `3`.
        * `grid_line_width` (`int`, optional): Line width for grid lines. Defaults to `2`.
    * **Raises:**
        * `ValueError`: If board dimensions are less than 2x2.
* `record(self, token: Token, action: int, **fields: Any) -> None`
    * **Description:** Records an action to the history. Called internally by `Token` methods.
    * **Parameters:**
        * `token` (`Token`): The `Token` object involved in the action.
        * `action` (`int`): The action type from `HistoryRecord` constants.
        * `**fields` (`Any`): Additional data to store with the history record.
* `undo(self) -> None`
    * **Description:** Undoes the last recorded action, reverting the board state to the previous step.
    * **Raises:**
        * `OutOfBounds`: If there are no more actions to undo (history is empty or at the beginning).
* `redo(self) -> None`
    * **Description:** Redoes the last undone action, moving forward in the history.
    * **Raises:**
        * `OutOfBounds`: If there are no more actions to redo (at the end of the history).
* `pos2coords(self, pos: str) -> Tuple[int, int]`
    * **Description:** Converts an algebraic position string (e.g., 'A1') to grid coordinates `(x, y)`.
    * **Parameters:**
        * `pos` (`str`): The position string in algebraic notation.
    * **Returns:**
        * `Tuple[int, int]`: The grid coordinates `(x, y)`.
    * **Raises:**
        * `BadCoords`: If the position string is invalid or out of bounds for the board.
* `get(self, pos: str) -> Optional[Token]`
    * **Description:** Retrieves the `Token` at a given position.
    * **Parameters:**
        * `pos` (`str`): The position in algebraic notation (e.g., 'B2') or as a tuple of coordinates `(x, y)`.
    * **Returns:**
        * `Optional[Token]`: The `Token` object at the specified position, or `None` if no token is present.
* `add(self, pos: str, token: Token) -> None`
    * **Description:** Adds a `Token` to the board at the specified position.
    * **Parameters:**
        * `pos` (`str`): The target position in algebraic notation (e.g., 'C3').
        * `token` (`Token`): The `Token` object to add.
    * **Raises:**
        * `ValueError`: If the token is already on a board or has already been added to this board.
* `draw(self, unhide: bool = False) -> Image`
    * **Description:** Draws the current state of the board as a Wand `Image`. This includes the background image, grid lines, grid labels, and all visible tokens.
    * **Parameters:**
        * `unhide` (`bool`, optional): If `True`, also draws hidden tokens. Defaults to `False`.
    * **Returns:**
        * `Image`: The rendered board image as a Wand `Image` object.
* `replay(self, delay: Optional[int] = None, optimize: bool = True) -> Image`
    * **Description:** Generates an animated GIF replay of the game history, showing each action performed on the board.
    * **Parameters:**
        * `delay` (`Optional[int]`, optional): Delay in milliseconds between frames in the GIF animation. If `None`, no delay is added. Defaults to `None`.
        * `optimize` (`bool`, optional): Whether to optimize the GIF layers to reduce file size. Defaults to `True`.
    * **Returns:**
        * `Image`: The animated GIF image as a Wand `Image` object.

**Examples:**

```python
from wand.image import Image
from boardgame_toolkit.core import Board, Token

# Load background image
with Image(filename='path/to/your/board_background.png') as bg_image:
    # Create a board instance
    board = Board(bg_image, dimensions=(8, 8), cell_size=60)

    # Load token image
    with Image(filename='path/to/your/pawn_token.png') as pawn_image:
        # Create tokens
        pawn1 = Token(pawn_image, label="Pawn 1")
        pawn2 = Token(pawn_image, label="Pawn 2")

    # Add tokens to the board
    board.add('A1', pawn1)
    board.add('H8', pawn2)

    # Move tokens
    pawn1.move('A2')
    pawn2.move('G7')

    # Draw the board
    board_image = board.draw()
    board_image.save(filename='initial_board.png')

    # Undo the last move (pawn2.move('G7'))
    board.undo()
    board_image_undo = board.draw()
    board_image_undo.save(filename='board_after_undo.png') # pawn2 back to original position

    # Redo the undone move (pawn2.move('G7'))
    board.redo()
    board_image_redo = board.draw()
    board_image_redo.save(filename='board_after_redo.png') # pawn2 moved to G7 again

    # Generate replay GIF
    replay_gif = board.replay(delay=500) # 500ms delay between frames
    replay_gif.save(filename='game_replay.gif')
```

---

This documentation provides a comprehensive overview of the `boardgame_toolkit.core` module. Remember to replace placeholder paths like `'path/to/your/board_background.png'` and `'path/to/your/token_image.png'` with actual file paths to your image resources when running the examples.