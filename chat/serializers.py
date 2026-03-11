from rest_framework import serializers


class SessionCreateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True)


class SessionSendSerializer(serializers.Serializer):
    content = serializers.CharField()
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)
    history_max_messages = serializers.IntegerField(required=False, min_value=0, max_value=50, default=20)
