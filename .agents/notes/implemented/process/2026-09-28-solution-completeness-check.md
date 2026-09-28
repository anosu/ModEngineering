# Agent Note: Solution completeness in the standard check

Status: implemented

## Problem

Formatting and project builds can pass while the IDE solution is missing or omits newly added tests. Tests can also select local shared sources while packaging selects pinned dependencies.

## Decision

The standard check validates the repository-named slnx as XML. Every project reference must exist inside the repository; the main project, discovered tests and evaluated pinned dependencies must be included. Duplicate projects are rejected. Folder layout, ordering and formatting remain user-owned. The test command explicitly selects pinned dependencies.

## Alternatives considered

Comparing generated solution text is easy but imposes ordering and destroys legitimate IDE folder layouts. Checking only existence misses unlisted tests. Relying on manual review has already allowed omissions. Structural validation enforces the contract without introducing a template drift system.

## Consequences

Consumers must maintain their standard solution before checks pass. Local solutions remain optional and cannot replace it. Project discovery stays in one helper shared by generation and validation; no private consumer inventory enters this repository. Existing repository notes contain no overlapping decision.
