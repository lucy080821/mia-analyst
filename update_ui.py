def tweak_frontend(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add required and change placeholder
    old_name = '''<input type="text" id="fbName" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-sm bg-white/50" placeholder="Nhập tên (không bắt buộc)">'''
    new_name = '''<input type="text" id="fbName" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-sm bg-white/50" placeholder="Nhập tên của bạn" required>'''
    
    # Hide the select container by adding 'hidden' class to the div
    old_div = '''<div>
                    <label class="block text-sm font-semibold text-slate-700 mb-1">Gói dịch vụ đang quan tâm</label>
                    <select id="fbPackage" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-sm bg-white/50 appearance-none">
                        <option value="Chưa xác định">-- Chọn gói --</option>
                        <option value="Free">Gói Miễn Phí (Free)</option>
                        <option value="Pro">Gói Chuyên Nghiệp (Pro)</option>
                        <option value="Enterprise">Gói Doanh Nghiệp</option>
                    </select>
                </div>'''
    new_div = '''<div class="hidden">
                    <label class="block text-sm font-semibold text-slate-700 mb-1">Gói dịch vụ đang quan tâm</label>
                    <select id="fbPackage" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-sm bg-white/50 appearance-none">
                        <option value="Chưa xác định">-- Chọn gói --</option>
                    </select>
                </div>'''

    old_label = '''<label class="block text-sm font-semibold text-slate-700 mb-1">Tên của bạn</label>'''
    new_label = '''<label class="block text-sm font-semibold text-slate-700 mb-1">Tên của bạn <span class="text-rose-500">*</span></label>'''

    content = content.replace(old_name, new_name)
    content = content.replace(old_div, new_div)
    content = content.replace(old_label, new_label)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

tweak_frontend(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard.html')
tweak_frontend(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard_en.html')
print("Frontend updated.")
