
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    let chartCounter = 0;

    // Storage Utils
    const STORAGE_KEY = 'ai_data_assistant_history_v1';
    function saveChatHistory(msgs) { localStorage.setItem(STORAGE_KEY, JSON.stringify(msgs)); }
    function loadChatHistory() { try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; } catch (e) { return []; } }

    let conversationMemory = loadChatHistory();

    // ===== UPLOAD LOGIC =====
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('excel-upload');
    const uploadStatus = document.getElementById('upload-status');
    const tableList = document.getElementById('table-list');


    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('border-primary', 'bg-slate-800');
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('border-primary', 'bg-slate-800');
    });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-primary', 'bg-slate-800');
        if (e.dataTransfer.files.length) handleFileUpload(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) handleFileUpload(e.target.files[0]);
    });

    async function handleFileUpload(file, sheet_name = 0) {
        if (!file.name.match(/\.(xlsx|xls|csv)$/i)) {
            uploadStatus.innerHTML = '<span class="text-red-400">Sai định dạng</span>';
            showModal('Vui lòng chọn file .xlsx, .xls hoặc .csv.');
            return;
        }

        uploadStatus.innerHTML = '<span class="text-primary animate-pulse">Đang xử lý...</span>';
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('sheet_name', sheet_name);

        try {
            const response = await fetch('/*{% url "upload_excel" %}*/', {
                method: 'POST',
                headers: { 'X-CSRFToken': '/*{{ csrf_token }}*/' },
                body: formData
            });
            const data = await response.json();
            
            if (response.ok) {
                uploadStatus.innerHTML = '<span class="text-green-500">Hoàn tất!</span>';
                showModal('Upload thành công. Dữ liệu đã sẵn sàng.');

                // Update Quick Stats
                document.getElementById('stat-rows').textContent = data.rows.toLocaleString();
                document.getElementById('stat-cols').textContent = data.columns.length;
                document.getElementById('stat-sheets').textContent = data.sheet_count || 1;

                // Handle Sheets Display & Selection
                const sheetNamesList = document.getElementById('sheet-names-list');
                const sheetSelectorContainer = document.getElementById('sheet-selector-container');
                const sheetSelector = document.getElementById('sheet-selector');
                
                if (data.sheet_names && data.sheet_names.length > 0) {
                    sheetNamesList.textContent = 'Sheets: ' + data.sheet_names.join(', ');
                    
                    const userTier = "/*{{ request.user.userprofile.tier|default:'FREE' }}*/";
                    if ((userTier === 'PLUS' || userTier === 'PREMIUM') && data.sheet_names.length > 1) {
                        sheetSelectorContainer.classList.remove('hidden');
                        sheetSelector.innerHTML = data.sheet_names.map((name, idx) => 
                            `<option value="${idx}" ${idx == data.current_sheet ? 'selected' : ''}>${name}</option>`
                        ).join('');
                        
                        sheetSelector.onchange = () => {
                            handleFileUpload(file, sheetSelector.value).then(() => {
                                showModal(`Đã chuyển sang sheet: ${data.sheet_names[sheetSelector.value]}`);
                            });
                        };
                    } else {
                        sheetSelectorContainer.classList.add('hidden');
                    }
                } else {
                    sheetNamesList.textContent = '';
                    sheetSelectorContainer.classList.add('hidden');
                }

                // Remove existing radio for same file if re-uploading sheet
                const safeFileName = file.name.replace(/"/g, '\\"');
                const existingRadio = document.querySelector(`input[name="datasource"][data-filename="${safeFileName}"]`);
                if (existingRadio) {
                    existingRadio.closest('label').remove();
                }

                const newHtml = `
                    <label class="flex items-center p-3 bg-white border border-green-500 rounded-xl cursor-pointer hover:border-green-600 transition-all shadow-sm">
                        <input type="radio" name="datasource" value="${data.table}" data-filename="${file.name.replace(/"/g, '&quot;')}" class="w-4 h-4 text-green-500 border-slate-300 focus:ring-green-500" checked>
                        <div class="ml-3 overflow-hidden">
                            <span class="block text-[11px] font-bold text-slate-900 truncate">${file.name}</span>
                            <span class="block text-[9px] text-green-500 mt-1">${data.rows} dòng | Excel</span>
                        </div>
                    </label>
                `;
                tableList.insertAdjacentHTML('beforeend', newHtml);
                runDatasetAnalysis(data.table, file.name);
            } else {
                uploadStatus.innerHTML = `<span class="text-red-400">Thất bại</span>`;
                showModal(`Lỗi: ${data.error || 'Server error'}`);
            }
        } catch (error) {
            uploadStatus.innerHTML = '<span class="text-red-400">Lỗi kết nối</span>';
        }
    }

    async function runDatasetAnalysis(table_name, file_name) {
        const loadingId = appendBotLoading();
        try {
            const response = await fetch('/*{% url "analyze_dataset" %}*/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '/*{{ csrf_token }}*/' },
                body: JSON.stringify({ table_name: table_name })
            });
            const data = await response.json();
            removeElement(loadingId);
            
            if (!response.ok) {
                console.error("Analysis failed:", data.error);
                return;
            }
            
            let chipsHtml = data.suggested_questions.map(q => 
                `<button type="button" onclick="document.getElementById('chat-input').value='${q}'; document.getElementById('chat-form').dispatchEvent(new Event('submit', {cancelable: true, bubbles: true}));" class="inline-block bg-white text-primary border border-primary/20 hover:bg-primary hover:text-white mt-2 mr-2 mb-1 px-3 py-1.5 rounded-full text-[11px] font-bold shadow-sm transition-all focus:ring-2 focus:ring-primary/50 text-left leading-tight break-words max-w-full"><span class="mr-1 opacity-70">✨</span>${q}</button>`
            ).join('');

            let cleanBtnHtml = "";
            if (data.needs_cleaning) {
                cleanBtnHtml = `
                <div class="mt-4 p-3 bg-red-50/80 border border-red-100 rounded-xl" id="clean-box-${table_name}">
                    <p class="text-xs font-bold text-red-500 mb-2 flex items-center"><svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg> Phát hiện dữ liệu lỗi/rỗng</p>
                    <p class="text-[11px] text-red-500/80 mb-3">${data.summary}</p>
                    <button type="button" onclick="cleanDataset('${table_name}')" class="w-full py-2 bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-600 hover:to-rose-600 text-white rounded-lg text-xs font-bold transition shadow-md shadow-red-500/20">👉 Làm sạch dữ liệu tự động</button>
                    <p class="text-[9px] text-red-400 mt-2 text-center">AI sẽ tự điền 0 vào dữ liệu số rỗng và xóa dòng toàn rỗng.</p>
                </div>
                `;
            } else {
                chipsHtml = `<p class="text-[11px] text-slate-500 mb-2 italic flex items-center"><svg class="w-3 h-3 text-green-500 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg> Dữ liệu hoàn toàn sạch sẽ, bạn có thể phân tích ngay!</p>` + chipsHtml;
            }

            const messageHtml = `
                <div data-role="assistant" class="flex items-start max-w-[95%] animate-report">
                    <div class="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-lg transform hover:rotate-12 transition-transform">
                        <span class="text-sm">🤖</span>
                    </div>
                    <div class="ml-3 flex-grow">
                        <div class="bubble-bot p-4 rounded-[20px] rounded-tl-none shadow-sm border border-indigo-100 bg-gradient-to-b from-white to-blue-50/30 overflow-hidden text-slate-700 text-sm">
                            <div class="flex items-center justify-between mb-2">
                                <p class="font-black text-indigo-900 text-xs uppercase tracking-widest flex items-center"><span class="w-2 h-2 rounded-full bg-green-500 animate-pulse mr-2"></span> DATA SCANNER</p>
                                <span class="text-[9px] font-bold text-slate-400 bg-white px-2 py-0.5 rounded-full border border-slate-100">${file_name}</span>
                            </div>
                            <!-- Separator line -->
                            <div class="h-px w-full bg-gradient-to-r from-indigo-100 to-transparent mb-3"></div>
                            
                            ${cleanBtnHtml}
                            <div class="mt-4">
                                <p class="text-xs font-bold text-slate-800 mb-2 flex items-center"><svg class="w-3.5 h-3.5 text-amber-500 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg> Gợi ý phân tích cho bạn:</p>
                                <div class="flex flex-wrap">${chipsHtml}</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            chatMessages.insertAdjacentHTML('beforeend', messageHtml);
            scrollToBottom();
            
        } catch (e) {
            console.error("Failed to analyze dataset", e);
        }
    }

    async function cleanDataset(table_name) {
        const loadingId = appendBotLoading();
        try {
            const response = await fetch('/*{% url "clean_dataset" %}*/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '/*{{ csrf_token }}*/' },
                body: JSON.stringify({ table_name: table_name })
            });
            const data = await response.json();
            removeElement(loadingId);
            
            if (response.ok) {
                const box = document.getElementById(`clean-box-${table_name}`);
                if (box) {
                    box.outerHTML = `<div class="mt-4 p-3 bg-green-50/80 border border-green-100 rounded-xl">
                        <p class="text-xs font-bold text-green-600 flex items-center"><svg class="w-4 h-4 mr-1 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg> Đã làm sạch dữ liệu thành công!</p>
                        <p class="text-[10px] text-green-600/70 mt-1">Dữ liệu của bạn hiện tại rất đẹp và sẵn sàng để phân tích.</p>
                    </div>`;
                }
            } else {
                showModal('Lỗi dọn dẹp: ' + (data.error || 'Server error'));
            }
        } catch (e) {
            removeElement(loadingId);
            showModal('Lỗi kết nối khi dọn dẹp');
        }
    }

    // ===== CHAT UI LOGIC =====
    function appendUserMessage(text) {
        const html = `
            <div data-role="user" class="flex items-start justify-end w-full animate-msg">
                <div class="mr-3 bubble-user text-white p-3 rounded-xl rounded-tr-none max-w-[80%] break-words shadow-sm">
                    <p class="text-xs m-0">${text}</p>
                </div>
                <div class="w-8 h-8 bg-slate-200 rounded-lg flex items-center justify-center text-slate-500 font-black text-[10px]">
                    /*{{ user.username|first|upper }}*/
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', html);
        scrollToBottom();
    }

    function appendBotLoading() {
        const id = 'loading-' + Date.now();
        const html = `
            <div id="${id}" class="flex items-start max-w-[85%] animate-msg">
                <div class="flex-shrink-0 w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center">
                    <svg class="w-4 h-4 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                </div>
                <div class="ml-3 bubble-bot p-3 rounded-xl rounded-tl-none shadow-sm">
                    <div class="flex space-x-1.5 items-center">
                        <div class="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce"></div>
                        <div class="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0.15s"></div>
                        <div class="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0.3s"></div>
                    </div>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', html);
        scrollToBottom();
        return id;
    }

    function removeElement(id) {
        document.getElementById(id)?.remove();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }



    function renderChatHistory() {
        const history = loadChatHistory();
        if (!history.length) return showModal('Lịch sử trống.');
        history.forEach(item => {
            if (item.role === 'user') appendUserMessage(item.content);
            else appendBotMessage({reply: item.content});
        });
    }

    function formatReportText(text) {
        if (!text) return "";
        let lines = text.split('\\n');
        let htmlLines = [];
        let inList = false;
        
        for (let i = 0; i < lines.length; i++) {
            let line = lines[i].trim();
            if (!line) {
                if (inList) { htmlLines.push('</ul>'); inList = false; }
                htmlLines.push('<div class="h-2"></div>');
                continue;
            }
            
            // Check headers
            if (line.startsWith('# ')) {
                if (inList) { htmlLines.push('</ul>'); inList = false; }
                let content = line.substring(2).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                htmlLines.push(`<h2 class="text-[14px] font-black text-primary mt-5 mb-2 uppercase tracking-wide border-b border-slate-100 pb-1">${content}</h2>`);
                continue;
            } else if (line.startsWith('## ')) {
                if (inList) { htmlLines.push('</ul>'); inList = false; }
                let content = line.substring(3).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                htmlLines.push(`<h3 class="text-[13px] font-bold text-slate-800 mt-4 mb-2">${content}</h3>`);
                continue;
            } else if (line.startsWith('### ')) {
                if (inList) { htmlLines.push('</ul>'); inList = false; }
                let content = line.substring(4).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                htmlLines.push(`<h4 class="text-[12px] font-bold text-slate-700 mt-3 mb-1.5">${content}</h4>`);
                continue;
            }
            
            let isBullet = false;
            let bulletType = 'disc';
            let content = line;
            
            if (line.match(/^[\-\*]\s+/)) {
                content = line.replace(/^[\-\*]\s+/, '');
                isBullet = true;
            } else if (line.match(/^\d+\.\s+/)) {
                content = line.replace(/^\d+\.\s+/, '');
                isBullet = true;
                bulletType = 'decimal';
            }
            
            // Apply inline formatting
            content = content.replace(/\*\*(.*?)\*\*/g, '<strong class="text-slate-900 font-bold">$1</strong>')
                             .replace(/(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)/g, '<em class="text-slate-700 italic">$1</em>');
            
            if (isBullet) {
                if (!inList) { htmlLines.push(`<ul class="space-y-1.5 my-2 pl-5">`); inList = true; }
                htmlLines.push(`<li class="list-${bulletType} text-[12px] text-slate-600 leading-relaxed">${content}</li>`);
            } else {
                if (inList) { htmlLines.push('</ul>'); inList = false; }
                htmlLines.push(`<p class="text-[12px] text-slate-600 leading-relaxed mb-2">${content}</p>`);
            }
        }
        if (inList) htmlLines.push('</ul>');
        
        return htmlLines.join('');
    }

    function appendBotMessage(data, isError=false) {
        // Method badge
        const methodBadges = {
            'sql': {label: 'SQL', color: 'bg-blue-100 text-blue-700', icon: '🗃️'},
            'python': {label: 'Python', color: 'bg-green-100 text-green-700', icon: '🐍'},
            'ml_cluster': {label: 'ML Clustering', color: 'bg-purple-100 text-purple-700', icon: '🔬'},
            'ml_forecast': {label: 'ML Forecast', color: 'bg-orange-100 text-orange-700', icon: '📈'},
            'ml_anomaly': {label: 'ML Anomaly', color: 'bg-red-100 text-red-700', icon: '🔍'},
        };
        const method = data.method || 'sql';
        const badge = methodBadges[method] || methodBadges['sql'];
        
        let badgeHtml = '';
        if (data.method && !isError) {
            badgeHtml = `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[8px] font-black ${badge.color} mr-2">${badge.icon} ${badge.label}</span>`;
        }

        let contentHtml = `<div class="report-content ${isError ? 'border-red-200 bg-red-50/30' : ''}">` +
            `<div class="report-title flex items-center flex-wrap"><svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg> Insight Report ${badgeHtml}</div>` +
            `<div class="report-section">${formatReportText(data.reply || data.error || '...') }</div>` +
            `</div>`;
        
        // ML Info card (for ML methods)
        if (data.ml_info && !isError) {
            let mlInfoHtml = '<div class="mt-4 p-3 bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-100 rounded-xl text-[9px] font-medium space-y-1">';
            mlInfoHtml += '<p class="text-[8px] font-black text-purple-600 uppercase tracking-wider mb-1">🧠 Machine Learning Info</p>';
            
            if (data.ml_info.optimal_k) mlInfoHtml += `<p class="text-slate-600">• K tối ưu (Elbow): <strong class="text-slate-900">${data.ml_info.optimal_k}</strong></p>`;
            if (data.ml_info.silhouette_score) mlInfoHtml += `<p class="text-slate-600">• Silhouette Score: <strong class="text-slate-900">${data.ml_info.silhouette_score}</strong></p>`;
            if (data.ml_info.model) mlInfoHtml += `<p class="text-slate-600">• Model: <strong class="text-slate-900">${data.ml_info.model}</strong></p>`;
            if (data.ml_info.r2_score !== undefined) mlInfoHtml += `<p class="text-slate-600">• R² Score: <strong class="text-slate-900">${data.ml_info.r2_score}</strong></p>`;
            if (data.ml_info.trend) mlInfoHtml += `<p class="text-slate-600">• Xu hướng: <strong class="text-slate-900">${data.ml_info.trend} (${data.ml_info.growth_percent}%)</strong></p>`;
            if (data.ml_info.anomaly_count !== undefined) mlInfoHtml += `<p class="text-slate-600">• Bất thường: <strong class="text-red-600">${data.ml_info.anomaly_count}</strong> / ${data.ml_info.total_rows} (${data.ml_info.anomaly_rate}%)</p>`;
            if (data.ml_info.features_used) mlInfoHtml += `<p class="text-slate-600">• Features: <strong class="text-slate-900">${data.ml_info.features_used.join(', ')}</strong></p>`;
            
            mlInfoHtml += '</div>';
            contentHtml += mlInfoHtml;
        }

        if (data.summary && !isError) {
            contentHtml += `<div class="mt-4 p-3 bg-slate-50 border border-slate-100 rounded-xl text-[9px] text-slate-500 font-medium space-y-1">` +
                `<p class="flex items-center"><span class="w-1.5 h-1.5 bg-primary rounded-full mr-2"></span> <strong>Câu hỏi:</strong> ${data.summary.question}</p>` +
                `<p class="flex items-center"><span class="w-1.5 h-1.5 bg-primary rounded-full mr-2"></span> <strong>Dữ liệu:</strong> ${data.summary.row_count} dòng</p>` +
                `</div>`;
        }

        if (data.type === 'table' && data.data?.length) {
            const cols = data.columns;
            let numericCols = cols.slice(1).filter(c => typeof data.data[0][c] === 'number');

            // Render Chart.js
            if (numericCols.length) {
                chartCounter++;
                const chartId = 'chart-' + chartCounter;
                contentHtml += `<div class="w-full h-64 mt-6 bg-white p-3 border border-slate-100 rounded-xl"><canvas id="${chartId}"></canvas></div>`;
                setTimeout(() => {
                    const ctx = document.getElementById(chartId).getContext('2d');
                    new Chart(ctx, {
                        type: data.data.length > 5 ? 'line' : 'bar',
                        data: {
                            labels: data.data.map(r => String(r[cols[0]]).substring(0, 10)),
                            datasets: numericCols.map((c, i) => ({
                                label: c,
                                data: data.data.map(r => r[c]),
                                backgroundColor: ['#6366f1', '#ec4899', '#3b82f6'][i%3] + '20',
                                borderColor: ['#6366f1', '#ec4899', '#3b82f6'][i%3],
                                borderWidth: 2, tension: 0.4, fill: true
                            }))
                        },
                        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 8, font: { size: 9 } } } } }
                    });
                }, 100);
            }

            contentHtml += `<details class="mt-3 group"><summary class="cursor-pointer text-[9px] font-bold text-slate-400 hover:text-primary flex items-center"><svg class="w-2.5 h-2.5 mr-1 group-open:rotate-90" fill="currentColor" viewBox="0 0 20 20"><path d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"></path></svg> DATA (${data.data.length} rows)</summary><div class="mt-2 overflow-x-auto border border-slate-100 rounded-lg bg-white"><table class="min-w-full divide-y divide-slate-100 text-[9px]"><thead class="bg-slate-50"><tr class="text-left text-slate-500">${cols.map(c => `<th class="px-3 py-2 font-bold">${c}</th>`).join('')}</tr></thead><tbody class="divide-y divide-slate-50">${data.data.map(r => `<tr class="hover:bg-slate-50/50">${cols.map(c => `<td class="px-3 py-2 text-slate-600">${r[c]}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details>`;
        }

        if (data.type === 'dashboard' && data.dashboards && data.dashboards.length > 0) {
            let dashboardHtml = '<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">';
            let chartConfigs = [];
            
            data.dashboards.forEach((chartObj, idx) => {
                chartCounter++;
                const chartId = 'chart-' + chartCounter;
                dashboardHtml += `
                    <div class="bg-white p-3 border border-slate-100 rounded-xl shadow-sm hover:shadow-md transition-shadow">
                        <h4 class="text-center font-bold text-slate-700 text-[11px] mb-2 truncate" title="${chartObj.title}">${chartObj.title}</h4>
                        <div class="w-full h-52"><canvas id="${chartId}"></canvas></div>
                    </div>`;
                chartConfigs.push({ id: chartId, obj: chartObj });
            });
            dashboardHtml += '</div>';
            contentHtml += dashboardHtml;
            
            setTimeout(() => {
                chartConfigs.forEach(config => {
                    const ctx = document.getElementById(config.id).getContext('2d');
                    const chartData = config.obj.data;
                    const cols = config.obj.columns;
                    
                    if (chartData && chartData.length > 0 && cols && cols.length >= 2) {
                        const labelCol = cols[0];
                        const valCol = cols[1];
                        const labels = chartData.map(r => String(r[labelCol]).substring(0, 20));
                        const values = chartData.map(r => Number(r[valCol]));
                        
                        let dataset = {
                            label: valCol,
                            data: values,
                            borderWidth: 2
                        };
                        
                        if (config.obj.type === 'pie' || config.obj.type === 'doughnut') {
                            // Single hue palette (Blue/Indigo shades) for better UX as requested
                            const singleHuePalette = [
                                '#1e3a8a', '#274b89', '#315ea8', '#3b82f6', '#60a5fa', 
                                '#93c5fd', '#bfdbfe', '#dbeafe', '#eff6ff', '#e0e7ff'
                            ];
                            // Repeat palette if needed, though usually pie has < 10 slices
                            let bgColors = [];
                            for(let i=0; i<values.length; i++) bgColors.push(singleHuePalette[i % singleHuePalette.length]);
                            
                            dataset.backgroundColor = bgColors;
                            dataset.borderColor = '#ffffff';
                        } else {
                            // Line/Bar charts
                            dataset.backgroundColor = '#6366f120';
                            dataset.borderColor = '#6366f1';
                            dataset.borderRadius = (config.obj.type === 'bar') ? 4 : 0;
                            dataset.tension = 0.4;
                            dataset.fill = true;
                        }

                        new Chart(ctx, {
                            type: config.obj.type || 'bar',
                            data: {
                                labels: labels,
                                datasets: [dataset]
                            },
                            options: { 
                                responsive: true, 
                                maintainAspectRatio: false, 
                                plugins: { 
                                    legend: { position: 'bottom', labels: { boxWidth: 8, font: { size: 9 } } } 
                                } 
                            }
                        });
                    }
                });
            }, 100);
        }

        const html = `
            <div data-role="assistant" class="flex items-start max-w-[95%] animate-report">
                <div class="flex-shrink-0 w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center">
                    <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                </div>
                <div class="ml-3 flex-grow">
                    <div class="bubble-bot p-1 rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                        ${contentHtml}
                    </div>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', html);
        scrollToBottom();
    }

    // ===== TIERED ANALYTICS LOGIC (NEW) =====
    document.getElementById('btn-run-analytics').addEventListener('click', async () => {
        const fileInput = document.getElementById('excel-upload');
        const files = fileInput.files;

        if (files.length === 0) {
            showModal('Vui lòng chọn ít nhất 1 file Excel/CSV trước khi chạy phân tích.');
            return;
        }

        const loadingId = appendBotLoading();
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        try {
            const response = await fetch('/*{% url "process_tiered_data" %}*/', {
                method: 'POST',
                headers: { 'X-CSRFToken': '/*{{ csrf_token }}*/' },
                body: formData
            });
            const data = await response.json();
            removeElement(loadingId);

            if (!response.ok) {
                appendBotMessage({reply: `Lỗi phân tích: ${data.error}`}, true);
                return;
            }

            // Build result UI
            let replyText = `### BÁO CÁO PHÂN TÍCH - ${data.tier}\n\n`;
            replyText += `**Tổng quan:**\n- Doanh thu: **${data.revenue.toLocaleString()} VNĐ**\n- Số đơn hàng: **${data.orders}**\n`;
            
            if (data.roas !== undefined) replyText += `- ROAS: **${data.roas.toFixed(2)}**\n`;
            if (data.cancel_rate !== undefined) replyText += `- Tỉ lệ hủy: **${data.cancel_rate.toFixed(1)}%**\n`;
            if (data.ltv_summary) replyText += `- LTV: **${data.ltv_summary}**\n`;
            if (data.flash_sale_script) replyText += `\n**Flash Sale:**\n${data.flash_sale_script}\n`;

            replyText += `\n**AI Insight:** ${data.ai_insight}`;

            let contentHtml = `<div class="report-content">` +
                `<div class="report-title flex items-center"><svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg> Strategic Analysis (${data.tier})</div>` +
                `<div class="report-section">${formatReportText(replyText)}</div>`;
            
            if (data.chart) {
                contentHtml += `<div class="mt-6"><img src="data:image/png;base64,${data.chart}" class="w-full rounded-xl border border-slate-100 shadow-sm" /></div>`;
            }
            contentHtml += `</div>`;

            const messageHtml = `
                <div data-role="assistant" class="flex items-start max-w-[95%] animate-report">
                    <div class="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-lg">
                        <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    </div>
                    <div class="ml-3 flex-grow">
                        <div class="bubble-bot p-1 rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                            ${contentHtml}
                        </div>
                    </div>
                </div>
            `;
            chatMessages.insertAdjacentHTML('beforeend', messageHtml);
            scrollToBottom();

        } catch (error) {
            removeElement(loadingId);
            appendBotMessage({reply: "Network Error."}, true);
        }
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const msg = chatInput.value.trim();
        if(!msg) return;

        const selectedTableInput = document.querySelector('input[name="datasource"]:checked');
        if (!selectedTableInput || selectedTableInput.value === 'temp_shopee_orders') {
            showModal('Vui lòng tải lên ít nhất 1 file Excel/CSV để AI có dữ liệu phân tích nhé!');
            return;
        }
        const selectedTable = selectedTableInput.value;

        appendUserMessage(msg);
        chatInput.value = '';
        const loadingId = appendBotLoading();

        try {
            const response = await fetch('/*{% url "ai_chat_api" %}*/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg, table: selectedTable, context: conversationMemory })
            });
            const data = await response.json();
            removeElement(loadingId);
            appendBotMessage(data, !response.ok || data.error);
            if(response.ok) conversationMemory.push({role: 'user', content: msg}, {role: 'assistant', content: data.reply});
        } catch (e) {
            removeElement(loadingId);
            appendBotMessage({reply: "Network Error."}, true);
        }
    });

    // ===== EXPORT & CONTEXT MENU LOGIC =====
    const contextMenu = document.getElementById('context-menu');
    let selectedReportContent = '';
    let selectedReportTitle = '';
    let selectedQuery = '';

    document.addEventListener('contextmenu', (e) => {
        const reportTarget = e.target.closest('.report-content');
        if (reportTarget) {
            e.preventDefault();
            selectedReportContent = reportTarget.querySelector('.report-section').innerText;
            selectedReportTitle = reportTarget.querySelector('.report-title').innerText;
            
            const parentMsg = reportTarget.closest('[data-role="assistant"]');
            const queryEl = parentMsg ? Array.from(parentMsg.querySelectorAll('p')).find(p => p.innerText.includes('Query:')) : null;
            selectedQuery = queryEl ? queryEl.innerText.replace('Query:', '').trim() : "";

            contextMenu.style.top = `${e.pageY}px`;
            contextMenu.style.left = `${e.pageX}px`;
            contextMenu.classList.remove('hidden');
        } else {
            contextMenu.classList.add('hidden');
        }
    });

    document.addEventListener('click', () => contextMenu.classList.add('hidden'));

    async function downloadReport(format) {
        if (!selectedReportContent) return;
        const loadingId = appendBotLoading();
        try {
            const response = await fetch('/*{% url "export_report" %}*/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '/*{{ csrf_token }}*/' },
                body: JSON.stringify({ content: selectedReportContent, format, title: selectedReportTitle })
            });
            removeElement(loadingId);
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${selectedReportTitle.replace(/\s+/g, '_')}.${format === 'word' ? 'docx' : 'pdf'}`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            } else {
                const data = await response.json();
                showModal(data.error || 'Lỗi tải xuống.');
            }
        } catch (e) {
            removeElement(loadingId);
            showModal('Lỗi kết nối.');
        }
    }

    // ===== PREMIUM DASHBOARD LOGIC =====
    async function loadDashboards() {
        const container = document.getElementById('dashboard-list');
        if (!container) return;
        try {
            const response = await fetch('/*{% url "dashboard_manager" %}*/');
            const data = await response.json();
            if (response.ok && data.dashboards.length > 0) {
                container.innerHTML = data.dashboards.map(db => `
                    <div class="group flex items-center justify-between p-2 bg-slate-800/30 hover:bg-slate-800 rounded-lg transition-all cursor-pointer">
                        <div class="flex items-center">
                            <svg class="w-3 h-3 text-slate-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"></path></svg>
                            <span class="text-[9px] text-slate-300 font-bold">${db.name}</span>
                        </div>
                        <button onclick="deleteDashboard(${db.id})" class="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 text-slate-600 transition-all">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                        </button>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<p class="text-[9px] text-slate-600 italic ml-2">Chưa có DB.</p>';
            }
        } catch (e) {}
    }

    async function createNewDashboard() {
        const name = prompt("Tên dashboard:");
        if (!name) return;
        try {
            await fetch('/*{% url "dashboard_manager" %}*/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '/*{{ csrf_token }}*/' },
                body: JSON.stringify({ action: 'create', name })
            });
            loadDashboards();
        } catch (e) {}
    }

    async function openSaveToDashboardModal() {
        const response = await fetch('/*{% url "dashboard_manager" %}*/');
        const data = await response.json();
        if (data.dashboards.length === 0) {
            if (confirm("Chưa có dashboard. Tạo mới?")) await createNewDashboard();
            return;
        }
        const div = document.createElement('div');
        div.id = "save-db-modal";
        div.className = "fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[300] flex items-center justify-center p-4";
        div.innerHTML = `<div class="bg-white rounded-[24px] p-6 max-w-sm w-full shadow-2xl">
            <h3 class="text-sm font-black text-slate-900 mb-4 uppercase">Lưu vào Dashboard</h3>
            <div class="space-y-2 mb-4">${data.dashboards.map(db => `<button onclick="saveToThisDashboard(${db.id})" class="w-full p-3 bg-slate-50 hover:bg-primary/5 border border-slate-100 text-left rounded-xl transition-all"><span class="block text-[11px] font-bold text-slate-700">${db.name}</span></button>`).join('')}</div>
            <button onclick="document.getElementById('save-db-modal').remove()" class="w-full text-xs text-slate-400 font-bold py-2">Hủy</button>
        </div>`;
        document.body.appendChild(div);
    }

    async function saveToThisDashboard(dbId) {
        await fetch('/*{% url "dashboard_manager" %}*/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '/*{{ csrf_token }}*/' },
            body: JSON.stringify({ action: 'add_widget', dashboard_id: dbId, title: selectedReportTitle, query: selectedQuery })
        });
        document.getElementById('save-db-modal')?.remove();
        showModal('Đã lưu!');
    }

    async function deleteDashboard(id) {
        if (!confirm("Xóa?")) return;
        await fetch('/*{% url "dashboard_manager" %}*/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '/*{{ csrf_token }}*/' },
            body: JSON.stringify({ action: 'delete_dashboard', dashboard_id: id })
        });
        loadDashboards();
    }

    /*{% if request.user.userprofile.tier == 'PREMIUM' %}*/ loadDashboards(); /*{% endif %}*/

    // Control Buttons
    document.getElementById('new-chat-btn').addEventListener('click', () => { chatMessages.innerHTML = ''; conversationMemory = []; });
    document.getElementById('save-chat-btn').addEventListener('click', () => {
        const msgs = Array.from(document.querySelectorAll('#chat-messages > [data-role]')).map(el => ({
            role: el.dataset.role, content: el.innerText.trim()
        }));
        saveChatHistory(msgs);
        showModal('Đã lưu!');
    });
    document.getElementById('load-chat-btn').addEventListener('click', renderChatHistory);
    document.getElementById('clear-chat-btn').addEventListener('click', () => { localStorage.removeItem(STORAGE_KEY); showModal('Đã xóa!'); });

    function showModal(msg) {
        document.getElementById('modal-message').textContent = msg;
        document.getElementById('modal').classList.remove('hidden');
    }
    document.getElementById('modal-close')?.addEventListener('click', () => {
        document.getElementById('modal').classList.add('hidden');
    });

    // ===== DATA PIPELINE LOGIC =====
    function openDataPipelineModal() {
        document.getElementById('data-pipeline-modal').classList.remove('hidden');
        loadPipelineDatasets();
        loadPipelineRelationships();
    }

    function closeDataPipelineModal() {
        document.getElementById('data-pipeline-modal').classList.add('hidden');
    }

    function switchPipelineTab(tab) {
        if (tab === 'datasets') {
            document.getElementById('content-datasets').classList.remove('hidden');
            document.getElementById('content-relationships').classList.add('hidden');
            document.getElementById('tab-datasets').className = 'px-4 py-2 text-sm font-bold rounded-lg bg-indigo-50 text-indigo-700 transition';
            document.getElementById('tab-relationships').className = 'px-4 py-2 text-sm font-bold rounded-lg text-slate-500 hover:bg-slate-50 transition';
            loadPipelineDatasets();
        } else {
            document.getElementById('content-datasets').classList.add('hidden');
            document.getElementById('content-relationships').classList.remove('hidden');
            document.getElementById('tab-datasets').className = 'px-4 py-2 text-sm font-bold rounded-lg text-slate-500 hover:bg-slate-50 transition';
            document.getElementById('tab-relationships').className = 'px-4 py-2 text-sm font-bold rounded-lg bg-indigo-50 text-indigo-700 transition';
            loadPipelineRelationships();
            populateRelationshipDropdowns();
        }
    }

    async function loadPipelineDatasets() {
        try {
            const res = await fetch('/*{% url "dataset_manager_api" %}*/');
            const data = await res.json();
            const list = document.getElementById('pipeline-datasets-list');
            
            let tableListHtml = `
                <label class="flex items-center p-3 bg-indigo-50 border border-indigo-200 rounded-xl cursor-pointer hover:border-indigo-500 transition-all shadow-sm">
                    <input type="radio" name="datasource" value="__WORKSPACE__" class="w-4 h-4 text-indigo-600 border-slate-300 focus:ring-indigo-500" checked>
                    <div class="ml-3 overflow-hidden">
                        <span class="block text-[11px] font-black text-indigo-900 uppercase truncate">Toàn bộ Kho dữ liệu</span>
                        <span class="block text-[9px] text-indigo-600 mt-1">AI tự động liên kết các bảng</span>
                    </div>
                </label>
            `;

            if (data.datasets.length === 0) {
                list.innerHTML = '<tr><td colspan="6" class="text-center italic text-slate-500">Chưa có dữ liệu nào. Hãy nạp thêm.</td></tr>';
            } else {
                list.innerHTML = data.datasets.map(d => `
                    <tr>
                        <td class="font-bold text-slate-700">${d.name}</td>
                        <td><span class="status-badge badge-info">${d.source_type}</span></td>
                        <td class="text-xs font-mono text-slate-400">${d.table_name}</td>
                        <td>${d.row_count.toLocaleString()}</td>
                        <td>${d.created_at}</td>
                        <td>
                            <button onclick="deletePipelineDataset(${d.id})" class="text-red-500 hover:bg-red-50 p-1.5 rounded-lg transition-colors" title="Xóa">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                            </button>
                        </td>
                    </tr>
                `).join('');

                data.datasets.forEach(d => {
                    tableListHtml += `
                        <label class="flex items-center p-3 bg-white border border-slate-200 rounded-xl cursor-pointer hover:border-primary transition-all shadow-sm">
                            <input type="radio" name="datasource" value="${d.table_name}" class="w-4 h-4 text-primary border-slate-300 focus:ring-primary">
                            <div class="ml-3 overflow-hidden">
                                <span class="block text-[11px] font-bold text-slate-900 truncate">${d.name}</span>
                                <span class="block text-[9px] text-slate-500 mt-1">${d.row_count.toLocaleString()} dòng | ${d.source_type}</span>
                            </div>
                        </label>
                    `;
                });
            }
            
            const tableListEl = document.getElementById('table-list');
            if (tableListEl) {
                const shopeeOpt = Array.from(tableListEl.children).find(el => el.innerHTML.includes('temp_shopee_orders'));
                let finalHtml = tableListHtml;
                if (shopeeOpt) {
                    finalHtml = shopeeOpt.outerHTML + tableListHtml;
                }
                tableListEl.innerHTML = finalHtml;
            }
        } catch (e) {
            console.error(e);
        }
    }

    window.deletePipelineDataset = async function(id) {
        if(!confirm('Bạn có chắc chắn muốn xóa dữ liệu này? (Sẽ xóa luôn các liên kết liên quan)')) return;
        try {
            const res = await fetch(`/*{% url "dataset_manager_api" %}*/?id=${id}`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': '/*{{ csrf_token }}*/' }
            });
            const data = await res.json();
            if(res.ok) {
                loadPipelineDatasets();
            } else {
                alert('Lỗi: ' + data.error);
            }
        } catch (e) {
            alert('Lỗi kết nối');
        }
    }

    window.handlePipelineUpload = async function(input) {
        if (input.files.length) {
            await handleFileUpload(input.files[0]);
            setTimeout(loadPipelineDatasets, 2000);
        }
    }

    async function loadPipelineRelationships() {
        try {
            const res = await fetch('/*{% url "relationship_manager_api" %}*/');
            const data = await res.json();
            const list = document.getElementById('pipeline-relationships-list');
            
            if (data.relationships.length === 0) {
                list.innerHTML = '<tr><td colspan="5" class="text-center italic text-slate-500">Chưa có liên kết nào.</td></tr>';
            } else {
                list.innerHTML = data.relationships.map(r => `
                    <tr>
                        <td class="font-bold text-indigo-700">${r.source_table}</td>
                        <td class="font-mono text-slate-600">${r.source_column}</td>
                        <td class="font-bold text-emerald-700">${r.target_table}</td>
                        <td class="font-mono text-slate-600">${r.target_column}</td>
                        <td>
                            <button onclick="deleteRelationship(${r.id})" class="text-red-500 hover:bg-red-50 p-1.5 rounded-lg transition-colors" title="Xóa">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                            </button>
                        </td>
                    </tr>
                `).join('');
            }
        } catch (e) {
            console.error(e);
        }
    }

    async function populateRelationshipDropdowns() {
        try {
            const res = await fetch('/*{% url "dataset_manager_api" %}*/');
            const data = await res.json();
            
            const srcDs = document.getElementById('rel-source-ds');
            const tgtDs = document.getElementById('rel-target-ds');
            
            let options = '<option value="">-- Chọn Dataset --</option>';
            data.datasets.forEach(d => {
                options += `<option value="${d.id}">${d.name} (${d.table_name})</option>`;
            });
            
            srcDs.innerHTML = options;
            tgtDs.innerHTML = options;
            
        } catch(e) {}
    }

    window.loadColumnsForDS = async function(dsId, selectId) {
        const select = document.getElementById(selectId);
        if(!dsId) {
            select.innerHTML = '<option value="">-- Chọn Cột --</option>';
            return;
        }
        
        try {
            const res = await fetch('/*{% url "dataset_manager_api" %}*/');
            const data = await res.json();
            const ds = data.datasets.find(d => d.id == dsId);
            
            if (ds && ds.columns) {
                let options = '<option value="">-- Chọn Cột --</option>';
                ds.columns.forEach(c => {
                    options += `<option value="${c}">${c}</option>`;
                });
                select.innerHTML = options;
            }
        } catch(e) {}
    }

    window.createRelationship = async function() {
        const source_id = document.getElementById('rel-source-ds').value;
        const target_id = document.getElementById('rel-target-ds').value;
        const source_col = document.getElementById('rel-source-col').value;
        const target_col = document.getElementById('rel-target-col').value;
        
        if (!source_id || !target_id || !source_col || !target_col) {
            alert('Vui lòng chọn đầy đủ các bảng và cột cần liên kết.');
            return;
        }
        if (source_id === target_id) {
            alert('Không thể liên kết 1 bảng với chính nó.');
            return;
        }
        
        try {
            const res = await fetch('/*{% url "relationship_manager_api" %}*/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '/*{{ csrf_token }}*/' },
                body: JSON.stringify({
                    source_dataset_id: source_id,
                    target_dataset_id: target_id,
                    source_column: source_col,
                    target_column: target_col
                })
            });
            const data = await res.json();
            if(res.ok) {
                loadPipelineRelationships();
                document.getElementById('rel-source-ds').value = '';
                document.getElementById('rel-target-ds').value = '';
                document.getElementById('rel-source-col').innerHTML = '<option value="">-- Chọn Cột --</option>';
                document.getElementById('rel-target-col').innerHTML = '<option value="">-- Chọn Cột --</option>';
            } else {
                alert('Lỗi: ' + data.error);
            }
        } catch (e) {
            alert('Lỗi kết nối');
        }
    }

    window.deleteRelationship = async function(id) {
        if(!confirm('Xóa liên kết này?')) return;
        try {
            const res = await fetch(`/*{% url "relationship_manager_api" %}*/?id=${id}`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': '/*{{ csrf_token }}*/' }
            });
            if(res.ok) {
                loadPipelineRelationships();
            }
        } catch (e) {}
    }

    setTimeout(() => {
        if(typeof loadPipelineDatasets === 'function') loadPipelineDatasets();
    }, 1000);
