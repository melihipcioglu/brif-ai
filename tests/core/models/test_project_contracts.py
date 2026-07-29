from __future__ import annotations

import pytest
from pydantic import ValidationError

from brif_ai.core.models import (
    Door,
    DoorType,
    EntryPoint,
    EntryRole,
    Level,
    OpenPassage,
    PassageDirection,
    Project,
    Space,
    SpaceFunction,
    VerticalConnector,
    VerticalConnectorType,
)


def _level(level_id: str = "level_1") -> Level:
    return Level(id=level_id, name="Ground")


def _space(space_id: str = "space_1", level_id: str = "level_1") -> Space:
    return Space(
        id=space_id,
        level_id=level_id,
        function=SpaceFunction.ENTRANCE,
        name="Entrance",
    )


def _entry(entry_id: str = "entry_1", space_id: str = "space_1") -> EntryPoint:
    return EntryPoint(id=entry_id, role=EntryRole.PRIMARY, space_id=space_id)


def _door(
    door_id: str = "door_1",
    space_a_id: str = "space_1",
    space_b_id: str = "space_2",
) -> Door:
    return Door(
        id=door_id,
        space_a_id=space_a_id,
        space_b_id=space_b_id,
        door_type=DoorType.STANDARD,
        direction=PassageDirection.BIDIRECTIONAL,
    )


def _project(
    *,
    levels: list[Level] | None = None,
    spaces: list[Space] | None = None,
    entry_points: list[EntryPoint] | None = None,
    doors: list[Door] | None = None,
    open_passages: list[OpenPassage] | None = None,
    vertical_connectors: list[VerticalConnector] | None = None,
) -> Project:
    return Project(
        id="project_1",
        schema_version="core.v0",
        levels=levels if levels is not None else [_level()],
        spaces=spaces if spaces is not None else [_space()],
        entry_points=entry_points if entry_points is not None else [_entry()],
        doors=doors if doors is not None else [],
        open_passages=open_passages if open_passages is not None else [],
        vertical_connectors=vertical_connectors if vertical_connectors is not None else [],
    )


def test_valid_minimum_project() -> None:
    project = _project()

    assert project.id == "project_1"
    assert project.spaces[0].function is SpaceFunction.ENTRANCE
    assert project.entry_points[0].role is EntryRole.PRIMARY


def test_rejects_invalid_id() -> None:
    with pytest.raises(ValidationError) as error:
        Level(id="Level 1", name="Ground")

    first_error = error.value.errors()[0]
    assert first_error["loc"] == ("id",)
    assert first_error["type"] == "string_pattern_mismatch"


def test_rejects_duplicate_id() -> None:
    with pytest.raises(ValidationError) as error:
        _project(levels=[_level("level_1"), _level("level_1")])

    assert "duplicate object id 'level_1'" in str(error.value)


def test_rejects_duplicate_id_across_object_types() -> None:
    with pytest.raises(ValidationError) as error:
        _project(spaces=[_space("entry_1")], entry_points=[_entry("entry_1", "entry_1")])

    assert "duplicate object id 'entry_1'" in str(error.value)


def test_rejects_unknown_level_reference() -> None:
    with pytest.raises(ValidationError) as error:
        _project(spaces=[_space(level_id="missing_level")])

    assert "level_id 'missing_level'" in str(error.value)


def test_rejects_door_with_unknown_space_reference() -> None:
    with pytest.raises(ValidationError) as error:
        _project(doors=[_door(space_b_id="missing_space")])

    assert "space_b_id 'missing_space'" in str(error.value)


def test_rejects_self_connecting_door() -> None:
    with pytest.raises(ValidationError) as error:
        _door(space_a_id="space_1", space_b_id="space_1")

    assert "door endpoints must reference two different spaces" in str(error.value)


def test_rejects_self_connecting_open_passage() -> None:
    with pytest.raises(ValidationError) as error:
        OpenPassage(
            id="passage_1",
            space_a_id="space_1",
            space_b_id="space_1",
            direction=PassageDirection.BIDIRECTIONAL,
        )

    assert "open passage endpoints must reference two different spaces" in str(error.value)


