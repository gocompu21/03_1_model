"""
세션 타임아웃된 사용자의 logout_time을 자동 기록하는 관리 명령어
사용법: python manage.py cleanup_sessions
크론으로 5분마다 실행 권장: */5 * * * * python manage.py cleanup_sessions
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from accounts.models import UserSession


class Command(BaseCommand):
    help = '세션 타임아웃된 사용자 세션을 정리하고 logout_time을 기록합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='비활성 시간 (분) - 기본값 30분',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 업데이트 없이 확인만',
        )

    def handle(self, *args, **options):
        timeout_minutes = options['timeout']
        dry_run = options['dry_run']
        
        # 타임아웃 기준 시간
        cutoff_time = timezone.now() - timedelta(minutes=timeout_minutes)
        
        # logout_time이 없고, last_activity가 타임아웃보다 오래된 세션
        stale_sessions = UserSession.objects.filter(
            logout_time__isnull=True,
            last_activity__lt=cutoff_time
        )
        
        count = stale_sessions.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('정리할 세션이 없습니다.'))
            return
        
        if dry_run:
            self.stdout.write(f'[DRY-RUN] {count}개의 세션이 타임아웃 처리될 예정:')
            for session in stale_sessions[:10]:
                self.stdout.write(f'  - {session.user.username}: 마지막 활동 {session.last_activity}')
            if count > 10:
                self.stdout.write(f'  ... 그 외 {count - 10}개')
        else:
            # 각 세션의 logout_time을 last_activity로 설정 (실제 비활성 시점)
            for session in stale_sessions:
                session.logout_time = session.last_activity
                session.save(update_fields=['logout_time'])
            
            self.stdout.write(self.style.SUCCESS(f'{count}개의 세션을 정리했습니다.'))
