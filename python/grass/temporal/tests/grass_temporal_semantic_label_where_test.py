# SPDX-License-Identifier: GPL-2.0-or-later

"""The where statement that selects maps by semantic label

A label with an underscore is fully qualified and also matches its upper case
and zero-padding-free forms; a shortcut or a band number matches the labels
that end or start with it. A quote in the label must not end the literal. The
statements below were recorded from the code that wrote them by string
replacement, on 26.10.2026, before the literals went through sql_literal(). The
alternatives of a shortcut are joined with OR and not put in parentheses, so
they escape a condition given before them with AND; that is kept as it was.
"""

import pytest

import grass.temporal as tgis

pytestmark = pytest.mark.usefixtures("temporal_module_session")

LABELS = ["S2_1", "S2_01", "s2_b_3", "1", "01", "B1", "it's", "a'_b", "x_y"]
WHERES = ["", "id > 1"]
EXPECTED = {
    ("S2_1", ""): "semantic_label IN ('S2_1', 'S2_01')",
    ("S2_1", "id > 1"): "id > 1 AND semantic_label IN ('S2_1', 'S2_01')",
    ("S2_01", ""): "semantic_label IN ('S2_01', 'S2_1')",
    ("S2_01", "id > 1"): "id > 1 AND semantic_label IN ('S2_01', 'S2_1')",
    ("s2_b_3", ""): "semantic_label IN ('s2_b_3')",
    ("s2_b_3", "id > 1"): "id > 1 AND semantic_label IN ('s2_b_3')",
    (
        "1",
        "",
    ): "semantic_label LIKE '01\\_%' ESCAPE '\\' OR semantic_label LIKE '%\\_01' ESCAPE '\\' OR semantic_label LIKE '1\\_%' ESCAPE '\\' OR semantic_label LIKE '%\\_1' ESCAPE '\\'",
    (
        "1",
        "id > 1",
    ): "id > 1 AND semantic_label LIKE '01\\_%' ESCAPE '\\' OR semantic_label LIKE '%\\_01' ESCAPE '\\' OR semantic_label LIKE '1\\_%' ESCAPE '\\' OR semantic_label LIKE '%\\_1' ESCAPE '\\'",
    (
        "01",
        "",
    ): "semantic_label LIKE '1\\_%' ESCAPE '\\' OR semantic_label LIKE '%\\_1' ESCAPE '\\' OR semantic_label LIKE '01\\_%' ESCAPE '\\' OR semantic_label LIKE '%\\_01' ESCAPE '\\'",
    (
        "01",
        "id > 1",
    ): "id > 1 AND semantic_label LIKE '1\\_%' ESCAPE '\\' OR semantic_label LIKE '%\\_1' ESCAPE '\\' OR semantic_label LIKE '01\\_%' ESCAPE '\\' OR semantic_label LIKE '%\\_01' ESCAPE '\\'",
    ("B1", ""): "semantic_label = 'B1'",
    ("B1", "id > 1"): "id > 1 AND semantic_label = 'B1'",
    ("it's", ""): "semantic_label = 'it''s'",
    ("it's", "id > 1"): "id > 1 AND semantic_label = 'it''s'",
    ("a'_b", ""): "semantic_label IN ('a''_b')",
    ("a'_b", "id > 1"): "id > 1 AND semantic_label IN ('a''_b')",
    ("x_y", ""): "semantic_label IN ('x_y')",
    ("x_y", "id > 1"): "id > 1 AND semantic_label IN ('x_y')",
}


@pytest.mark.parametrize("where", WHERES)
@pytest.mark.parametrize("label", LABELS)
def test_the_where_statement_for_a_semantic_label(label, where):
    stds = tgis.SpaceTimeRasterDataset("zz@PERMANENT")
    stds.semantic_label = label

    result = stds._update_where_statement_by_semantic_label(where)

    assert result == EXPECTED[(label, where)]
