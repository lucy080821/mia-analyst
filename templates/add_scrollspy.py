import re

def add_scrollspy(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # If already added, don't add again
    if '<!-- ScrollSpy Script -->' in content:
        print(f"ScrollSpy already in {filepath}")
        return

    script_html = """
    <!-- ScrollSpy Script -->
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const sections = document.querySelectorAll('section[id]');
            const navLinks = document.querySelectorAll('a[href^="#"]');
            
            function onScroll() {
                let current = '';
                sections.forEach(section => {
                    const sectionTop = section.offsetTop;
                    if (window.scrollY >= sectionTop - 200) {
                        current = section.getAttribute('id');
                    }
                });

                navLinks.forEach(link => {
                    const href = link.getAttribute('href');
                    if (!href || href === '#') return;
                    
                    if (current && href === '#' + current) {
                        link.classList.add('text-primary');
                        // Also make it a bit bolder or add a visual indicator if you like
                        // link.classList.add('font-bold'); 
                    } else {
                        link.classList.remove('text-primary');
                    }
                });
            }
            
            window.addEventListener('scroll', onScroll);
            onScroll(); // Trigger once on load
        });
    </script>
</body>"""

    content = content.replace('</body>', script_html)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Successfully updated {filepath}")

add_scrollspy('landing.html')
add_scrollspy('landing_en.html')
