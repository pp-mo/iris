#!/usr/bin/env bash
echo "python -m unittest iris.tests.test_ff"
python -m unittest iris.tests.test_ff

echo ""
echo ""
echo "------------------"
echo "python -m unittest discover -v iris.tests.unit.fileformats.ff"
python -m unittest discover -v iris.tests.unit.fileformats.ff
