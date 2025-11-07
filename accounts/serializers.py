# accounts/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    Machine,
    MachineInstance,
    TrainingReservation,
)

User = get_user_model()


# --- Generic user serializer used by existing views ---
class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        # Prefer Django's get_full_name if available; otherwise join first/last; fallback to email
        try:
            name = obj.get_full_name()
            if name:
                return name
        except Exception:
            pass
        first = getattr(obj, "first_name", "") or ""
        last = getattr(obj, "last_name", "") or ""
        name = (first + " " + last).strip()
        return name or getattr(obj, "email", "")

    def get_role(self, obj):
        # Return role if your User has it; otherwise empty string
        return getattr(obj, "role", "")

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role"]


# --- Machines / booking serializers for Delivery 4 ---
class MachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Machine
        fields = ["id", "name", "category", "location", "description", "required_training_level"]


class MachineInstanceSerializer(serializers.ModelSerializer):
    machine = MachineSerializer(read_only=True)

    class Meta:
        model = MachineInstance
        fields = ["id", "nickname", "status", "machine"]


class TrainingReservationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingReservation
        fields = ["trainer", "machine_instance", "start_time", "end_time"]

    def validate(self, attrs):
        start = attrs["start_time"]
        end = attrs["end_time"]
        if end <= start:
            raise serializers.ValidationError("end_time must be after start_time")

        trainer = attrs["trainer"]
        # strict no-overlap for the same trainer
        qs = TrainingReservation.objects.filter(trainer=trainer, status="CONFIRMED")
        for r in qs:
            # overlap if not (r ends before start OR r starts after end)
            if not (r.end_time <= start or r.start_time >= end):
                raise serializers.ValidationError("This trainer is already booked for that time range.")
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return TrainingReservation.objects.create(student=user, **validated_data)


class TrainingReservationSerializer(serializers.ModelSerializer):
    trainer_email = serializers.CharField(source="trainer.email", read_only=True)
    machine_instance = MachineInstanceSerializer(read_only=True)

    class Meta:
        model = TrainingReservation
        fields = [
            "id",
            "status",
            "start_time",
            "end_time",
            "trainer_email",
            "machine_instance",
            "created_at",
        ]
