"""
Management command to generate TrainingSessions from scheduled training shifts.

Usage:
    python manage.py generate_training_sessions                    # Generate for next 14 days
    python manage.py generate_training_sessions --days 30          # Generate for next 30 days
    python manage.py generate_training_sessions --date 2025-01-15  # Generate for specific date
    python manage.py generate_training_sessions --dry-run          # Preview without creating
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta, date

from reservations.models import TrainingSession
from scheduling.models import Shift
from machines.models import Training


class Command(BaseCommand):
    help = 'Generate TrainingSession records from scheduled training shifts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=14,
            help='Number of days ahead to generate sessions for (default: 14)'
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Generate sessions for a specific date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be created without actually creating'
        )
        parser.add_argument(
            '--trainer',
            type=int,
            help='Only generate for a specific trainer (user ID)'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Only generate for a specific category'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate sessions even if they already exist (deletes existing first)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days = options['days']
        specific_date = options.get('date')
        trainer_id = options.get('trainer')
        category_filter = options.get('category')
        force = options.get('force', False)

        # Determine date range
        if specific_date:
            try:
                start_date = datetime.strptime(specific_date, '%Y-%m-%d').date()
                end_date = start_date
            except ValueError:
                raise CommandError(f'Invalid date format: {specific_date}. Use YYYY-MM-DD.')
        else:
            start_date = timezone.now().date()
            end_date = start_date + timedelta(days=days)

        self.stdout.write(f'\nGenerating training sessions from {start_date} to {end_date}')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No records will be created\n'))
        if force:
            self.stdout.write(self.style.WARNING('FORCE MODE - Existing sessions will be recreated\n'))

        # Get training shifts in date range
        shifts = Shift.objects.filter(
            shift_type='training',
            date__gte=start_date,
            date__lte=end_date
        ).select_related('user', 'location')

        if trainer_id:
            shifts = shifts.filter(user_id=trainer_id)

        if category_filter:
            shifts = shifts.filter(team_category__icontains=category_filter)

        self.stdout.write(f'Found {shifts.count()} training shifts\n')

        if shifts.count() == 0:
            self.stdout.write(self.style.WARNING('No training shifts found. Make sure shifts exist with shift_type="training"'))
            return

        created_count = 0
        skipped_count = 0
        error_count = 0

        # Get all active trainings grouped by category
        trainings_by_category = {}
        for training in Training.objects.filter(status='active'):
            cat = (training.category or 'general').lower().strip()
            if cat not in trainings_by_category:
                trainings_by_category[cat] = []
            trainings_by_category[cat].append(training)

        self.stdout.write(f'Found trainings in categories: {list(trainings_by_category.keys())}\n')

        with transaction.atomic():
            for shift in shifts:
                try:
                    # Check if session already exists for this shift
                    existing = TrainingSession.objects.filter(source_shift=shift)
                    
                    if existing.exists():
                        if force:
                            # Delete existing sessions without bookings
                            deleted = existing.filter(bookings__isnull=True).delete()
                            self.stdout.write(
                                f'  DELETED: {deleted[0]} existing session(s) for shift {shift.id}'
                            )
                        else:
                            self.stdout.write(
                                f'  SKIP: Session already exists for shift {shift.id} '
                                f'({shift.date} {shift.start_time})'
                            )
                            skipped_count += 1
                            continue

                    # Determine category from shift
                    category = (shift.team_category or 'general').strip()
                    category_lower = category.lower()

                    # Find matching trainings for this category
                    matching_trainings = trainings_by_category.get(category_lower, [])
                    
                    # Try fuzzy match if exact match fails
                    if not matching_trainings:
                        for cat_key, trainings in trainings_by_category.items():
                            if cat_key in category_lower or category_lower in cat_key:
                                matching_trainings = trainings
                                break
                    
                    # Try without "team" suffix
                    if not matching_trainings and 'team' in category_lower:
                        cat_without_team = category_lower.replace('team', '').strip()
                        matching_trainings = trainings_by_category.get(cat_without_team, [])

                    if not matching_trainings:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  WARN: No trainings found for category "{category}" '
                                f'(shift {shift.id}). Available: {list(trainings_by_category.keys())}'
                            )
                        )
                        skipped_count += 1
                        continue

                    # Use the first training by level (Level 1 first)
                    # Each shift = one training session for simplicity
                    training = sorted(matching_trainings, key=lambda t: t.level)[0]

                    # Get location from shift
                    location = shift.location

                    # Determine max participants
                    max_participants = getattr(training, 'max_participants', None) or 4

                    if dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  CREATE: {training.name} (L{training.level}) - '
                                f'{shift.date} {shift.start_time}-{shift.end_time} - '
                                f'Trainer: {shift.user.get_full_name() or shift.user.email}'
                            )
                        )
                        created_count += 1
                    else:
                        session = TrainingSession.objects.create(
                            training=training,
                            trainer=shift.user,
                            date=shift.date,
                            start_time=shift.start_time,
                            end_time=shift.end_time,
                            location=location,
                            max_participants=max_participants,
                            source_shift=shift,
                            status='available',
                            notes=f'Auto-generated from shift #{shift.id}'
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  CREATED: {training.name} (L{training.level}) - '
                                f'{shift.date} {shift.start_time}-{shift.end_time} - '
                                f'Trainer: {shift.user.get_full_name() or shift.user.email} '
                                f'[Session #{session.id}]'
                            )
                        )
                        created_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ERROR processing shift {shift.id}: {str(e)}')
                    )
                    error_count += 1
                    import traceback
                    traceback.print_exc()

            if dry_run:
                # Rollback in dry run mode
                transaction.set_rollback(True)

        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('Summary:')
        self.stdout.write(f'  Created: {created_count}')
        self.stdout.write(f'  Skipped: {skipped_count}')
        self.stdout.write(f'  Errors:  {error_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - No records were actually created'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {created_count} training sessions'))