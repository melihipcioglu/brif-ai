"""Project-side core v0 data contracts."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import Field, model_validator

from brif_ai.core.models.common import (
    ContractModel,
    DoorType,
    EntryRole,
    NonEmptyString,
    ObjectId,
    PassageDirection,
    SpaceFunction,
    VerticalConnectorType,
)


class Level(ContractModel):
    id: ObjectId
    name: NonEmptyString


class Space(ContractModel):
    id: ObjectId
    level_id: ObjectId
    function: SpaceFunction
    name: NonEmptyString


class EntryPoint(ContractModel):
    id: ObjectId
    role: EntryRole
    space_id: ObjectId


class Door(ContractModel):
    id: ObjectId
    space_a_id: ObjectId
    space_b_id: ObjectId
    door_type: DoorType
    direction: PassageDirection

    @model_validator(mode="after")
    def reject_self_connection(self) -> Door:
        if self.space_a_id == self.space_b_id:
            raise ValueError("door endpoints must reference two different spaces")
        return self


class OpenPassage(ContractModel):
    id: ObjectId
    space_a_id: ObjectId
    space_b_id: ObjectId
    direction: PassageDirection

    @model_validator(mode="after")
    def reject_self_connection(self) -> OpenPassage:
        if self.space_a_id == self.space_b_id:
            raise ValueError("open passage endpoints must reference two different spaces")
        return self


class VerticalConnector(ContractModel):
    id: ObjectId
    connector_type: VerticalConnectorType
    space_a_id: ObjectId
    space_b_id: ObjectId
    direction: PassageDirection

    @model_validator(mode="after")
    def reject_self_connection(self) -> VerticalConnector:
        if self.space_a_id == self.space_b_id:
            raise ValueError("vertical connector endpoints must reference two different spaces")
        return self


CoreObject = Level | Space | EntryPoint | Door | OpenPassage | VerticalConnector


class Project(ContractModel):
    id: ObjectId
    schema_version: NonEmptyString
    levels: list[Level] = Field(min_length=1)
    spaces: list[Space] = Field(min_length=1)
    entry_points: list[EntryPoint]
    doors: list[Door]
    open_passages: list[OpenPassage]
    vertical_connectors: list[VerticalConnector]

    @model_validator(mode="after")
    def validate_project_integrity(self) -> Project:
        self._validate_unique_object_ids()
        level_ids = {level.id for level in self.levels}
        space_ids = {space.id for space in self.spaces}

        for space in self.spaces:
            if space.level_id not in level_ids:
                raise ValueError(
                    f"space {space.id!r} references unknown level_id {space.level_id!r}"
                )

        for entry_point in self.entry_points:
            if entry_point.space_id not in space_ids:
                raise ValueError(
                    f"entry point {entry_point.id!r} references unknown space_id "
                    f"{entry_point.space_id!r}"
                )

        for connection in self._connections():
            if connection.space_a_id not in space_ids:
                raise ValueError(
                    f"{connection.id!r} references unknown space_a_id {connection.space_a_id!r}"
                )
            if connection.space_b_id not in space_ids:
                raise ValueError(
                    f"{connection.id!r} references unknown space_b_id {connection.space_b_id!r}"
                )

        return self

    def _validate_unique_object_ids(self) -> None:
        seen: dict[str, str] = {}
        collections: list[tuple[str, Iterable[CoreObject]]] = [
            ("level", self.levels),
            ("space", self.spaces),
            ("entry_point", self.entry_points),
            ("door", self.doors),
            ("open_passage", self.open_passages),
            ("vertical_connector", self.vertical_connectors),
        ]

        for object_type, objects in collections:
            for item in objects:
                previous_type = seen.get(item.id)
                if previous_type is not None:
                    raise ValueError(
                        f"duplicate object id {item.id!r} used by "
                        f"{previous_type!r} and {object_type!r}"
                    )
                seen[item.id] = object_type

    def _connections(self) -> Iterable[Door | OpenPassage | VerticalConnector]:
        yield from self.doors
        yield from self.open_passages
        yield from self.vertical_connectors
