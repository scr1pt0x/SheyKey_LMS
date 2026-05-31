"""Unit tests for deal status machine transitions."""
import pytest


VALID_TRANSITIONS = {
    "draft": ["pending", "active"],
    "pending": ["active", "draft"],
    "active": ["closed", "overdue"],
    "overdue": ["active", "closed"],
    "closed": [],
}

INVALID_TRANSITIONS = {
    "draft": ["closed", "overdue"],
    "pending": ["overdue", "closed"],
    "active": ["draft", "pending"],
    "overdue": ["draft", "pending"],
    "closed": ["draft", "pending", "active", "overdue"],
}


def is_valid_transition(from_status: str, to_status: str) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, [])


class TestDealStatusMachine:
    def test_draft_to_pending(self):
        assert is_valid_transition("draft", "pending") is True

    def test_draft_to_active_manager_activate(self):
        assert is_valid_transition("draft", "active") is True

    def test_pending_to_active(self):
        assert is_valid_transition("pending", "active") is True

    def test_pending_to_draft_rejection(self):
        assert is_valid_transition("pending", "draft") is True

    def test_active_to_closed(self):
        assert is_valid_transition("active", "closed") is True

    def test_active_to_overdue(self):
        assert is_valid_transition("active", "overdue") is True

    def test_overdue_to_active_after_payment(self):
        assert is_valid_transition("overdue", "active") is True

    def test_overdue_to_closed(self):
        assert is_valid_transition("overdue", "closed") is True

    def test_draft_cannot_go_overdue(self):
        assert is_valid_transition("draft", "overdue") is False

    def test_pending_cannot_go_overdue(self):
        assert is_valid_transition("pending", "overdue") is False

    def test_closed_is_terminal(self):
        for target in ["draft", "pending", "active", "overdue"]:
            assert is_valid_transition("closed", target) is False

    def test_all_invalid_transitions(self):
        for from_status, invalid_targets in INVALID_TRANSITIONS.items():
            for to_status in invalid_targets:
                assert is_valid_transition(from_status, to_status) is False, (
                    f"Expected {from_status}→{to_status} to be invalid"
                )


class TestOverdueCaseStatusMachine:
    VALID_CASE_TRANSITIONS = {
        "new": ["in_progress"],
        "in_progress": ["agreed", "closed"],
        "agreed": ["in_progress", "closed"],
        "closed": [],
    }

    def _is_valid(self, from_s: str, to_s: str) -> bool:
        return to_s in self.VALID_CASE_TRANSITIONS.get(from_s, [])

    def test_new_to_in_progress(self):
        assert self._is_valid("new", "in_progress") is True

    def test_in_progress_to_agreed(self):
        assert self._is_valid("in_progress", "agreed") is True

    def test_in_progress_to_closed(self):
        assert self._is_valid("in_progress", "closed") is True

    def test_agreed_to_closed(self):
        assert self._is_valid("agreed", "closed") is True

    def test_agreed_can_reopen(self):
        assert self._is_valid("agreed", "in_progress") is True

    def test_closed_is_terminal(self):
        for target in ["new", "in_progress", "agreed"]:
            assert self._is_valid("closed", target) is False

    def test_new_cannot_skip_to_closed(self):
        assert self._is_valid("new", "closed") is False
