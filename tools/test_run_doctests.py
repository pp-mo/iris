from pathlib import Path

import pytest
from run_doctests import list_modules_recursive  # , list_filepaths_recursive

from tools.run_doctests import list_filepaths_recursive


def make_dirs_and_files(pattern, basepath, create_module_inits=False):
    for dirname, pyfiles in pattern.items():
        dirpath = basepath / dirname.replace(".", "/")
        if not dirpath.exists():
            dirpath.mkdir()
        for content in pyfiles:
            with open(dirpath / content, "w") as mainfile:
                # Just create an empty top-level file
                pass


@pytest.fixture
def tempmodules(tmp_path):
    """Create  temporary discoverable modules."""
    patt = {
        "tmp_test_module": ["__init__.py", "s0.py", "s1.py"],
        "tmp_test_module.sm1": ["__init__.py", "s1.py", "s2.py", "_ps1.py"],
        "tmp_test_module.sm1.ssm1": ["__init__.py", "s3.py", "s4.py"],
        "tmp_test_module.sm1.ssm2": ["__init__.py", "s4.py", "s5.py", "_ps2.py"],
        "tmp_test_module.notamodule": ["xx1.py", "xx2.py"],
        "tmp_test_module.sm2": ["__init__.py", "s6.py"],
    }
    make_dirs_and_files(patt, tmp_path)
    try:
        import sys

        sys.path.append(str(tmp_path))
        yield
    finally:
        sys.path.remove(str(tmp_path))


@pytest.fixture
def tempsources(tmp_path):
    """Create temporary sourcefiles."""
    patt = {
        "maindir": ["s0.rst", "s1.rst", "ignore.this"],
        "maindir/subdir1": ["s1.rst", "s2.rst", "_px1.rst"],
        "maindir/subdir1/subsubdir1": ["s3.rst", "s4.rst"],
        "maindir/subdir1/subsubdir2": ["s4.rst", "s5.rst", "_px2.rst"],
        "maindir/subdir2": ["s6.rst"],
    }
    make_dirs_and_files(patt, tmp_path)
    try:
        import sys

        sys.path.append(str(tmp_path))
        yield
    finally:
        sys.path.remove(str(tmp_path))


class TestListModules:
    def test_import(self, tempmodules):
        """Check that 'tempmodules' puts the test module on the import path."""
        import tmp_test_module

        assert "<module 'tmp_test_module' from" in str(tmp_test_module)

    def test_nomatch(self):
        result = list_modules_recursive("not.exists")
        assert result == ["not.exists"]

    def test_recurse(self, tempmodules):
        result = list_modules_recursive("tmp_test_module")
        assert result == [
            "tmp_test_module",
            "tmp_test_module.s0",
            "tmp_test_module.s1",
            "tmp_test_module.sm1",
            "tmp_test_module.sm1._ps1",
            "tmp_test_module.sm1.s1",
            "tmp_test_module.sm1.s2",
            "tmp_test_module.sm1.ssm1",
            "tmp_test_module.sm1.ssm1.s3",
            "tmp_test_module.sm1.ssm1.s4",
            "tmp_test_module.sm1.ssm2",
            "tmp_test_module.sm1.ssm2._ps2",
            "tmp_test_module.sm1.ssm2.s4",
            "tmp_test_module.sm1.ssm2.s5",
            "tmp_test_module.sm2",
            "tmp_test_module.sm2.s6",
        ]

    def test_recurse_noprivate(self, tempmodules):
        result = list_modules_recursive("tmp_test_module", include_private=False)
        assert result == [
            "tmp_test_module",
            "tmp_test_module.s0",
            "tmp_test_module.s1",
            "tmp_test_module.sm1",
            # 'tmp_test_module.sm1._ps1',
            "tmp_test_module.sm1.s1",
            "tmp_test_module.sm1.s2",
            "tmp_test_module.sm1.ssm1",
            "tmp_test_module.sm1.ssm1.s3",
            "tmp_test_module.sm1.ssm1.s4",
            "tmp_test_module.sm1.ssm2",
            # 'tmp_test_module.sm1.ssm2._ps2',
            "tmp_test_module.sm1.ssm2.s4",
            "tmp_test_module.sm1.ssm2.s5",
            "tmp_test_module.sm2",
            "tmp_test_module.sm2.s6",
        ]

    def test_exclude_submod(self, tempmodules):
        result = list_modules_recursive("tmp_test_module", exclude_matches=["sm1"])
        assert result == [
            "tmp_test_module",
            "tmp_test_module.s0",
            "tmp_test_module.s1",
            "tmp_test_module.sm2",
            "tmp_test_module.sm2.s6",
        ]

    def test_exclude_namematch(self, tempmodules):
        result = list_modules_recursive("tmp_test_module", exclude_matches=["s1"])
        assert result == [
            "tmp_test_module",
            "tmp_test_module.s0",
            # 'tmp_test_module.s1',
            "tmp_test_module.sm1",
            # 'tmp_test_module.sm1._ps1',
            # 'tmp_test_module.sm1.s1',
            "tmp_test_module.sm1.s2",
            "tmp_test_module.sm1.ssm1",
            "tmp_test_module.sm1.ssm1.s3",
            "tmp_test_module.sm1.ssm1.s4",
            "tmp_test_module.sm1.ssm2",
            "tmp_test_module.sm1.ssm2._ps2",
            "tmp_test_module.sm1.ssm2.s4",
            "tmp_test_module.sm1.ssm2.s5",
            "tmp_test_module.sm2",
            "tmp_test_module.sm2.s6",
        ]


