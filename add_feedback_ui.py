def add_feedback_ui(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # The HTML to insert
    feedback_html = """
    <!-- Feedback Floating Button -->
    <button id="feedbackBtn" class="fixed bottom-6 right-6 z-50 bg-gradient-to-r from-indigo-500 to-purple-600 text-white p-3 rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition-all duration-300 flex items-center justify-center group" title="Gửi góp ý">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"></path></svg>
    </button>

    <!-- Feedback Modal -->
    <div id="feedbackModal" class="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/40 backdrop-blur-sm opacity-0 pointer-events-none transition-opacity duration-300">
        <div class="bg-white/90 backdrop-blur-md rounded-2xl shadow-2xl w-full max-w-md p-6 transform scale-95 transition-transform duration-300 border border-white/50" id="feedbackModalContent">
            <div class="flex justify-between items-center mb-5">
                <h3 class="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600">Gửi Phản Hồi</h3>
                <button id="closeFeedbackBtn" class="text-slate-400 hover:text-rose-500 transition-colors">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <form id="feedbackForm" class="space-y-4">
                <div>
                    <label class="block text-sm font-semibold text-slate-700 mb-1">Tên của bạn</label>
                    <input type="text" id="fbName" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-sm bg-white/50" placeholder="Nhập tên (không bắt buộc)">
                </div>
                <div>
                    <label class="block text-sm font-semibold text-slate-700 mb-1">Gói dịch vụ đang quan tâm</label>
                    <select id="fbPackage" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-sm bg-white/50 appearance-none">
                        <option value="Chưa xác định">-- Chọn gói --</option>
                        <option value="Free">Gói Miễn Phí (Free)</option>
                        <option value="Pro">Gói Chuyên Nghiệp (Pro)</option>
                        <option value="Enterprise">Gói Doanh Nghiệp</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-semibold text-slate-700 mb-1">Nội dung góp ý <span class="text-rose-500">*</span></label>
                    <textarea id="fbContent" rows="4" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-sm bg-white/50 resize-none" placeholder="Mọi ý kiến của bạn đều giúp hệ thống tuyệt vời hơn..." required></textarea>
                </div>
                <div class="pt-2">
                    <button type="submit" id="fbSubmitBtn" class="w-full py-3 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white rounded-xl font-bold shadow-md shadow-indigo-200 transition-all flex justify-center items-center">
                        <span id="fbSubmitText">Gửi đi ngay</span>
                        <svg id="fbSubmitSpinner" class="w-5 h-5 ml-2 animate-spin hidden" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                    </button>
                </div>
            </form>
        </div>
    </div>

    <!-- Toast Notification (SweetAlert-style minimal) -->
    <div id="toastNotification" class="fixed top-6 right-6 z-[200] transform transition-all duration-300 translate-x-full opacity-0">
        <div class="bg-white border-l-4 border-green-500 shadow-xl rounded-lg p-4 flex items-start max-w-sm">
            <div class="flex-shrink-0">
                <svg class="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            </div>
            <div class="ml-3">
                <h3 class="text-sm font-bold text-slate-800">Thành công!</h3>
                <p class="text-xs text-slate-600 mt-1" id="toastMessage">Cảm ơn bạn đã gửi phản hồi.</p>
            </div>
        </div>
    </div>

    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const modal = document.getElementById('feedbackModal');
        const content = document.getElementById('feedbackModalContent');
        const openBtn = document.getElementById('feedbackBtn');
        const closeBtn = document.getElementById('closeFeedbackBtn');
        const form = document.getElementById('feedbackForm');
        
        function openModal() {
            modal.classList.remove('opacity-0', 'pointer-events-none');
            content.classList.remove('scale-95');
        }
        
        function closeModal() {
            modal.classList.add('opacity-0', 'pointer-events-none');
            content.classList.add('scale-95');
        }
        
        function showToast(msg) {
            const toast = document.getElementById('toastNotification');
            document.getElementById('toastMessage').innerText = msg;
            toast.classList.remove('translate-x-full', 'opacity-0');
            setTimeout(() => {
                toast.classList.add('translate-x-full', 'opacity-0');
            }, 4000);
        }

        openBtn.addEventListener('click', openModal);
        closeBtn.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if(e.target === modal) closeModal();
        });

        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const submitBtn = document.getElementById('fbSubmitBtn');
            const spinner = document.getElementById('fbSubmitSpinner');
            const text = document.getElementById('fbSubmitText');
            
            // UI Loading
            submitBtn.disabled = true;
            spinner.classList.remove('hidden');
            text.innerText = 'Đang gửi...';

            const payload = {
                customer_name: document.getElementById('fbName').value,
                service_package: document.getElementById('fbPackage').value,
                content: document.getElementById('fbContent').value
            };

            try {
                const res = await fetch('/analytics/api/submit-feedback/', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if(data.success) {
                    closeModal();
                    form.reset();
                    showToast(data.message || 'Cảm ơn bạn đã đóng góp ý kiến!');
                } else {
                    alert('Lỗi: ' + data.error);
                }
            } catch (err) {
                alert('Đã xảy ra lỗi kết nối. Vui lòng thử lại sau.');
            } finally {
                submitBtn.disabled = false;
                spinner.classList.add('hidden');
                text.innerText = 'Gửi đi ngay';
            }
        });
    });
    </script>
"""
    if 'id="feedbackBtn"' not in content:
        content = content.replace('{% endblock %}', feedback_html + '\n{% endblock %}')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

add_feedback_ui(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard.html')
add_feedback_ui(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard_en.html')
print("Injected Feedback UI")
