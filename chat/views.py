from uuid import uuid4
from datetime import datetime, timezone

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema

from .serializers import SessionCreateSerializer, SessionSendSerializer
from .services.rag_chat import generate_rag_answer, list_generate_content_models
from .services.session_store import delete_session, load_messages, save_messages
from organizations.permissions import HasOrganization


class SessionChatViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasOrganization]
    # Helps drf-spectacular generate a schema for this ViewSet.
    serializer_class = SessionCreateSerializer

    @action(detail=False, methods=["get"], url_path="models")
    @extend_schema(
        responses={200: OpenApiResponse(description="List available GenAI chat models (best-effort).")},
        tags=["chat"],
        operation_id="chat_models",
    )
    def models(self, request):
        return Response({"models": list_generate_content_models()})

    @extend_schema(
        request=SessionCreateSerializer,
        responses={200: OpenApiResponse(description="Session created (Redis-backed).")},
        tags=["chat"],
        operation_id="chat_session_create",
    )
    def create(self, request):
        serializer = SessionCreateSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        session_id = str(uuid4())

        save_messages(
            organization_id=request.user.organization_id,
            user_id=request.user.id,
            session_id=session_id,
            messages=[],
            ttl_seconds=int(request.query_params.get("ttl", 21600)),
        )

        return Response({"session_id": session_id, "title": serializer.validated_data.get("title", "")})

    def retrieve(self, request, pk=None):
        messages = load_messages(
            organization_id=request.user.organization_id,
            user_id=request.user.id,
            session_id=pk,
        )
        return Response({"session_id": pk, "messages": messages})

    def destroy(self, request, pk=None):
        delete_session(
            organization_id=request.user.organization_id,
            user_id=request.user.id,
            session_id=pk,
        )
        return Response(status=204)

    @action(detail=True, methods=["get", "post"], url_path="messages")
    @extend_schema(
        methods=["GET"],
        responses={200: OpenApiResponse(description="Get session messages.")},
        tags=["chat"],
        operation_id="chat_session_messages_list",
    )
    @extend_schema(
        methods=["POST"],
        request=SessionSendSerializer,
        responses={200: OpenApiResponse(description="Send a message and receive an assistant response.")},
        tags=["chat"],
        operation_id="chat_session_messages_send",
    )
    def messages(self, request, pk=None):
        if request.method == "GET":
            messages = load_messages(
                organization_id=request.user.organization_id,
                user_id=request.user.id,
                session_id=pk,
            )
            return Response({"session_id": pk, "messages": messages})

        serializer = SessionSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ttl_seconds = int(request.query_params.get("ttl", 21600))
        content = serializer.validated_data["content"].strip()
        top_k = serializer.validated_data.get("top_k", 5)
        history_max_messages = serializer.validated_data.get("history_max_messages", 20)

        history = load_messages(
            organization_id=request.user.organization_id,
            user_id=request.user.id,
            session_id=pk,
        )

        now = datetime.now(timezone.utc).isoformat()
        history.append({"role": "user", "content": content, "created_at": now})

        answer, sources = generate_rag_answer(
            query=content,
            organization_id=request.user.organization_id,
            top_k=top_k,
            history=history,
            history_max_messages=history_max_messages,
        )

        history.append({"role": "assistant", "content": answer, "sources": sources, "created_at": now})

        max_messages = int(request.query_params.get("max_messages", 30))
        if len(history) > max_messages:
            history = history[-max_messages:]

        save_messages(
            organization_id=request.user.organization_id,
            user_id=request.user.id,
            session_id=pk,
            messages=history,
            ttl_seconds=ttl_seconds,
        )

        return Response(
            {
                "session_id": pk,
                "assistant_message": {"role": "assistant", "content": answer, "sources": sources, "created_at": now},
            }
        )
