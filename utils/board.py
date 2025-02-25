import re
import math
import string
import itertools

from wand.image import Image
from wand.color import Color
from wand.drawing import Drawing

POS_RE = re.compile(r"^([A-Z]{1,4})(\d+)$")


### Made by txlyre


def label_generator():
    for r in itertools.count(1):
        for i in itertools.product(string.ascii_uppercase, repeat=r):
            yield "".join(i)


def label2index(l):
    i = 0

    for ol in label_generator():
        if l == ol:
            break

        i += 1

    return i


class Direction:
    L = (-1, 0)
    R = (1, 0)
    U = (0, -1)
    D = (0, 1)

    UL = (-1, -1)
    UR = (1, -1)
    DL = (-1, 1)
    DR = (1, 1)


class BadCoords(Exception):
    pass


class AlreadyOccupied(Exception):
    pass


class OutOfBounds(Exception):
    pass


class Token:
    def __init__(self, img, dim=1, label=None, **data):
        self.img = img
        self.dim = dim
        self.label = label
        self.data = data

        self._board = None
        self._x = 0
        self._y = 0

        self.hidden = False

    def __repr__(self):
        if not self._board:
            return "<Token>"

        return f"<Token {self._board} {self.pos}>"

    def __str__(self):
        return repr(self)

    def __setattr__(self, key, value):
        if key in ("img", "dim", "label", "data", "_board", "_x", "_y", "hidden"):
            self.__dict__[key] = value

            return

        if key in self.data:
            self.record(HistoryRecord.UPDATE, key=key, new=value, old=self.data[key])
        else:
            self.record(HistoryRecord.UPDATE, key=key, new=value)

        self.data[key] = value

    def __getattr__(self, key):
        return self.data[key]

    def _set_image(self, img):
        if isinstance(img, bytes):
            self.img = Image(blob=img)
        elif isinstance(img, str):
            self.img = Image(filename=img)
        else:
            self.img = img

        if (
            self.img.size[0] != self._board.token_dim * self.dim
            or self.img.size[1] != self._board.token_dim * self.dim
        ):
            if isinstance(img, Image):
                self.img = self.img.clone()

            self.img.liquid_rescale(
                self._board.token_dim * self.dim, self._board.token_dim * self.dim
            )

    def _set_board(self, board):
        self._board = board

        self._set_image(self.img)

    @property
    def coords(self):
        return self._x, self._y

    @property
    def pos(self):
        l = next(itertools.islice(label_generator(), self._x, None)).upper()
        i = self._board.h - self._y

        return l + str(i)

    def record(self, action, **fields):
        self._board.record(self, action, **fields)

    def hide(self):
        if not self.hidden:
            self.hidden = True

            self.record(HistoryRecord.HIDE)

    def unhide(self):
        if self.hidden:
            self.hidden = False

            self.record(HistoryRecord.UNHIDE)

    def remove(self):
        self.record(HistoryRecord.REMOVE)

        self._board.tokens.remove(self)

        self._board = None

    def move(self, pos, record=True):
        if isinstance(pos, tuple):
            x, y = pos
        else:
            x, y = self._board.pos2coords(pos)

        if self.dim > 1:
            if x + self.dim > self._board.w:
                raise OutOfBounds

            if y + self.dim > self._board.h:
                raise OutOfBounds

        if record:
            self.record(HistoryRecord.MOVE, ox=self._x, oy=self._y, x=x, y=y)

        self._x = x
        self._y = y

    def step(self, dir, steps=1):
        x = self._x
        y = self._y

        for _ in range(steps):
            x += dir[0]

            if x < 0:
                x = 0

            if x >= self._board.w:
                x = self._board.w - 1

            if self.dim > 1:
                if x + self.dim > self._board.w:
                    x = self._board.w - self.dim

            y += dir[1]

            if y < 0:
                y = 0

            if y >= self._board.h:
                y = self._board.h - 1

            if self.dim > 1:
                if y + self.dim > self._board.h:
                    y = self._board.h - self.dim

        self.move((x, y))


class HistoryRecord:
    CREATE = 0
    MOVE = 1
    HIDE = 2
    UNHIDE = 3
    REMOVE = 4
    UPDATE = 5

    def __init__(self, action, token, **fields):
        self.action = action
        self.token = token
        self.board = token._board

        self.fields = fields

    def __repr__(self):
        return f"<HistoryRecord {self.action} {self.token} {self.board}>"

    def __str__(self):
        return repr(self)

    def do(self):
        match self.action:
            case HistoryRecord.CREATE:
                self.token._set_board(self.board)

                self.board.tokens.add(self.token)

                self.token._x = self.fields["x"]
                self.token._y = self.fields["y"]

            case HistoryRecord.MOVE:
                self.token._x = self.fields["x"]
                self.token._y = self.fields["y"]

            case HistoryRecord.HIDE:
                self.token.hide()

            case HistoryRecord.UNHIDE:
                self.token.unhide()

            case HistoryRecord.REMOVE:
                self.board.tokens.remove(self.token)

                self.token._board = None

            case HistoryRecord.UPDATE:
                self.token.data[self.fields["key"]] = self.fields["new"]

    def undo(self):
        match self.action:
            case HistoryRecord.CREATE:
                self.board.tokens.remove(self.token)

                self.token._board = None

            case HistoryRecord.MOVE:
                self.token._x = self.fields["ox"]
                self.token._y = self.fields["oy"]

            case HistoryRecord.HIDE:
                self.token.unhide()

            case HistoryRecord.UNHIDE:
                self.token.hide()

            case HistoryRecord.REMOVE:
                self.token._set_board(self.board)

                self.board.tokens.add(self.token)

            case HistoryRecord.UPDATE:
                if "old" not in self.fields:
                    del self.token.data[self.fields["key"]]
                else:
                    self.token.data[self.fields["key"]] = self.fields["old"]


