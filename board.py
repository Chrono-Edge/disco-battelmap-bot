import re
import string
import itertools

from wand.image import Image
from wand.color import Color
from wand.drawing import Drawing

POS_RE = re.compile(r"^([A-Z]{1,4})(\d+)$")


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
    def __init__(self, img, dim=1, **data):
        self.dim = dim
        self.img = img
        self.data = data

        self._board = None
        self._x = 0
        self._y = 0

        self.hidden = False

    def __repr__(self):
        return f"<Token {self.pos}>"

    def __str__(self):
        return repr(self)

    def _set_image(self, img):
        if isinstance(img, bytes):
            img = Image(blob=img)
        elif isinstance(img, str):
            img = Image(filename=img)
        else:
            img = img.clone()

        img.resize(self._board.token_dim * self.dim, self._board.token_dim * self.dim)

        self.img = img

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

    def hide(self):
        self.hidden = True

    def unhide(self):
        self.hidden = False

    def remove(self):
        self._board.tokens.remove(self)

        self._board = None

    def move(self, pos):
        if isinstance(pos, tuple):
            x, y = pos
        else:
            x, y = self._board.pos2coords(pos)

        if self.dim > 1:
            if x + self.dim > self._board.w:
                raise OutOfBounds

            if y + self.dim > self._board.h:
                raise OutOfBounds

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


class Board:
    def __init__(
        self,
        bgimg,
        dim=None,
        token_dim=70,
        padding=48,
        font="./Arial.ttf",
        font_size=28,
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

        self.pw = w * self.token_dim + self.padding * 2
        self.ph = h * self.token_dim + self.padding * 2

        bgimg.liquid_rescale(self.pw - self.padding * 2, self.ph - self.padding * 2)

        self.bgimg = bgimg

        self.tokens = []

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
        token._set_board(self)

        token.move(pos)

        self.tokens.append(token)

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

        for token in self.tokens:
            if not unhide and token.hidden:
                continue

            x, y = token.coords

            im.composite(
                token.img,
                x * self.token_dim + self.padding,
                y * self.token_dim + self.padding,
            )

        return im
