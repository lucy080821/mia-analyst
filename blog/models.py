from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.text import slugify

class Category(models.TextChoices):
    SOLUTIONS = 'solutions', 'Giải pháp'
    KNOWLEDGE = 'knowledge', 'Kiến thức'
    TECHNOLOGY = 'technology', 'Công nghệ'
    CASE_STUDY = 'case_study', 'Case Study'

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

class Post(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    category = models.CharField(max_length=50, choices=Category.choices, default=Category.KNOWLEDGE)
    
    # Author details
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    author_pseudonym = models.CharField(max_length=100, blank=True, help_text="Bút danh (sẽ lưu lại cho lần sau)")
    
    # Meta / SEO
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    
    # Content
    cover_image = models.ImageField(upload_to='blog/covers/', blank=True, null=True)
    summary = models.TextField(help_text="Phần tóm tắt hiển thị dưới tiêu đề như trong hình (hỗ trợ HTML).")
    content = models.TextField(help_text="Nội dung chính (nhúng HTML).")
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    
    # Stats
    total_views = models.PositiveIntegerField(default=0)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, help_text="Hẹn giờ đăng bài theo ngày/giờ. Để trống để đăng ngay.")
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
        
        # Save last known pseudonym to user profile if needed, or we just fetch last post
    
    def is_published(self):
        return self.published_at <= timezone.now()

    @property
    def reading_time(self):
        # Strip simple HTML tags to get plain text
        import re
        clean_text = re.sub('<[^<]+?>', '', self.content)
        words = len(clean_text.split())
        # Assuming average reading speed of 200 words per minute
        minutes = max(1, round(words / 200))
        return minutes

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-published_at']

class ReadingSession(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reading_sessions')
    session_id = models.CharField(max_length=100)
    duration = models.PositiveIntegerField(help_text="Thời gian tính bằng giây")
    scroll_depth = models.FloatField(help_text="Tỷ lệ cuộn từ 0 đến 1")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Phiên đọc"
        verbose_name_plural = "Các phiên đọc"
