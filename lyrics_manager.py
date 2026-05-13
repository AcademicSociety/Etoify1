import os
import json
import requests
import re
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QSizePolicy, QPushButton, QHBoxLayout, QApplication
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve

class LyricsFetcherThread(QThread):
    """
    كلاس بيشتغل في الخلفية (Background Thread) 
    عشان يجيب الكلمات من غير ما يهنج واجهة البرنامج
    """
    lyrics_ready = pyqtSignal(dict)

    def __init__(self, title, artist=""):
        super().__init__()
        self.title = title
        self.artist = artist
        self.cache_dir = "lyrics_cache"
        os.makedirs(self.cache_dir, exist_ok=True) 

    def get_safe_filename(self, text):
        if not text: return "unknown"
        safe_text = re.sub(r'[\\/*?:"<>|]', "", text)
        return " ".join(safe_text.split()).replace(" ", "_")

    def run(self):
        clean_t = LyricsManager.clean_title(self.title)
        clean_a = LyricsManager.clean_title(self.artist)
        
        filename = f"{self.get_safe_filename(clean_t)}_{self.get_safe_filename(clean_a)}.json"
        cache_path = os.path.join(self.cache_dir, filename)

        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.lyrics_ready.emit(data)
                    return
            except Exception as e:
                print(f"Cache read error: {e}")

        lyrics_data = self._fetch_from_api(clean_t, clean_a)

        has_synced = bool(lyrics_data.get('synced'))
        has_plain = bool(lyrics_data.get('plain'))
        error_msgs = ["لم يتم العثور على كلمات لهذه الأغنية.", "خطأ في الاتصال بالسيرفر."]
        
        if has_synced or (has_plain and lyrics_data.get('plain') not in error_msgs):
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(lyrics_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"Cache write error: {e}")

        self.lyrics_ready.emit(lyrics_data)

    def _fetch_from_api(self, title, artist):
        if not artist and re.search(r'[-:|]', title):
            parts = re.split(r'[-:|]', title)
            if len(parts) >= 2:
                artist = LyricsManager.clean_title(parts[0].strip())
                title = LyricsManager.clean_title(parts[1].strip())

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        timeout_secs = 15

        try:
            if artist and title:
                url = f"https://lrclib.net/api/get?artist_name={artist}&track_name={title}"
                response = requests.get(url, headers=headers, timeout=timeout_secs)
                if response.status_code == 200:
                    data = response.json()
                    return {'synced': data.get('syncedLyrics'), 'plain': data.get('plainLyrics')}
            
            query = f"{title} {artist}".strip()
            search_url = f"https://lrclib.net/api/search?q={query}"
            search_res = requests.get(search_url, headers=headers, timeout=timeout_secs)
            
            if search_res.status_code == 200:
                results = search_res.json()
                if results:
                    return {
                        'synced': results[0].get('syncedLyrics'),
                        'plain': results[0].get('plainLyrics')
                    }
            
            search_url_title_only = f"https://lrclib.net/api/search?q={title}"
            search_res_title = requests.get(search_url_title_only, headers=headers, timeout=timeout_secs)
            
            if search_res_title.status_code == 200:
                results_title = search_res_title.json()
                if results_title:
                    return {
                        'synced': results_title[0].get('syncedLyrics'),
                        'plain': results_title[0].get('plainLyrics')
                    }

            return {'synced': None, 'plain': "لم يتم العثور على كلمات لهذه الأغنية."}
        except Exception as e:
            print(f"Lyrics Error: {e}")
            return {'synced': None, 'plain': "خطأ في الاتصال بالسيرفر. تأكد من اتصالك بالإنترنت."}

class LyricsManager:
    @staticmethod
    def clean_title(title):
        if not title: return ""
        title = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title)
        
        junk_words = [
            'official video', 'official audio', 'lyric video', 'lyrics', 
            'official music video', 'video', 'audio', '4k', '8k', 'high quality', 
            'hq', 'full hd', 'منتج حصري', 'فيديو كليب', 'حصريا', 'حصرياً',
            'كلمات', 'بالكلمات', 'مترجمة', 'مترجم', 'كاملة', 'اغنية', 'أغنية', 
            'نسخة أصلية', 'ريمكس', 'بطيء', 'موسيقى', 'كليب', 'Official', 'Music', 'Live'
        ]
        
        for word in junk_words:
            title = re.compile(re.escape(word), re.IGNORECASE).sub('', title)
        
        title = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', title) 
        return " ".join(title.split())

# =========================================================
# LyricsPage Class
# =========================================================

class LyricsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 20, 0, 20)
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(30, 0, 30, 10)
        self.header_layout.addStretch() 
        
        self.copy_btn = QPushButton("Copy Lyrics 📋")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.setFixedWidth(150)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                border-radius: 15px;
                padding: 8px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background-color: #1ed760;
                font-size: 15px;
            }
            QPushButton:pressed {
                background-color: #1aa34a;
            }
        """)
        self.copy_btn.clicked.connect(self.copy_lyrics_to_clipboard)
        self.header_layout.addWidget(self.copy_btn)
        self.layout.addLayout(self.header_layout)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")
        
        # إخفاء شريط التمرير لإعطاء شكل أنظف 
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.content_layout.setSpacing(10) # قللنا المسافات شوية عشان الشكل يكون متماسك
        
        self.scroll_area.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll_area)
        
        self.lines = [] 
        self.current_line_idx = -1
        self.fetcher_thread = None
        self.full_lyrics_text = "" 
        # تجهيز الأنيميشن السريع والسلس
        self.scroll_anim = QPropertyAnimation(self.scroll_area.verticalScrollBar(), b"value")
        # OutCubic: بيبدأ بسرعة جداً عشان يلحق الأغنية، وبعدين يبطأ بنعومة في النهاية
        self.scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic) 
        self.scroll_anim.setDuration(250) # سرعنا الأنيميشن عشان التزامن يكون مثالي

        # الاستايلات الأسطورية
        self.INACTIVE_STYLE = """
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 22px; 
            color: #555555; 
            font-weight: 600; 
            padding: 8px;
        """
        self.ACTIVE_STYLE = """
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 32px; 
            color: #1DB954; 
            font-weight: 900; 
            padding: 12px;
        """

    def load_lyrics_in_background(self, title, artist=""):
        self._clear_layout()
        loading_lbl = QLabel("جاري تحميل الكلمات...")
        loading_lbl.setStyleSheet("font-family: 'Segoe UI'; font-size: 18px; color: #1DB954; font-weight: bold;") 
        loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(loading_lbl)

        if self.fetcher_thread and self.fetcher_thread.isRunning():
            self.fetcher_thread.terminate()
            self.fetcher_thread.wait()

        self.fetcher_thread = LyricsFetcherThread(title, artist)
        self.fetcher_thread.lyrics_ready.connect(self.set_lyrics)
        self.fetcher_thread.start()

    def _clear_layout(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.lines.clear()
        self.current_line_idx = -1

    def set_lyrics(self, lyrics_data):
        self._clear_layout()

        synced = lyrics_data.get('synced')
        plain = lyrics_data.get('plain')

        # مساحة فارغة فوق عشان السطر الأول يكون في النص
        top_spacer = QWidget()
        top_spacer.setFixedHeight(self.scroll_area.height() // 2)
        self.content_layout.addWidget(top_spacer)

        all_text_lines = []
        if synced:
            for line in synced.split('\n'):
                match = re.search(r'\[(\d+):(\d+(?:\.\d+)?)\](.*)', line)
                if match:
                    text = match.group(3).strip()
                    text = re.sub(r'<\d+:\d+(?:\.\d+)?>', '', text).strip()
                    if text: all_text_lines.append(text)
                    
                    # ... (باقي كود إنشاء الـ Label كما هو عندك) ...
                    mins = int(match.group(1))
                    secs = float(match.group(2))
                    time_ms = int((mins * 60 + secs) * 1000)
                    lbl = QLabel(text if text else "• • •")
                    lbl.setWordWrap(True)
                    lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
                    lbl.setMaximumWidth(800) 
                    lbl.setStyleSheet(self.INACTIVE_STYLE)
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.content_layout.addWidget(lbl)
                    self.lines.append((time_ms, lbl))
            self.full_lyrics_text = "\n".join(all_text_lines)
        else:
            text = plain if plain else "No lyrics available for this song."
            self.full_lyrics_text = text
            # ... (باقي كود إنشاء الـ Label للـ plain كما هو عندك) ...
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            lbl.setMaximumWidth(800)
            lbl.setStyleSheet(self.INACTIVE_STYLE)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(lbl)

        # مساحة فارغة تحت عشان السطر الأخير يقدر يوصل للنص
        bottom_spacer = QWidget()
        bottom_spacer.setFixedHeight(self.scroll_area.height() // 2)
        self.content_layout.addWidget(bottom_spacer)

    def update_position(self, position_ms):
        if not self.lines:
            return
        
        # اللمسة السحرية: تعويض التأخير بـ 150 مللي ثانية عشان السطر يظهر مع النطق بالظبط
        adjusted_position = position_ms + 150 
        
        new_idx = -1
        for i, (time_ms, lbl) in enumerate(self.lines):
            if adjusted_position >= time_ms:
                new_idx = i
            else:
                break
        
        if new_idx != self.current_line_idx and new_idx != -1:
            if self.current_line_idx != -1:
                # إرجاع السطر القديم للوضع المطفي
                self.lines[self.current_line_idx][1].setStyleSheet(self.INACTIVE_STYLE)
            
            self.current_line_idx = new_idx
            current_lbl = self.lines[self.current_line_idx][1]
            
            # إضاءة السطر الجديد وتكبيره (Pop-up)
            current_lbl.setStyleSheet(self.ACTIVE_STYLE) 
            
            # حساب المكان المطلوب للأنيميشن
            vbar = self.scroll_area.verticalScrollBar()
            target_val = current_lbl.pos().y() + (current_lbl.height() // 2) - (self.scroll_area.viewport().height() // 2)
            
            target_val = int(max(vbar.minimum(), min(target_val, vbar.maximum())))
            
            # تشغيل الأنيميشن السلس
            self.scroll_anim.stop()
            self.scroll_anim.setStartValue(vbar.value())
            self.scroll_anim.setEndValue(target_val)
            self.scroll_anim.start()

    def copy_lyrics_to_clipboard(self):
        if self.full_lyrics_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.full_lyrics_text)
            
            # تغيير شكل الزرار مؤقتاً عشان المستخدم يعرف إنه اتنسخ
            original_text = self.copy_btn.text()
            self.copy_btn.setText("Copied! ✅")
            self.copy_btn.setStyleSheet(self.copy_btn.styleSheet().replace("#1DB954", "#2ecc71"))
            
            # رجع شكل الزرار بعد ثانية ونصف
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: (
                self.copy_btn.setText(original_text),
                self.copy_btn.setStyleSheet(self.copy_btn.styleSheet().replace("#2ecc71", "#1DB954"))
            ))