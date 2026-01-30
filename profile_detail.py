import time
import django
from django.conf import settings
from django.template.loader import render_to_string
from django.test import RequestFactory
import cProfile
import pstats
import io

import os

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from study.views import detail
from exam.models import Exam, Question
from django.contrib.auth.models import User


def profile_round(round_number):
    print(f"--- Profiling Round {round_number} (Optimized View) ---")
    
    start_total = time.time()
    
    request = RequestFactory().get(f'/study/{round_number}/')
    user = User.objects.first()
    if not user:
        user = User.objects.create_user(username='testviewer', password='password')
    request.user = user
    
    # Warm up
    print("Warming up...")
    detail(request, round_number)
    
    print("Starting Profiled View Call...")
    pr = cProfile.Profile()
    pr.enable()
    
    response = detail(request, round_number)
    
    pr.disable()
    t3 = time.time()
    print(f"View Total Time: {t3 - start_total:.4f}s")
    
    # Print Top 100 time-consuming functions
    s = io.StringIO()
    sortby = 'cumulative'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats(100)
    
    with open('profile_output.txt', 'w', encoding='utf-8') as f:
        f.write(s.getvalue())
    
    print("Profiling saved to profile_output.txt")

if __name__ == "__main__":
    # Ensure round 7 exists or fallback
    if not Exam.objects.filter(round_number=7).exists():
        print("Round 7 not found, trying Round 6")
        profile_round(6)
    else:
        profile_round(7)