def test_rejects_self_connecting_vertical_connector() -> None:
    with pytest.raises(ValidationError) as error:
        VerticalConnector(
            id="vertical_1",
            connector_type=VerticalConnectorType.STAIR,
            space_a_id="space_1",
            space_b_id="space_1",
            direction=PassageDirection.BIDIRECTIONAL,
        )

    assert "vertical connector endpoints must reference two different spaces" in str(error.value)


def test_rejects_entry_point_with_unknown_space_reference() -> None:
    with pytest.raises(ValidationError) as error:
        _project(entry_points=[_entry(space_id="missing_space")])

    assert "space_id 'missing_space'" in str(error.value)


@pytest.mark.parametrize("link_kind", ["door", "open_passage", "vertical_connector"])
def test_rejects_link_with_unknown_space_a_reference(link_kind: str) -> None:
    if link_kind == "door":
        with pytest.raises(ValidationError) as error:
            _project(doors=[_door(space_a_id="missing_space", space_b_id="space_1")])
    elif link_kind == "open_passage":
        passage = OpenPassage(
            id="passage_1",
            space_a_id="missing_space",
            space_b_id="space_1",
            direction=PassageDirection.BIDIRECTIONAL,
        )
        with pytest.raises(ValidationError) as error:
            _project(open_passages=[passage])
    else:
        connector = VerticalConnector(
            id="vertical_1",
            connector_type=VerticalConnectorType.STAIR,
            space_a_id="missing_space",
            space_b_id="space_1",
            direction=PassageDirection.BIDIRECTIONAL,
        )
        with pytest.raises(ValidationError) as error:
            _project(vertical_connectors=[connector])

    assert "space_a_id 'missing_space'" in str(error.value)


def test_allows_multiple_entry_points() -> None:
    project = _project(
        entry_points=[
            _entry("entry_1", "space_1"),
            EntryPoint(id="entry_2", role=EntryRole.SECONDARY, space_id="space_1"),
            EntryPoint(id="entry_3", role=EntryRole.SERVICE, space_id="space_1"),
        ]
    )

    assert [entry.role for entry in project.entry_points] == [
        EntryRole.PRIMARY,
        EntryRole.SECONDARY,
        EntryRole.SERVICE,
    ]


def test_entry_point_connects_to_valid_space() -> None:
    project = _project()

    referenced_space_ids = {space.id for space in project.spaces}
    assert project.entry_points[0].space_id in referenced_space_ids


def test_door_can_connect_different_levels_for_validator() -> None:
    project = _project(
        levels=[_level("level_1"), _level("level_2")],
        spaces=[
            _space("space_1", "level_1"),
            _space("space_2", "level_2"),
        ],
        doors=[_door()],
    )

    assert project.doors[0].space_a_id == "space_1"
    assert project.doors[0].space_b_id == "space_2"


def test_open_passage_can_connect_different_levels_for_validator() -> None:
    passage = OpenPassage(
        id="passage_1",
        space_a_id="space_1",
        space_b_id="space_2",
        direction=PassageDirection.BIDIRECTIONAL,
    )

    project = _project(
        levels=[_level("level_1"), _level("level_2")],
        spaces=[
            _space("space_1", "level_1"),
            _space("space_2", "level_2"),
        ],
        open_passages=[passage],
    )

    assert project.open_passages[0].id == "passage_1"


def test_vertical_connector_can_connect_same_level_for_validator() -> None:
    connector = VerticalConnector(
        id="vertical_1",
        connector_type=VerticalConnectorType.STAIR,
        space_a_id="space_1",
        space_b_id="space_2",
        direction=PassageDirection.BIDIRECTIONAL,
    )

    project = _project(
        spaces=[
            _space("space_1", "level_1"),
            _space("space_2", "level_1"),
        ],
        vertical_connectors=[connector],
    )

    assert project.vertical_connectors[0].connector_type is VerticalConnectorType.STAIR
