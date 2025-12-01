# social/views.py
"""
Views and API endpoints for social features.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

from .models import (
    Project, ProjectImage, ProjectLike, ProjectComment,
    Friendship, UserStats, Badge, UserBadge
)

User = get_user_model()


# ============================================================================
# PAGE VIEWS
# ============================================================================

@login_required
def projects_feed(request):
    """Main projects feed/forum page."""
    return render(request, 'social/projects_feed.html')


@login_required
def project_detail(request, project_id):
    """Single project detail page."""
    project = get_object_or_404(
        Project.objects.select_related('user').prefetch_related('images', 'machines_used'),
        id=project_id,
        status='published'
    )
    
    # Increment view count
    project.views_count += 1
    project.save(update_fields=['views_count'])
    
    return render(request, 'social/project_detail.html', {'project': project})


@login_required
def create_project(request):
    """Create new project page."""
    return render(request, 'social/create_project.html')


@login_required
def edit_project(request, project_id):
    """Edit existing project page."""
    project = get_object_or_404(Project, id=project_id, user=request.user)
    return render(request, 'social/edit_project.html', {'project': project})


@login_required
def friends_page(request):
    """Friends list and friend requests page."""
    return render(request, 'social/friends.html')


@login_required
def user_profile(request, user_id):
    """View another user's profile."""
    profile_user = get_object_or_404(User, id=user_id)
    return render(request, 'social/user_profile.html', {'profile_user': profile_user})


@login_required
def leaderboard(request):
    """Gamification leaderboard page."""
    return render(request, 'social/leaderboard.html')


# ============================================================================
# PROJECT API ENDPOINTS
# ============================================================================

@login_required
@require_GET
def api_projects_list(request):
    """Get paginated list of projects with filtering."""
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 12))
    category = request.GET.get('category', '')
    machine_type = request.GET.get('machine_type', '')
    user_id = request.GET.get('user_id', '')
    sort = request.GET.get('sort', 'recent')  # recent, popular, most_liked
    
    projects = Project.objects.filter(status='published').select_related('user')
    
    # Filters
    if category:
        projects = projects.filter(categories__contains=[category])
    
    if machine_type:
        projects = projects.filter(machine_types_used__contains=[machine_type])
    
    if user_id:
        projects = projects.filter(user_id=user_id)
    
    # Sorting
    if sort == 'popular':
        projects = projects.order_by('-views_count', '-created_at')
    elif sort == 'most_liked':
        projects = projects.order_by('-likes_count', '-created_at')
    else:  # recent
        projects = projects.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(projects, per_page)
    page_obj = paginator.get_page(page)
    
    # Check if current user liked each project
    user_likes = set(
        ProjectLike.objects.filter(
            user=request.user,
            project__in=page_obj.object_list
        ).values_list('project_id', flat=True)
    )
    
    projects_data = []
    for project in page_obj.object_list:
        projects_data.append({
            'id': project.id,
            'title': project.title,
            'description': project.description[:200] + '...' if len(project.description) > 200 else project.description,
            'cover_image': project.cover_image.url if project.cover_image else None,
            'author_id': project.user_id,
            'author_name': project.author_name,
            'author_avatar': None,  # Add avatar URL if you have it
            'categories': project.categories,
            'machine_types_used': project.machine_types_used,
            'likes_count': project.likes_count,
            'comments_count': project.comments_count,
            'views_count': project.views_count,
            'is_liked': project.id in user_likes,
            'created_at': project.created_at.isoformat(),
        })
    
    return JsonResponse({
        'success': True,
        'projects': projects_data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    })


