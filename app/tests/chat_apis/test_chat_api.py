import pytest

pytestmark = pytest.mark.skip(
    reason="chat API가 /sessions + WebSocket 구조로 리팩토링됨. 이 파일은 구 /conversations REST 흐름을 가정하므로 재작성 필요."
)