class TestListSources:
    def test_nonexist(self, tempsources):
        result = list_filepaths_recursive("none")
        assert result == [Path("none")]

    def test_toponly(self, tempsources, tmp_path):
        top_path = tmp_path / "maindir"
        top_pathstr = str(top_path)
        result = list_filepaths_recursive(top_pathstr)
        assert result == [top_path]

    def test_recurse_all(self, tempsources, tmp_path):
        top_pathstr = str(tmp_path / "maindir")
        result = list_filepaths_recursive(top_pathstr + "/**/*")
        assert result == [
            tmp_path / pathstr
            for pathstr in [
                "maindir/s0.rst",
                "maindir/s1.rst",
                "maindir/ignore.this",
                "maindir/subdir1",
                "maindir/subdir2",
                "maindir/subdir1/s1.rst",
                "maindir/subdir1/s2.rst",
                "maindir/subdir1/_px1.rst",
                "maindir/subdir1/subsubdir1",
                "maindir/subdir1/subsubdir2",
                "maindir/subdir2/s6.rst",
                "maindir/subdir1/subsubdir1/s3.rst",
                "maindir/subdir1/subsubdir1/s4.rst",
                "maindir/subdir1/subsubdir2/s4.rst",
                "maindir/subdir1/subsubdir2/s5.rst",
                "maindir/subdir1/subsubdir2/_px2.rst",
            ]
        ]

    def test_recurse_rsts(self, tempsources, tmp_path):
        top_pathstr = str(tmp_path / "maindir")
        result = list_filepaths_recursive(top_pathstr + "/**/*.rst")
        assert result == [
            tmp_path / pathstr
            for pathstr in [
                "maindir/s0.rst",
                "maindir/s1.rst",
                # 'maindir/ignore.this',
                # 'maindir/subdir1',
                # 'maindir/subdir2',
                "maindir/subdir1/s1.rst",
                "maindir/subdir1/s2.rst",
                "maindir/subdir1/_px1.rst",
                # 'maindir/subdir1/subsubdir1',
                # 'maindir/subdir1/subsubdir2',
                "maindir/subdir2/s6.rst",
                "maindir/subdir1/subsubdir1/s3.rst",
                "maindir/subdir1/subsubdir1/s4.rst",
                "maindir/subdir1/subsubdir2/s4.rst",
                "maindir/subdir1/subsubdir2/s5.rst",
                "maindir/subdir1/subsubdir2/_px2.rst",
            ]
        ]

    def test_recurse_exclude_subpath(self, tempsources, tmp_path):
        top_pathstr = str(tmp_path / "maindir")
        result = list_filepaths_recursive(
            top_pathstr + "/**/*.rst", exclude_matches=["/subsubdir2/"]
        )
        assert result == [
            tmp_path / pathstr
            for pathstr in [
                "maindir/s0.rst",
                "maindir/s1.rst",
                "maindir/subdir1/s1.rst",
                "maindir/subdir1/s2.rst",
                "maindir/subdir1/_px1.rst",
                "maindir/subdir2/s6.rst",
                "maindir/subdir1/subsubdir1/s3.rst",  # Note the odd ordering
                "maindir/subdir1/subsubdir1/s4.rst",
            ]
        ]

    def test_recurse_namematch_1(self, tempsources, tmp_path):
        """Search for '*s*.rst'."""
        top_pathstr = str(tmp_path / "maindir")
        result = list_filepaths_recursive(
            top_pathstr + "/**/*s*.rst",
        )
        assert result == [
            tmp_path / pathstr
            for pathstr in [
                "maindir/s0.rst",
                "maindir/s1.rst",
                "maindir/subdir1/s1.rst",
                "maindir/subdir1/s2.rst",
                "maindir/subdir2/s6.rst",
                "maindir/subdir1/subsubdir1/s3.rst",
                "maindir/subdir1/subsubdir1/s4.rst",
                "maindir/subdir1/subsubdir2/s4.rst",
                "maindir/subdir1/subsubdir2/s5.rst",
            ]
        ]

    def test_recurse_namematch_2(self, tempsources, tmp_path):
        """Search for '*1.rst'."""
        top_pathstr = str(tmp_path / "maindir")
        result = list_filepaths_recursive(
            top_pathstr + "/**/*1.rst",
        )
        assert result == [
            tmp_path / pathstr
            for pathstr in [
                "maindir/s1.rst",
                "maindir/subdir1/s1.rst",
                "maindir/subdir1/_px1.rst",
            ]
        ]

    def test_recurse_match_nonexist_glob(self, tempsources, tmp_path):
        top_pathstr = str(tmp_path / "maindir")
        search_path = top_pathstr + "*pqr*"
        result = list_filepaths_recursive(search_path)
        assert result == []

    def test_recurse_match_nonexist_noglob(self, tempsources, tmp_path):
        top_pathstr = str(tmp_path / "maindir")
        search_path = top_pathstr + "subdir1/non.exist"
        # As not actually a search, returns the given path.
        result = list_filepaths_recursive(search_path)
        assert result == [Path(search_path)]
