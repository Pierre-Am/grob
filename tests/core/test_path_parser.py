import pytest

from grob.core.path_parser import PathParser


@pytest.mark.parametrize(
    "pattern, path, expected_result",
    [
        pytest.param(".*", "foo/bar.txt", {}),
        pytest.param("foo/bar_{index}.txt", "foo/bar_1.txt", {"index": "1"}),
        pytest.param("foo/bar_{index}.txt", "foo/bar_abc.txt", {"index": "abc"}),
        pytest.param("foo/bar_{index}.txt", "foo/bar_abc_123.txt", {"index": "abc_123"}),
        pytest.param("foo/bar_{index}.txt", "foo/bar_.txt", None),
        pytest.param("foo/*/bar_{index}.txt", "foo/bar_1.txt", None),
        pytest.param("foo/*/bar_{index}.txt", "foo/baz/bar_1.txt", {"index": "1"}),
        pytest.param("foo/*/bar_{index}.txt", "foo/baz/clang/bar_1.txt", None),
        pytest.param("foo/bar_{index}.(mp3|aac|wav)", "foo/bar_1.mp3", {"index": "1"}),
        pytest.param("foo/bar_{index}.(mp3|aac|wav)", "foo/bar_1.aac", {"index": "1"}),
        pytest.param("foo/bar_{index}.(mp3|aac|wav)", "foo/bar_1.wav", {"index": "1"}),
        pytest.param("foo/bar_{index}.(mp3|aac|wav)", "foo/bar_1.txt", None),
        pytest.param("foo/bar_{index}.(mp3|aac|wav)", "foo/bar.mp3", None),
        pytest.param("foo/{subset}/{name}.txt", "foo/train/doc.txt", {"subset": "train", "name": "doc"}),
        pytest.param("foo/{subset}/{name}.txt", "foo/doc.txt", None),
        pytest.param("foo/(a|b)/file_{index}.txt", "foo/a/file_001.txt", {"index": "001"}),
        pytest.param("foo/(a|b)/file_{index}.txt", "foo/b/file_001.txt", {"index": "001"}),
        pytest.param("foo/(a|b)/file_{index}.txt", "foo/ab/file_001.txt", None),
        pytest.param("foo/{artist}-{album}/tracks.json", "foo/a-a-a-a/tracks.json", {"artist": "a", "album": "a-a-a"}),
        pytest.param(
            "foo/{artist!g}-{album}/tracks.json", "foo/a-a-a-a/tracks.json", {"artist": "a-a-a", "album": "a"}
        ),
        pytest.param(
            "foo/{artist}-{album!g}/tracks.json", "foo/a-a-a-a/tracks.json", {"artist": "a", "album": "a-a-a"}
        ),
    ],
)
def test_path_parser(pattern, path, expected_result):
    parser = PathParser(pattern)
    assert parser(path) == expected_result


@pytest.mark.parametrize(
    "pattern, expected_parts",
    [
        pytest.param(".*", []),
        # Ensure order is preserved
        pytest.param("{z}_{a}", ["z", "a"]),
        pytest.param("foo/bar_{index}.txt", ["index"]),
        pytest.param("foo/*/bar_{index}.txt", ["index"]),
        pytest.param("foo/bar_{index}.(mp3|aac|wav)", ["index"]),
        pytest.param("foo/{subset}/{name}.txt", ["subset", "name"]),
        pytest.param("foo/(a|b)/file_{index}.txt", ["index"]),
        pytest.param("foo/{artist!g}-{album}/tracks.json", ["artist", "album"]),
        pytest.param(r"(?P<this should be escaped>\d){foo}", ["foo"]),
        pytest.param(r"\{this should be escaped\}{foo}", ["foo"]),
    ],
)
def test_path_parser_key_parts(pattern, expected_parts):
    parser = PathParser(pattern)
    assert parser.key_parts == expected_parts
