"""Session state-machine tests. Store is faked via monkeypatch — no Firestore."""
import src.session as session


class FakeStore:
    def __init__(self, current=None):
        self.current = current
        self.cleared = False
        self.line_updates = []
        self.memos = []
        self.sessions_opened = []

    def get_session(self, phone):
        return self.current

    def clear_session(self, phone):
        self.cleared = True
        self.current = None

    def open_session(self, phone, pending_action, context):
        self.sessions_opened.append((pending_action, context))
        self.current = {"pending_action": pending_action, "context": context}

    def set_line_item_business(self, phone, rid, idx, is_business):
        self.line_updates.append((rid, idx, is_business))
        return True  # simulate successful update

    def create_unverified_memo(self, phone, txn_id, note):
        self.memos.append((txn_id, note))
        return "memo1"

    def log_agent_step(self, payload):
        pass


def _patch(monkeypatch, fake):
    monkeypatch.setattr(session, "store", fake)


def test_no_session_returns_greeting(monkeypatch):
    _patch(monkeypatch, FakeStore(current=None))
    assert "photo" in session.handle_text("p", "hi").lower()


def test_split_business(monkeypatch):
    fake = FakeStore(current={"pending_action": "confirm_split",
                              "context": {"receipt_id": "r1", "line_index": 1,
                                          "description": "tape measure"}})
    _patch(monkeypatch, fake)
    reply = session.handle_text("p", "business")
    assert fake.line_updates == [("r1", 1, True)]
    assert fake.cleared
    assert "business" in reply.lower()


def test_split_personal(monkeypatch):
    fake = FakeStore(current={"pending_action": "confirm_split",
                              "context": {"receipt_id": "r1", "line_index": 0,
                                          "description": "snacks"}})
    _patch(monkeypatch, fake)
    session.handle_text("p", "personal")
    assert fake.line_updates == [("r1", 0, False)]


def test_split_unrecognized_keeps_session(monkeypatch):
    fake = FakeStore(current={"pending_action": "confirm_split",
                              "context": {"receipt_id": "r1", "line_index": 0}})
    _patch(monkeypatch, fake)
    reply = session.handle_text("p", "maybe?")
    assert not fake.cleared
    assert "business" in reply.lower() and "personal" in reply.lower()


def test_need_receipt_text_creates_memo(monkeypatch):
    fake = FakeStore(current={"pending_action": "need_receipt",
                              "context": {"txn_id": "t1", "amount": 320.0,
                                          "merchant": "City Electric"}})
    _patch(monkeypatch, fake)
    reply = session.handle_text("p", "Smith job wire")
    assert fake.memos == [("t1", "Smith job wire")]
    assert "unverified memo" in reply.lower()
    assert fake.cleared  # no queue → session should be cleared


def test_need_receipt_queue_advances_to_next(monkeypatch):
    """After answering first orphan, session advances to the second one."""
    queue = [{"txn_id": "t2", "amount": 55.0, "merchant": "Shell"}]
    fake = FakeStore(current={"pending_action": "need_receipt",
                              "context": {"txn_id": "t1", "amount": 320.0,
                                          "merchant": "City Electric", "queue": queue}})
    _patch(monkeypatch, fake)
    reply = session.handle_text("p", "Smith job wire")
    assert fake.memos == [("t1", "Smith job wire")]
    # Session should NOT be cleared — it advances to t2
    assert not fake.cleared
    # A new session should have been opened for t2
    assert len(fake.sessions_opened) == 1
    _, ctx = fake.sessions_opened[0]
    assert ctx["txn_id"] == "t2"
    assert ctx["queue"] == []
    # Reply should mention the next charge
    assert "Shell" in reply or "55" in reply


def test_need_receipt_last_in_queue_clears_session(monkeypatch):
    """Answering the last orphan in the queue clears the session."""
    fake = FakeStore(current={"pending_action": "need_receipt",
                              "context": {"txn_id": "t2", "amount": 55.0,
                                          "merchant": "Shell", "queue": []}})
    _patch(monkeypatch, fake)
    session.handle_text("p", "fuel for the truck")
    assert fake.cleared


def test_unknown_pending_action_clears_session(monkeypatch):
    """A stale or unrecognised pending_action results in a greeting and cleared session."""
    fake = FakeStore(current={"pending_action": "obsolete_action", "context": {}})
    _patch(monkeypatch, fake)
    reply = session.handle_text("p", "hello")
    assert fake.cleared
    assert "photo" in reply.lower()