@login_required
@require_GET
def api_project_detail(request, project_id):
    """Get single project details."""
    project = get_object_or_404(
        Project.objects.select_related('user').prefetch_related('images', 'machines_used'),
        id=project_id
    )
    
    # Check if user can view (published or own project)
    if project.status != 'published' and project.user != request.user:
        return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
    
    # Check if user liked this project
    is_liked = ProjectLike.objects.filter(project=project, user=request.user).exists()
    
    # Get machines used
    machines = [{
        'id': m.id,
        'name': m.name,
        'machine_name': m.machine_name,
        'category': m.category,
    } for m in project.machines_used.all()]
    
    # Get images
    images = [{
        'id': img.id,
        'url': img.image.url,
        'caption': img.caption,
    } for img in project.images.all()]
    
    return JsonResponse({
        'success': True,
        'project': {
            'id': project.id,
            'title': project.title,
            'description': project.description,
            'cover_image': project.cover_image.url if project.cover_image else None,
            'images': images,
            'author_id': project.user_id,
            'author_name': project.author_name,
            'categories': project.categories,
            'machine_types_used': project.machine_types_used,
            'machines_used': machines,
            'likes_count': project.likes_count,
            'comments_count': project.comments_count,
            'views_count': project.views_count,
            'is_liked': is_liked,
            'is_owner': project.user == request.user,
            'status': project.status,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
        }
    })


