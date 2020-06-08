class LobsteroException(Exception):
    """The base exception for all lobstero-related errors.
    You should never see this. Hopefully."""


class ImageScriptException(Exception):
    """The base exception for all Imagescript-related errors.
    this inherits from LobsteroException."""


class UnknownOperationException(ImageScriptException):
    """An UnknownOperationException error is raised when you attempt to do something that Lobstero doesn't understand.
    For example, the Imagescript code ``blurr();`` would produce this error, as there is no ``blurr`` operation.

    Check your spelling!
    The Imagescript manual has more in-depth information on the basics."""


class BadInputException(ImageScriptException):
    """A BadInputException error is raised when you try to perform an operation with the wrong kind of data.
    It can be raised if:
    - The image you provide is too small.
    - You use an argument with a word or letter instead of a number.
    - You try to use an argument that an operation does not support.

    For example:
    - the Imagescript code ``blur(amount: hello world);`` would produce this error, because the ``amount`` argument should be a number.
    - the Imagescript code ``blur(strength: 10);`` would produce this error, because the ``blur`` operation has no ``strength`` argument.

    Double-check what you're doing!"""


class TooMuchToDoException(ImageScriptException):
    """A TooMuchToDoException error should be fairly self-explanatory.
    Try doing less things at once!"""


class BadSyntaxException(ImageScriptException):
    """A BadSyntaxException error is raised when Lobstero doesn't understand the code you try to run.
    This can be raised if:
    - You put too many brackets in your code.
    - You forget a semicolon between operations.

    Double-check what you're doing!
    The Imagescript manual has more in-depth information on the basics."""


class MissingBracketsException(BadSyntaxException):
    """A MissingBracketsException error is raised when your code has no brackets.
    Brackets are needed after each operation - this is so that potential arguments can be specified within them.
    You still need a pair of brackets after an operation, even if the operation takes no arguments.

    Double-check what you're doing!"""


class MissingColonException(BadSyntaxException):
    """A MissingColonException error should be fairly self-explanatory.
    When giving arguments to an operation, make sure that they're arranged in ``argument: value`` pairs.

    Double-check what you're doing!
    The Imagescript manual has more in-depth information on the basics."""


class MissingSemicolonException(BadSyntaxException):
    """A MissingBracketsException error is raised when your code has no semicolons.
    A semicolon is needed after each operation - this is to break them up so that they aren't clustered together.

    Double-check what you're doing!
    The Imagescript manual has more in-depth information on the basics."""


class OnExtendedCooldown(LobsteroException):
    """An exception raised when something is on an extended cooldown."""

    def __init__(self, expires):
        self.expires = expires

    def __str__(self) -> str:
        return self.expires.diff_for_humans()
