import csv
import json
from functools import partial
from itertools import zip_longest
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Protocol, TextIO, Tuple, TypeAlias, Union

from grob.types import Group, GroupKey, TagName

SqueezedGroup: TypeAlias = Optional[str]
FormattedGroup: TypeAlias = Union[Group, SqueezedGroup]
Groups: TypeAlias = Union[Iterable[FormattedGroup], Dict[GroupKey, FormattedGroup]]


class _PathJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Path):
            return obj.as_posix()
        return super().default(obj)


def format_groups(
    groups: Dict[GroupKey, Groups],
    stream: TextIO,
    tag_names: List[TagName],
    relative_to: Optional[Path] = None,
    squeeze: bool = True,
    with_keys: bool = True,
    output_format: Literal["json", "jsonl", "human", "csv", "tsv"] = "json",
) -> None:
    groups, squeezed = prepare_groups(
        groups,
        tag_names=tag_names,
        relative_to=relative_to,
        squeeze=squeeze,
        with_keys=with_keys,
    )
    formatter = _FORMATTERS[output_format]()
    formatter(groups, stream, tag_names=tag_names, with_keys=with_keys, squeezed=squeezed)


def prepare_groups(
    groups: Dict[GroupKey, Groups],
    tag_names: List[TagName],
    relative_to: Optional[Path] = None,
    squeeze: bool = True,
    with_keys: bool = True,
) -> Tuple[Groups, bool]:
    if relative_to is not None:
        # Paths are absolute
        for group in groups.values():
            for tag in group:
                if isinstance(group[tag], list):
                    group[tag] = [path.relative_to(relative_to) if path is not None else path for path in group[tag]]
                else:
                    group[tag] = group[tag].relative_to(relative_to) if group[tag] is not None else group[tag]
    squeezed = False
    if squeeze and len(tag_names) == 1:
        tag_name = tag_names[0]
        groups = {key: group.get(tag_name) for key, group in groups.items()}
        squeezed = True
    if with_keys:
        return groups, squeezed
    return list(groups.values()), squeezed


class OutputFormatter(Protocol):
    def __call__(
        self, groups: Groups, stream: TextIO, tag_names: List[str], squeezed: bool = False, with_keys: bool = True
    ):
        pass


class JsonOutputFormatter:
    def __call__(
        self, groups: Groups, stream: TextIO, tag_names: List[str], squeezed: bool = False, with_keys: bool = True
    ) -> None:
        json.dump(groups, stream, cls=_PathJSONEncoder)


class JsonlOutputFormatter:
    def __call__(
        self, groups: Groups, stream: TextIO, tag_names: List[str], squeezed: bool = False, with_keys: bool = True
    ) -> None:
        for record in self._iter_records(groups, squeezed=squeezed, with_keys=with_keys):
            stream.write(json.dumps(record, cls=_PathJSONEncoder) + "\n")

    @staticmethod
    def _iter_records(groups: Groups, squeezed: bool, with_keys: bool) -> Iterable[Any]:
        if with_keys:
            for key, group in groups.items():
                if squeezed:
                    yield {"key": key, "file": group}
                else:
                    yield {"key": key, "files": group}
        else:
            yield from groups


class TableOutputFormatter:
    def __init__(self, separator: str, line_terminator: str = "\n") -> None:
        self.delimiter = separator
        self.line_terminator = line_terminator

    def __call__(
        self, groups: Groups, stream: TextIO, tag_names: List[str], squeezed: bool = False, with_keys: bool = True
    ) -> None:
        writer = csv.writer(stream, delimiter=self.delimiter, lineterminator=self.line_terminator)
        for row in self._iter_rows(groups, squeezed=squeezed, with_keys=with_keys, tag_names=tag_names):
            writer.writerow(row)

    def _iter_rows(self, groups: Groups, tag_names: List[str], squeezed: bool, with_keys: bool) -> Iterable[List[str]]:
        header = ["files"] if squeezed else tag_names
        if with_keys:
            header = ["key", *header]
        yield header

        for key, group in groups.items() if with_keys else zip_longest([], groups):
            if squeezed:
                files = [self._format_path(group)]
            else:
                files = [self._format_path(group.get(tag_name, "")) for tag_name in tag_names]
            yield [key, *files] if with_keys else files

    @staticmethod
    def _format_path(path_or_paths: Union[str, Path, List[Path], List[str]]) -> str:
        paths = [path_or_paths] if not isinstance(path_or_paths, list) else path_or_paths
        formatted_paths = [path if isinstance(path, str) else path.as_posix() for path in paths if path is not None]
        return ", ".join(formatted_paths)


class HumanOutputFormatter(TableOutputFormatter):
    def __call__(
        self, groups: Groups, stream: TextIO, tag_names: List[str], squeezed: bool = False, with_keys: bool = True
    ) -> None:
        raise NotImplementedError()


_FORMATTERS = {
    "human": HumanOutputFormatter,
    "json": JsonOutputFormatter,
    "jsonl": JsonlOutputFormatter,
    "csv": partial(TableOutputFormatter, separator=","),
    "tsv": partial(TableOutputFormatter, separator="\t"),
}