@login_required
@require_POST
def api_create_project(request):
    """Create a new project."""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'success': False, 'error': 'Title is required'})
        
        description = data.get('description', '').strip()
        if not description:
            return JsonResponse({'success': False, 'error': 'Description is required'})
        
        project = Project.objects.create(
            user=request.user,
            title=title,
            description=description,
            categories=data.get('categories', []),
            machine_types_used=data.get('machine_types_used', []),
            status=data.get('status', 'published'),
        )
        
        # Add machines used
        machine_ids = data.get('machine_ids', [])
        if machine_ids:
            from machines.models import Machine
            machines = Machine.objects.filter(id__in=machine_ids)
            project.machines_used.set(machines)
        
        # Update user stats
        stats = UserStats.get_or_create_for_user(request.user)
        stats.projects_count += 1
        stats.add_xp(25, 'Created a project')
        
        return JsonResponse({
            'success': True,
            'project_id': project.id,
            'message': 'Project created successfully!'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def api_update_project(request, project_id):
    """Update an existing project."""
    project = get_object_or_404(Project, id=project_id, user=request.user)
    
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        if 'title' in data:
            project.title = data['title'].strip()
        if 'description' in data:
            project.description = data['description'].strip()
        if 'categories' in data:
            project.categories = data['categories']
        if 'machine_types_used' in data:
            project.machine_types_used = data['machine_types_used']
        if 'status' in data:
            project.status = data['status']
        
        project.save()
        
        # Update machines used
        if 'machine_ids' in data:
            from machines.models import Machine
            machines = Machine.objects.filter(id__in=data['machine_ids'])
            project.machines_used.set(machines)
        
        return JsonResponse({'success': True, 'message': 'Project updated'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def api_delete_project(request, project_id):
    """Delete a project."""
    project = get_object_or_404(Project, id=project_id, user=request.user)
    
    project.delete()
    
    # Update user stats
    stats = UserStats.get_or_create_for_user(request.user)
    stats.projects_count = max(0, stats.projects_count - 1)
    stats.save()
    
    return JsonResponse({'success': True, 'message': 'Project deleted'})


@login_required
@require_POST
def api_like_project(request, project_id):
    """Like or unlike a project."""
    project = get_object_or_404(Project, id=project_id, status='published')
    
    like, created = ProjectLike.objects.get_or_create(
        project=project,
        user=request.user
    )
    
    if not created:
        # Already liked, so unlike
        like.delete()
        project.likes_count = max(0, project.likes_count - 1)
        project.save(update_fields=['likes_count'])
        
        return JsonResponse({
            'success': True,
            'liked': False,
            'likes_count': project.likes_count
        })
    else:
        # New like
        project.likes_count += 1
        project.save(update_fields=['likes_count'])
        
        # Add XP to project owner
        if project.user != request.user:
            owner_stats = UserStats.get_or_create_for_user(project.user)
            owner_stats.total_likes_received += 1
            owner_stats.add_xp(5, 'Received a like')
        
        return JsonResponse({
            'success': True,
            'liked': True,
            'likes_count': project.likes_count
        })


@login_required
@require_GET
def api_project_comments(request, project_id):
    """Get comments for a project."""
    project = get_object_or_404(Project, id=project_id, status='published')
    
    comments = ProjectComment.objects.filter(
        project=project,
        parent__isnull=True  # Top-level comments only
    ).select_related('user').prefetch_related('replies__user').order_by('-created_at')
    
    comments_data = []
    for comment in comments:
        replies_data = [{
            'id': reply.id,
            'content': reply.content,
            'author_id': reply.user_id,
            'author_name': reply.user.get_full_name() or reply.user.email.split('@')[0],
            'created_at': reply.created_at.isoformat(),
        } for reply in comment.replies.all()]
        
        comments_data.append({
            'id': comment.id,
            'content': comment.content,
            'author_id': comment.user_id,
            'author_name': comment.user.get_full_name() or comment.user.email.split('@')[0],
            'created_at': comment.created_at.isoformat(),
            'replies': replies_data,
        })
    
    return JsonResponse({
        'success': True,
        'comments': comments_data
    })


@login_required
@require_POST
def api_add_comment(request, project_id):
    """Add a comment to a project."""
    project = get_object_or_404(Project, id=project_id, status='published')
    
    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        parent_id = data.get('parent_id')
        
        if not content:
            return JsonResponse({'success': False, 'error': 'Comment cannot be empty'})
        
        parent = None
        if parent_id:
            parent = get_object_or_404(ProjectComment, id=parent_id, project=project)
        
        comment = ProjectComment.objects.create(
            project=project,
            user=request.user,
            content=content,
            parent=parent
        )
        
        # Update comment count
        project.comments_count += 1
        project.save(update_fields=['comments_count'])
        
        # Add XP for commenting
        stats = UserStats.get_or_create_for_user(request.user)
        stats.add_xp(5, 'Posted a comment')
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'author_name': request.user.get_full_name() or request.user.email.split('@')[0],
                'created_at': comment.created_at.isoformat(),
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ============================================================================
# FRIEND API ENDPOINTS
# ============================================================================

@login_required
@require_GET
def api_friends_list(request):
    """Get user's friends and pending requests."""
    user = request.user
    
    # Accepted friends
    friendships = Friendship.objects.filter(
        Q(from_user=user, status='accepted') | Q(to_user=user, status='accepted')
    ).select_related('from_user', 'to_user')
    
    friends = []
    for f in friendships:
        friend = f.to_user if f.from_user == user else f.from_user
        friend_stats = UserStats.get_or_create_for_user(friend)
        
        friends.append({
            'id': friend.id,
            'name': friend.get_full_name() or friend.email.split('@')[0],
            'email': friend.email,
            'level': friend_stats.level,
            'xp': friend_stats.xp_points,
            'projects_count': friend_stats.projects_count,
            'trainings_completed': friend_stats.trainings_completed,
            'friendship_id': f.id,
            'friends_since': f.accepted_at.isoformat() if f.accepted_at else None,
        })
    
    # Pending requests (received)
    pending_received = Friendship.objects.filter(
        to_user=user,
        status='pending'
    ).select_related('from_user')
    
    pending_requests = [{
        'id': f.id,
        'from_user_id': f.from_user_id,
        'from_user_name': f.from_user.get_full_name() or f.from_user.email.split('@')[0],
        'sent_at': f.created_at.isoformat(),
    } for f in pending_received]
    
    # Pending requests (sent)
    pending_sent = Friendship.objects.filter(
        from_user=user,
        status='pending'
    ).select_related('to_user')
    
    sent_requests = [{
        'id': f.id,
        'to_user_id': f.to_user_id,
        'to_user_name': f.to_user.get_full_name() or f.to_user.email.split('@')[0],
        'sent_at': f.created_at.isoformat(),
    } for f in pending_sent]
    
    return JsonResponse({
        'success': True,
        'friends': friends,
        'pending_requests': pending_requests,
        'sent_requests': sent_requests,
    })


@login_required
@require_POST
def api_send_friend_request(request):
    """Send a friend request to another user."""
    try:
        data = json.loads(request.body)
        to_user_id = data.get('user_id')
        
        if not to_user_id:
            return JsonResponse({'success': False, 'error': 'User ID required'})
        
        to_user = get_object_or_404(User, id=to_user_id)
        
        if to_user == request.user:
            return JsonResponse({'success': False, 'error': 'Cannot friend yourself'})
        
        # Check if friendship already exists
        existing = Friendship.objects.filter(
            Q(from_user=request.user, to_user=to_user) |
            Q(from_user=to_user, to_user=request.user)
        ).first()
        
        if existing:
            if existing.status == 'accepted':
                return JsonResponse({'success': False, 'error': 'Already friends'})
            elif existing.status == 'pending':
                return JsonResponse({'success': False, 'error': 'Request already pending'})
            elif existing.status == 'declined':
                # Allow re-requesting after decline
                existing.status = 'pending'
                existing.from_user = request.user
                existing.to_user = to_user
                existing.save()
                return JsonResponse({'success': True, 'message': 'Friend request sent'})
        
        Friendship.objects.create(
            from_user=request.user,
            to_user=to_user,
            status='pending'
        )
        
        return JsonResponse({'success': True, 'message': 'Friend request sent'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def api_respond_friend_request(request, friendship_id):
    """Accept or decline a friend request."""
    friendship = get_object_or_404(
        Friendship,
        id=friendship_id,
        to_user=request.user,
        status='pending'
    )
    
    try:
        data = json.loads(request.body)
        action = data.get('action')  # 'accept' or 'decline'
        
        if action == 'accept':
            friendship.accept()
            
            # Update both users' friend counts
            from_stats = UserStats.get_or_create_for_user(friendship.from_user)
            to_stats = UserStats.get_or_create_for_user(friendship.to_user)
            
            from_stats.friends_count += 1
            to_stats.friends_count += 1
            
            from_stats.add_xp(10, 'Made a new friend')
            to_stats.add_xp(10, 'Made a new friend')
            
            return JsonResponse({'success': True, 'message': 'Friend request accepted'})
            
        elif action == 'decline':
            friendship.decline()
            return JsonResponse({'success': True, 'message': 'Friend request declined'})
        
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def api_remove_friend(request, friendship_id):
    """Remove a friend."""
    friendship = get_object_or_404(
        Friendship,
        Q(from_user=request.user) | Q(to_user=request.user),
        id=friendship_id,
        status='accepted'
    )
    
    # Update friend counts
    from_stats = UserStats.get_or_create_for_user(friendship.from_user)
    to_stats = UserStats.get_or_create_for_user(friendship.to_user)
    
    from_stats.friends_count = max(0, from_stats.friends_count - 1)
    to_stats.friends_count = max(0, to_stats.friends_count - 1)
    from_stats.save()
    to_stats.save()
    
    friendship.delete()
    
    return JsonResponse({'success': True, 'message': 'Friend removed'})


@login_required
@require_GET
def api_search_users(request):
    """Search for users to add as friends."""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'success': True, 'users': []})
    
    users = User.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    ).exclude(id=request.user.id)[:10]
    
    # Get existing friendships
    existing_friendships = Friendship.objects.filter(
        Q(from_user=request.user) | Q(to_user=request.user)
    ).values_list('from_user_id', 'to_user_id', 'status')
    
    friendship_map = {}
    for from_id, to_id, status in existing_friendships:
        other_id = to_id if from_id == request.user.id else from_id
        friendship_map[other_id] = status
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'name': user.get_full_name() or user.email.split('@')[0],
            'email': user.email,
            'friendship_status': friendship_map.get(user.id, None),
        })
    
    return JsonResponse({'success': True, 'users': users_data})


# ============================================================================
# USER PROFILE & STATS API
# ============================================================================

@login_required
@require_GET
def api_user_profile(request, user_id):
    """Get a user's public profile."""
    profile_user = get_object_or_404(User, id=user_id)
    stats = UserStats.get_or_create_for_user(profile_user)
    
    # Check friendship status
    friendship = Friendship.objects.filter(
        Q(from_user=request.user, to_user=profile_user) |
        Q(from_user=profile_user, to_user=request.user)
    ).first()
    
    friendship_status = None
    friendship_id = None
    if friendship:
        friendship_status = friendship.status
        friendship_id = friendship.id
    
    # Get user's public projects
    projects = Project.objects.filter(
        user=profile_user,
        status='published'
    ).order_by('-created_at')[:6]
    
    projects_data = [{
        'id': p.id,
        'title': p.title,
        'cover_image': p.cover_image.url if p.cover_image else None,
        'likes_count': p.likes_count,
    } for p in projects]
    
    # Get earned badges
    badges = UserBadge.objects.filter(user=profile_user).select_related('badge')[:8]
    badges_data = [{
        'id': b.badge.id,
        'name': b.badge.name,
        'icon': b.badge.icon,
        'rarity': b.badge.rarity,
        'earned_at': b.earned_at.isoformat(),
    } for b in badges]
    
    return JsonResponse({
        'success': True,
        'profile': {
            'id': profile_user.id,
            'name': profile_user.get_full_name() or profile_user.email.split('@')[0],
            'is_self': profile_user == request.user,
            'friendship_status': friendship_status,
            'friendship_id': friendship_id,
            'stats': {
                'level': stats.level,
                'xp_points': stats.xp_points,
                'xp_to_next_level': 100 - (stats.xp_points % 100),
                'projects_count': stats.projects_count,
                'total_likes_received': stats.total_likes_received,
                'trainings_completed': stats.trainings_completed,
                'certifications_count': stats.certifications_count,
                'friends_count': stats.friends_count,
                'unique_machines_used': stats.unique_machines_used,
            },
            'projects': projects_data,
            'badges': badges_data,
        }
    })


@login_required
@require_GET
def api_my_stats(request):
    """Get current user's stats."""
    stats = UserStats.get_or_create_for_user(request.user)
    
    return JsonResponse({
        'success': True,
        'stats': {
            'level': stats.level,
            'xp_points': stats.xp_points,
            'xp_to_next_level': 100 - (stats.xp_points % 100),
            'projects_count': stats.projects_count,
            'total_likes_received': stats.total_likes_received,
            'trainings_completed': stats.trainings_completed,
            'certifications_count': stats.certifications_count,
            'friends_count': stats.friends_count,
            'unique_machines_used': stats.unique_machines_used,
            'total_reservations': stats.total_reservations,
        }
    })


@login_required
@require_GET
def api_leaderboard(request):
    """Get leaderboard data."""
    category = request.GET.get('category', 'xp')  # xp, projects, trainings
    
    if category == 'projects':
        stats = UserStats.objects.order_by('-projects_count', '-xp_points')[:20]
        sort_field = 'projects_count'
    elif category == 'trainings':
        stats = UserStats.objects.order_by('-trainings_completed', '-xp_points')[:20]
        sort_field = 'trainings_completed'
    else:  # xp
        stats = UserStats.objects.order_by('-xp_points')[:20]
        sort_field = 'xp_points'
    
    stats = stats.select_related('user')
    
    # Find current user's rank
    user_stats = UserStats.get_or_create_for_user(request.user)
    user_rank = UserStats.objects.filter(**{f'{sort_field}__gt': getattr(user_stats, sort_field)}).count() + 1
    
    leaderboard_data = []
    for i, s in enumerate(stats, 1):
        leaderboard_data.append({
            'rank': i,
            'user_id': s.user_id,
            'name': s.user.get_full_name() or s.user.email.split('@')[0],
            'level': s.level,
            'xp_points': s.xp_points,
            'projects_count': s.projects_count,
            'trainings_completed': s.trainings_completed,
            'is_current_user': s.user == request.user,
        })
    
    return JsonResponse({
        'success': True,
        'leaderboard': leaderboard_data,
        'user_rank': user_rank,
        'user_stats': {
            'level': user_stats.level,
            'xp_points': user_stats.xp_points,
            'projects_count': user_stats.projects_count,
            'trainings_completed': user_stats.trainings_completed,
        }
    })