from rest_framework import serializers
from .models import User, StudentProfile, TrainerProfile


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ['major1', 'major2', 'minor1', 'minor2']


class TrainerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainerProfile
        fields = ['specialty', 'bio', 'certifications']


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    student_profile = StudentProfileSerializer(read_only=True)
    trainer_profile = TrainerProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'firebase_uid', 'email', 'password', 'first_name', 'last_name',
            'role', 'student_profile', 'trainer_profile'
        ]

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
