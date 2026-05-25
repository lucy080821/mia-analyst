def update_frontend(filepath, is_en=False):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add Trash button to sidebar header
    if is_en:
        old_header = '''<div class="gemini-section-header sidebar-hide">
                    <span>RECENT HISTORY</span>
                </div>'''
        new_header = '''<div class="gemini-section-header sidebar-hide flex justify-between items-center pr-4">
                    <span>RECENT HISTORY</span>
                    <button onclick="clearChatHistory()" class="text-slate-400 hover:text-rose-500 transition-colors" title="Clear History">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                    </button>
                </div>'''
    else:
        old_header = '''<div class="gemini-section-header sidebar-hide">
                    <span>Lịch sử gần đây</span>
                </div>'''
        new_header = '''<div class="gemini-section-header sidebar-hide flex justify-between items-center pr-4">
                    <span>Lịch sử gần đây</span>
                    <button onclick="clearChatHistory()" class="text-slate-400 hover:text-rose-500 transition-colors" title="Xóa toàn bộ lịch sử">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                    </button>
                </div>'''
    
    content = content.replace(old_header, new_header)

    # 2. Add clearChatHistory JS function
    js_code_vi = '''
    window.clearChatHistory = async function() {
        if(!confirm("Bạn có chắc chắn muốn xóa toàn bộ lịch sử trò chuyện?")) return;
        
        // Clear LocalStorage
        localStorage.removeItem(STORAGE_KEY);
        
        // Clear Server
        try {
            const res = await fetch('/analytics/api/chat-history/clear/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            });
            const data = await res.json();
            if(data.success) {
                const list = document.getElementById('chat-history-list');
                if(list) list.innerHTML = '<p class="text-[10px] text-slate-500 italic px-4 py-2 sidebar-hide">Chưa có lịch sử.</p>';
                // Show notification if window.showToast exists or fallback
                if(typeof showToast === 'function') {
                    showToast(data.message);
                } else {
                    alert(data.message);
                }
            } else {
                alert("Lỗi: " + data.error);
            }
        } catch(e) {
            console.error(e);
            alert("Đã xảy ra lỗi khi xóa lịch sử.");
        }
    };
    '''

    js_code_en = '''
    window.clearChatHistory = async function() {
        if(!confirm("Are you sure you want to clear your entire chat history?")) return;
        
        // Clear LocalStorage
        localStorage.removeItem(STORAGE_KEY);
        
        // Clear Server
        try {
            const res = await fetch('/analytics/api/chat-history/clear/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            });
            const data = await res.json();
            if(data.success) {
                const list = document.getElementById('chat-history-list');
                if(list) list.innerHTML = '<p class="text-[10px] text-slate-500 italic px-4 py-2 sidebar-hide">No history.</p>';
                
                if(typeof showToast === 'function') {
                    showToast("Chat history cleared.");
                } else {
                    alert("Chat history cleared.");
                }
            } else {
                alert("Error: " + data.error);
            }
        } catch(e) {
            console.error(e);
            alert("An error occurred while clearing history.");
        }
    };
    '''

    js_code = js_code_en if is_en else js_code_vi

    # append before the closing </script> right before </body>
    if 'window.clearChatHistory =' not in content:
        content = content.replace('</script>\n{% endblock %}', js_code + '\n</script>\n{% endblock %}')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

update_frontend(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard.html', False)
update_frontend(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard_en.html', True)
print("Frontend updated for clear history.")
