from core.views import get_template_name
import os
from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings

from .models import Post, Category, Tag, ReadingSession
from .forms import PostForm

# ======================== PUBLIC VIEWS ========================

class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 9
    
    def get_template_names(self):
        if getattr(self.request, 'LANGUAGE_CODE', 'vi') == 'en':
            return [self.template_name.replace('.html', '_en.html')]
        return [self.template_name]

    def get_queryset(self):
        qs = Post.objects.filter(published_at__lte=timezone.now())
        
        # Filtet by Category
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category=category)
            
        # Filter by Author
        author = self.request.GET.get('author')
        if author:
            qs = qs.filter(models.Q(author__username=author) | models.Q(author_pseudonym=author))
            
        # Filter by Tag
        tag = self.request.GET.get('tag')
        if tag:
            qs = qs.filter(tags__slug=tag)
            
        # Filter by Month/Year
        month = self.request.GET.get('month')
        year = self.request.GET.get('year')
        if month and year:
            qs = qs.filter(published_at__month=month, published_at__year=year)
            
        return qs.distinct()
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.choices
        context['current_category'] = self.request.GET.get('category', '')
        context['current_author'] = self.request.GET.get('author', '')
        context['current_tag'] = self.request.GET.get('tag', '')
        return context

class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'

    def get_template_names(self):
        if getattr(self.request, 'LANGUAGE_CODE', 'vi') == 'en':
            return [self.template_name.replace('.html', '_en.html')]
        return [self.template_name]
    
    def get_queryset(self):
        # We allow staff to view unpublished posts, otherwise only published
        if self.request.user.is_staff:
            return Post.objects.all()
        return Post.objects.filter(published_at__lte=timezone.now())
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        
        # Increment total views (raw clicks)
        Post.objects.filter(id=post.id).update(total_views=models.F('total_views') + 1)
        
        # Related posts based on category
        context['related_posts'] = Post.objects.filter(
            category=post.category, 
            published_at__lte=timezone.now()
        ).exclude(id=post.id)[:3]
        return context


# ======================== MANAGEMENT VIEWS ========================

def is_manager(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

import json
import statistics
from django.db.models import Avg

@login_required
@user_passes_test(is_manager)
def manage_post_list(request):
    query = request.GET.get('q', '')
    posts = Post.objects.all()
    if query:
        posts = posts.filter(title__icontains=query)
    
    context = {
        'posts': posts,
        'query': query,
    }
    return render(request, get_template_name(request, 'blog/manage/post_list.html'), context)

from management.utils import export_to_excel

@login_required
@user_passes_test(is_manager)
def manage_blog_analytics(request):
    query = request.GET.get('q', '')
    posts = Post.objects.all()
    if query:
        posts = posts.filter(title__icontains=query)
    
    # Calculate analytic metrics for each post
    for post in posts:
        sessions = post.reading_sessions.filter(duration__lte=1200) # Filter outliers > 20 mins
        if sessions.exists():
            durations = list(sessions.values_list('duration', flat=True))
            depths = list(sessions.values_list('scroll_depth', flat=True))
            
            post.median_duration = statistics.median(durations)
            post.avg_scroll_depth = sum(depths) / len(depths) * 100
            post.engaged_readers = sessions.count()
        else:
            post.median_duration = 0
            post.avg_scroll_depth = 0
            post.engaged_readers = 0

    if request.GET.get('export') == 'excel':
        export_data = []
        for p in posts:
            export_data.append({
                'Tiêu đề': p.title,
                'Danh mục': p.get_category_display(),
                'Tổng lượt xem (Clicks)': p.total_views,
                'Lượt đọc chuyên sâu': p.engaged_readers,
                'Thời gian đọc trung vị (giây)': f"{p.median_duration:.1f}",
                'Độ sâu cuộn trung bình (%)': f"{p.avg_scroll_depth:.1f}%",
                'Ngày xuất bản': p.published_at.strftime('%Y-%m-%d') if p.published_at else 'Chưa đăng'
            })
        return export_to_excel(export_data, f"Mia_Blog_Analytics_{timezone.now().strftime('%Y%m%d')}")

    context = {
        'posts': posts,
        'query': query,
    }
    return render(request, get_template_name(request, 'blog/manage/analytics.html'), context)

@csrf_exempt
def track_reading(request):
    # Support both GET and POST for maximum compatibility
    if request.method in ["POST", "GET"]:
        try:
            if request.method == "POST":
                data = json.loads(request.body)
            else:
                data = request.GET

            post_id = data.get('post_id')
            duration = int(data.get('duration', 0))
            scroll_depth = float(data.get('scroll_depth', 0))
            session_id = data.get('session_id', 'unknown')

            if post_id:
                post = get_object_or_404(Post, id=post_id)
                # If it's a new session or duration is low, also increment raw views
                if duration < 10: 
                    # Only increment once per session roughly
                    pass 

                ReadingSession.objects.update_or_create(
                    session_id=session_id,
                    post=post,
                    defaults={
                        'duration': duration,
                        'scroll_depth': min(1.0, scroll_depth)
                    }
                )
                return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid'}, status=405)

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (self.request.user.is_staff or self.request.user.is_superuser)

class ManagePostCreateView(ManagerRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/manage/post_form.html'
    success_url = reverse_lazy('blog:manage_post_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_tags'] = Tag.objects.all()
        return context

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class ManagePostUpdateView(ManagerRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/manage/post_form.html'
    success_url = reverse_lazy('blog:manage_post_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_tags'] = Tag.objects.all()
        return context


class ManagePostDeleteView(ManagerRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/manage/post_confirm_delete.html'
    success_url = reverse_lazy('blog:manage_post_list')


# ======================== API VIEWS ========================

@csrf_exempt
@login_required
@user_passes_test(is_manager)
def upload_image(request):
    if request.method == "POST":
        file_obj = request.FILES.get('file')
        if not file_obj:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
            
        file_name = default_storage.save(f"blog/uploads/{file_obj.name}", ContentFile(file_obj.read()))
        file_url = f"{settings.MEDIA_URL}{file_name}"
        
        return JsonResponse({'location': file_url})
    return JsonResponse({'error': 'Invalid request'}, status=400)
