# WebSocket 챗봇 핸들러 백업
# SSE 방식으로 전환하면서 제거된 코드
# 원본 위치: app/services/chat.py - ChatService.handle_websocket
#            app/apis/v1/chat_routers.py - websocket_chat

# ── service (app/services/chat.py) ──────────────────────────────────────────

# async def handle_websocket(self, websocket: WebSocket, session_id: str, user_id: int) -> None:
#     await websocket.accept()
#     redis = await get_redis()
#
#     try:
#         while True:
#             user_text = await websocket.receive_text()
#             if not user_text.strip():
#                 continue
#
#             await self.repo.create_message(session_id, MessageRole.USER, user_text)
#
#             history = await self.repo.get_messages(session_id, limit=20)
#             history_payload = [{"role": msg.role, "content": msg.content} for msg in history[:-1]]
#
#             health_profile = await HealthProfile.get_or_none(user_id=user_id)
#             health_context = (
#                 {
#                     "primary_conditions": health_profile.primary_conditions,
#                     "allergies": health_profile.allergies,
#                     "current_medications": health_profile.current_medications,
#                     "lifestyle_exercise": health_profile.lifestyle_exercise,
#                     "lifestyle_smoking": health_profile.lifestyle_smoking,
#                     "lifestyle_alcohol": health_profile.lifestyle_alcohol,
#                 }
#                 if health_profile
#                 else None
#             )
#
#             task_payload = json.dumps(
#                 {
#                     "session_id": session_id,
#                     "user_message": user_text,
#                     "history": history_payload,
#                     "health_profile": health_context,
#                 }
#             )
#             await redis.publish(f"chat:request:{session_id}", task_payload)
#
#             pubsub = redis.pubsub()
#             await pubsub.subscribe(f"chat:stream:{session_id}")
#
#             full_response: list[str] = []
#             async for redis_msg in pubsub.listen():
#                 if redis_msg["type"] != "message":
#                     continue
#                 data: str = redis_msg["data"]
#                 if data.startswith("[ERROR]"):
#                     await websocket.send_text(json.dumps({"type": "error", "content": data[7:]}))
#                     break
#                 if data == "[DONE]":
#                     break
#                 full_response.append(data)
#                 await websocket.send_text(json.dumps({"type": "stream", "content": data}))
#
#             await pubsub.unsubscribe(f"chat:stream:{session_id}")
#             await pubsub.aclose()
#
#             complete_text = "".join(full_response)
#             if complete_text:
#                 await self.repo.create_message(session_id, MessageRole.ASSISTANT, complete_text)
#                 await self.repo.touch_session(session_id)
#
#             await websocket.send_text(json.dumps({"type": "done", "content": complete_text}))
#
#     except WebSocketDisconnect:
#         pass


# ── router (app/apis/v1/chat_routers.py) ────────────────────────────────────

# @chat_router.websocket("/ws/{session_id}")
# async def websocket_chat(
#     websocket: WebSocket,
#     session_id: str,
#     token: str,
#     db_session: Annotated[AsyncSession, Depends(get_async_session)],
# ) -> None:
#     try:
#         verified = JwtService().verify_jwt(token=token, token_type="access")
#         user_id: int = verified.payload["user_id"]
#     except HTTPException:
#         await websocket.close(code=1008)
#         return
#
#     session = await ChatRepository(db_session).get_session(session_id, user_id)
#     if not session:
#         await websocket.close(code=1008)
#         return
#
#     await ChatService(db_session).handle_websocket(websocket, session_id, user_id)