class Board:
    def __init__(
        self,
        bgimg,
        dim=None,
        token_dim=70,
        padding=48,
        font="./Arial.ttf",
        font_size=28,
        label_font_size=20,
        label_outline_width=3,
        line_width=2,
    ):
        if isinstance(bgimg, bytes):
            bgimg = Image(blob=bgimg)
        elif isinstance(bgimg, str):
            bgimg = Image(filename=bgimg)

        if dim is not None:
            w, h = dim
        else:
            w, h = bgimg.size

            w //= token_dim
            h //= token_dim

        if w < 2 or h < 2:
            raise ValueError

        self.w = w
        self.h = h

        self.token_dim = token_dim
        self.padding = padding
        self.font = font
        self.font_size = font_size
        self.line_width = line_width
        self.label_font_size = label_font_size
        self.label_outline_width = label_outline_width

        self.pw = w * self.token_dim + self.padding * 2
        self.ph = h * self.token_dim + self.padding * 2

        bgimg.liquid_rescale(self.pw - self.padding * 2, self.ph - self.padding * 2)

        with Image(width=1, height=1) as im:
            with Drawing() as draw:
                self.font_size = self.font_size
                self.font_metrics = draw.get_font_metrics(im, "lorem ipsum")

                self.font_size = self.label_font_size
                self.label_font_metrics = draw.get_font_metrics(im, "lorem ipsum")

        self.bgimg = bgimg

        self.tokens = set()

        self.history = []
        self.history_pos = -1

    def __repr__(self):
        return f"<Board {self.w}x{self.h}>"

    def __str__(self):
        return repr(self)

    def record(self, token, action, **fields):
        if self.history_pos < -1:
            self.history = self.history[: self.history_pos]
            self.history_pos = -1

        self.history.append(HistoryRecord(action, token, **fields))

    def undo(self):
        if abs(self.history_pos) > len(self.history) or not self.history:
            raise OutOfBounds

        self.history[self.history_pos].undo()
        self.history_pos -= 1

    def redo(self):
        if self.history_pos >= -1:
            raise OutOfBounds

        self.history_pos += 1
        self.history[self.history_pos].do()

    def pos2coords(self, pos):
        x, y = POS_RE.match(pos.strip().upper()).groups()
        x = label2index(x)
        y = self.h - int(y)

        if x < 0 or x >= self.w or y < 0 or y >= self.h:
            raise BadCoords(x, y)

        return x, y

    def get(self, pos):
        if isinstance(pos, tuple):
            x, y = pos
        else:
            x, y = self.pos2coords(pos)

        for token in self.tokens:
            ox, oy = token.coords
            dim = token.dim
            if dim == 1:
                dim = 0

            sx = ox
            ex = ox + dim
            sy = oy
            ey = oy + dim

            if x >= sx and x < ex and y >= sy and y < ey:
                return token

        return None

    def add(self, pos, token):
        if token._board is not None or token in self.tokens:
            raise ValueError

        token._set_board(self)

        token.move(pos, record=False)

        self.tokens.add(token)

        token.record(HistoryRecord.CREATE, x=token._x, y=token._y)

    def draw(self, unhide=False):
        im = Image(width=self.pw, height=self.ph, pseudo="canvas:")

        im.composite(self.bgimg, self.padding, self.padding)

        with Drawing() as draw:
            draw.stroke_color = Color("black")
            draw.stroke_width = 3
            draw.font = self.font
            draw.font_size = self.font_size

            for x in range(self.padding, self.pw, self.token_dim):
                draw.line((x, 0), (x, self.ph))

            for y in range(self.padding, self.ph, self.token_dim):
                draw.line((0, y), (self.pw, y))

            for i, l in zip(range(self.w), label_generator()):
                x = self.padding + i * self.token_dim

                draw.text(x, self.font_size, l)
                draw.text(x, self.ph, l)

            for i, j in zip(reversed(range(self.h)), range(self.h)):
                y = self.padding + self.font_size + i * self.token_dim

                draw.text(0, y, str(j + 1))
                draw.text(self.pw - self.font_size, y, str(j + 1))

            draw(im)

        with Drawing() as draw:
            draw.font = self.font

            for token in self.tokens:
                if not unhide and token.hidden:
                    continue

                x, y = token.coords

                im.composite(
                    token.img,
                    x * self.token_dim + self.padding,
                    y * self.token_dim + self.padding,
                )

                if token.label is not None:
                    maxlen = math.ceil(
                        self.token_dim / self.label_font_metrics.character_width
                    )

                    draw.stroke_color = Color("black")
                    draw.font_size = self.label_font_size + self.label_outline_width
                    draw.text(
                        x * self.token_dim + self.padding,
                        y * self.token_dim + self.padding + self.token_dim,
                        token.label[:maxlen],
                    )

                    draw.stroke_color = Color("white")
                    draw.font_size = self.label_font_size
                    draw.text(
                        x * self.token_dim + self.padding,
                        y * self.token_dim + self.padding + self.token_dim,
                        token.label[:maxlen],
                    )

            draw(im)

        return im

    def replay(self, delay=None, optimize=True):
        while self.history_pos >= -len(self.history):
            self.undo()

        im = self.draw()

        if delay:
            im.delay = int(im.ticks_per_second / 1000 * delay)

        while self.history_pos < -1:
            self.redo()

            im.sequence.append(self.draw())

        if delay:
            for frame in im.sequence:
                frame.delay = int(frame.ticks_per_second / 1000 * delay)

        if optimize:
            im.optimize_layers()

        return im
