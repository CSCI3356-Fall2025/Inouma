# social/admin.py
from django.contrib import admin
from .models import (
    Project, ProjectImage, ProjectLike, ProjectComment,
    Friendship, UserStats, Badge, UserBadge
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'status', 'likes_count', 'views_count', 'created_at']
    list_filter = ['status', 'categories', 'created_at']
    search_fields = ['title', 'description', 'user__email', 'user__first_name']
    readonly_fields = ['likes_count', 'comments_count', 'views_count', 'created_at', 'updated_at']
    filter_horizontal = ['machines_used']


@admin.register(ProjectImage)
class ProjectImageAdmin(admin.ModelAdmin):
    list_display = ['project', 'caption', 'order', 'created_at']
    list_filter = ['created_at']


@admin.register(ProjectComment)
class ProjectCommentAdmin(admin.ModelAdmin):
    list_display = ['project', 'user', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'user__email']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ['from_user', 'to_user', 'status', 'created_at', 'accepted_at']
    list_filter = ['status', 'created_at']
    search_fields = ['from_user__email', 'to_user__email']


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'xp_points', 'projects_count', 'trainings_completed', 'friends_count']
    search_fields = ['user__email', 'user__first_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['icon', 'name', 'category', 'rarity', 'xp_reward', 'is_active']
    list_filter = ['category', 'rarity', 'is_active']
    search_fields = ['name', 'description']


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'badge', 'earned_at']
    list_filter = ['badge', 'earned_at']
    search_fields = ['user__email', 'badge__name']