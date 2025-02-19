import datetime
import inspect
from typing import TYPE_CHECKING, Any, Optional, Union

from dis_snek.client.utils.cache import TTLCache
from dis_snek.models import Embed, MaterialColors

if TYPE_CHECKING:
    from dis_snek.client import Snake

__all__ = ("debug_embed", "get_cache_state", "strf_delta")


def debug_embed(title: str, **kwargs) -> Embed:
    """Create a debug embed with a standard header and footer."""
    e = Embed(
        f"Dis-Snek Debug: {title}",
        url="https://github.com/Discord-Snake-Pit/Dis-Snek/tree/master/dis_snek/ext/debug_scale",
        color=MaterialColors.BLUE_GREY,
        **kwargs,
    )
    e.set_footer(
        "Dis-Snek Debug Scale",
        icon_url="https://media.discordapp.net/attachments/907639005070377020/918600896433238097/sparkle-snekCUnetnoise_scaleLevel0x2.500000.png",
    )
    return e


def get_cache_state(bot: "Snake") -> str:
    """Create a nicely formatted table of internal cache state."""
    caches = [
        c[0]
        for c in inspect.getmembers(bot.cache, predicate=lambda x: isinstance(x, dict))
        if not c[0].startswith("__")
    ]
    table = []

    for cache in caches:
        val = getattr(bot.cache, cache)

        if isinstance(val, TTLCache):
            amount = [len(val), f"{val.hard_limit}({val.soft_limit})"]
            expire = f"{val.ttl}s"
        else:
            amount = [len(val), "∞"]
            expire = "none"

        row = [cache.removesuffix("_cache"), amount, expire]
        table.append(row)

    # http caches
    table.append(["endpoints", [len(bot.http._endpoints), "∞"], "none"])
    table.append(["ratelimits", [len(bot.http.ratelimit_locks), "∞"], "w_ref"])

    adjust_subcolumn(table, 1, aligns=[">", "<"])

    labels = ["Cache", "Amount", "Expire"]
    return make_table(table, labels)


def strf_delta(time_delta: datetime.timedelta, show_seconds: bool = True) -> str:
    """Formats timedelta into a human readable string."""
    years, days = divmod(time_delta.days, 365)
    hours, rem = divmod(time_delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)

    years_fmt = f"{years} year{'s' if years > 1 or years == 0 else ''}"
    days_fmt = f"{days} day{'s' if days > 1 or days == 0 else ''}"
    hours_fmt = f"{hours} hour{'s' if hours > 1 or hours == 0 else ''}"
    minutes_fmt = f"{minutes} minute{'s' if minutes > 1 or minutes == 0 else ''}"
    seconds_fmt = f"{seconds} second{'s' if seconds > 1 or seconds == 0 else ''}"

    if years >= 1:
        return f"{years_fmt} and {days_fmt}"
    if days >= 1:
        return f"{days_fmt} and {hours_fmt}"
    if hours >= 1:
        return f"{hours_fmt} and {minutes_fmt}"
    if show_seconds:
        return f"{minutes_fmt} and {seconds_fmt}"
    return f"{minutes_fmt}"


def _make_solid_line(
    column_widths: list[int],
    left_char: str,
    middle_char: str,
    right_char: str,
) -> str:
    """
    Internal helper function.

    Constructs a "solid" line for the table (top, bottom, line between labels and table)
    """
    return f"{left_char}{middle_char.join('─' * (width + 2) for width in column_widths)}{right_char}"


def _make_data_line(
    column_widths: list[int],
    line: list[Any],
    left_char: str,
    middle_char: str,
    right_char: str,
    aligns: Union[list[str], str] = "<",
) -> str:
    """
    Internal helper function.

    Constructs a line with data for the table
    """
    if isinstance(aligns, str):
        aligns = [aligns for _ in column_widths]

    line = (f"{str(value): {align}{width}}" for width, align, value in zip(column_widths, aligns, line))
    return f"{left_char}{f'{middle_char}'.join(line)}{right_char}"


def _get_column_widths(columns) -> list[int]:
    """
    Internal helper function.

    Calculates max width of each column
    """
    return [max(len(str(value)) for value in column) for column in columns]


def adjust_subcolumn(
    rows: list[list[Any]], column_index: int, separator: str = "/", aligns: Union[list[str], str] = "<"
) -> None:
    """Converts column composed of list of subcolumns into aligned str representation."""
    column = list(zip(*rows))[column_index]
    subcolumn_widths = _get_column_widths(zip(*column))
    if isinstance(aligns, str):
        aligns = [aligns for _ in subcolumn_widths]

    column = [_make_data_line(subcolumn_widths, row, "", separator, "", aligns) for row in column]
    for row, new_item in zip(rows, column):
        row[column_index] = new_item


def make_table(rows: list[list[Any]], labels: Optional[list[Any]] = None, centered: bool = False) -> str:
    """
    Converts 2D list to str representation as table

    :param rows: 2D list containing objects that have a single-line representation (via `str`). All rows must be of the same length.
    :param labels: List containing the column labels. If present, the length must equal to that of each row.
    :param centered: If the items should be aligned to the center, else they are left aligned.
    :return: A table representing the rows passed in.
    """
    columns = zip(*rows) if labels is None else zip(*rows, labels)
    column_widths = _get_column_widths(columns)
    align = "^" if centered else "<"
    align = [align for _ in column_widths]

    lines = [_make_solid_line(column_widths, "╭", "┬", "╮")]

    data_left = "│ "
    data_middle = " │ "
    data_right = " │"
    if labels is not None:
        lines.append(_make_data_line(column_widths, labels, data_left, data_middle, data_right, align))
        lines.append(_make_solid_line(column_widths, "├", "┼", "┤"))
    for row in rows:
        lines.append(_make_data_line(column_widths, row, data_left, data_middle, data_right, align))
    lines.append(_make_solid_line(column_widths, "╰", "┴", "╯"))
    return "\n".join(lines)
