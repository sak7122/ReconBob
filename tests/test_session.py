"""Session state-machine tests. Store is faked via monkeypatch — no Firestore."""
import src.session as session


class FakeStore:
    def __init__(self, current=None):
        self.current = current
        self.cleared = False
        self.line_updates = []
        self.memos = []

    def get_session(self, phone):
        return self.current

    def clear_session(self, phone):
        self.cleared = True

    def set_line_item_business(self, phone, rid, idx, is_business):
        self.line_updates.append((rid, idx, is_business))

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
