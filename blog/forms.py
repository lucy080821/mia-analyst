from django import forms
from django.utils.text import slugify
from django.utils import timezone
from .models import Post, Tag

class PostForm(forms.ModelForm):
    PUBLISH_CHOICES = (
        ('now', 'Đăng ngay'),
        ('schedule', 'Hẹn giờ'),
    )
    
    publish_status = forms.ChoiceField(
        choices=PUBLISH_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'publish-status-radio'}),
        initial='now',
        label='Trạng thái đăng'
    )

    published_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local', 
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50',
            'step': '1',
        }, format='%Y-%m-%dT%H:%M:%S')
    )
    
    tags_str = forms.CharField(
        label='Tags (phân cách bằng dấu phẩy)',
        required=False,
        help_text='Ví dụ: AI, Logistics, Tài chính',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50',
            'placeholder': 'Nhập các thẻ, cách nhau bằng dấu phẩy...',
            'list': 'existing-tags-list'
        })
    )

    class Meta:
        model = Post
        fields = [
            'title', 'slug', 'category', 'author_pseudonym', 
            'cover_image', 'summary', 'content', 'published_at',
            'meta_title', 'meta_description', 'meta_keywords'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
            'slug': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50', 'placeholder': 'Để trống sẽ tự tạo từ tiêu đề'}),
            'category': forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
            'author_pseudonym': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
            'cover_image': forms.FileInput(attrs={'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'}),
            'summary': forms.Textarea(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50', 'rows': 3}),
            'content': forms.Textarea(attrs={'id': 'post-editor', 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50', 'rows': 15}),
            'meta_title': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
            'meta_description': forms.Textarea(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50', 'rows': 3}),
            'meta_keywords': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['tags_str'].initial = ", ".join(t.name for t in self.instance.tags.all())
            
            # If pub date is in the future, select 'schedule'
            if self.instance.published_at and self.instance.published_at > timezone.now():
                self.fields['publish_status'].initial = 'schedule'
            else:
                self.fields['publish_status'].initial = 'now'

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle publish status
        publish_status = self.cleaned_data.get('publish_status')
        if publish_status == 'now':
            instance.published_at = timezone.now()
        # else: already handled by the field input if schedule was selected
        
        if commit:
            instance.save()
        
        # Process tags
        if instance.pk:
            tags_data = self.cleaned_data.get('tags_str', '')
            tag_names = [t.strip() for t in tags_data.split(',') if t.strip()]
            tag_objs = []
            for name in tag_names:
                slug = slugify(name)
                # Handle cases where slugify might return empty (e.g. only non-alphanumeric chars)
                if not slug:
                    slug = f"tag-{abs(hash(name)) % 10000}"
                tag, _ = Tag.objects.get_or_create(name=name, defaults={'slug': slug})
                tag_objs.append(tag)
            instance.tags.set(tag_objs)
            
        return instance
