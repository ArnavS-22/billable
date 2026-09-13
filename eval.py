"""Reliability fixtures for the draft gate (must-release vs must-hold)."""

import matters

matters.MATTERS.clear()
matters.MATTERS.update(
    {
        "alpha": {
            "client": "Alpha LLC",
            "matter_number": "1000.001",
            "matter_name": "Alpha LLC - Test Matter",
        },
        "gamma": {
            "client": "Gamma LLC",
            "matter_number": "2000.002",
            "matter_name": "Gamma LLC - Test Matter",
        },
    }
)

from release import draft_from_fields


def _check(name, entry, expect_ready, expect_task=None, expect_matter=None):
    ok = entry["ready_to_confirm"] is expect_ready
    if expect_task and entry["task_type"] != expect_task:
        ok = False
    if expect_matter and entry["matter_number"] != expect_matter:
        ok = False
    status = "PASS" if ok else "FAIL"
    print(f"{status}  {name}")
    print(f"       ready={entry['ready_to_confirm']} task={entry['task_type']} matter={entry['matter_number']}")
    print(f"       narrative={entry['narrative']}")
    print(f"       hours={entry['hours']} reason={entry['reason']}")
    return ok


def main() -> None:
    results = []
    results.append(
        _check(
            "must-release: known client, markup, 18m",
            draft_from_fields(
                "Alpha_NDA",
                18,
                "User reviewing and adding markup comments to a draft NDA document",
            ),
            expect_ready=True,
            expect_task="Document Drafting/Revision",
            expect_matter="1000.001",
        )
    )
    results.append(
        _check(
            "must-hold: no client key",
            draft_from_fields("notes", 20, "reading a memo"),
            expect_ready=False,
        )
    )
    results.append(
        _check(
            "must-hold: duration 2 minutes",
            draft_from_fields("Alpha_NDA", 2, "draft markup on NDA"),
            expect_ready=False,
            expect_matter="1000.001",
        )
    )
    results.append(
        _check(
            "must-hold: two clients in the name",
            draft_from_fields("alpha_vs_gamma_term_sheet", 20, "review"),
            expect_ready=False,
        )
    )
    passed = sum(results)
    print()
    print(f"{passed}/{len(results)} fixtures passed")
    raise SystemExit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
