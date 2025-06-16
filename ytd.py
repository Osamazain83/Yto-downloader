import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import yt_dlp
import os

class VideoItem(ttk.Frame):
    def __init__(self, parent, title, url):
        super().__init__(parent)
        self.url = url
        self.title = title

        self.var_selected = tk.BooleanVar(value=False)
        self.check = ttk.Checkbutton(self, variable=self.var_selected)
        self.check.pack(side="left", padx=5)

        self.lbl_title = ttk.Label(self, text=title, width=50, anchor="w", wraplength=350)
        self.lbl_title.pack(side="left", padx=5)

        self.status_label = ttk.Label(self, text="Idle", width=10)
        self.status_label.pack(side="left", padx=5)

        self.progress = ttk.Progressbar(self, length=120)
        self.progress.pack(side="left", padx=5)

    def is_selected(self):
        return self.var_selected.get()

    def set_status(self, text):
        self.status_label.config(text=text)

    def set_progress(self, val):
        self.progress['value'] = val

class YouTubeDownloaderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader")
        self.geometry("650x480")
        self.resizable(False, False)
        self.configure(bg="#2e2e2e")

        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TLabel", background="#2e2e2e", foreground="#ddd")
        style.configure("TCheckbutton", background="#2e2e2e", foreground="#ddd")
        style.configure("TButton", background="#444", foreground="#eee", padding=6)
        style.map("TButton", background=[('active', '#666')])
        style.configure("TProgressbar", troughcolor="#444", background="#6a9fb5")

        # URL entry
        url_frame = ttk.Frame(self, style="TFrame")
        url_frame.pack(fill="x", padx=15, pady=(15, 10))
        ttk.Label(url_frame, text="YouTube URL:").pack(side="left", padx=(0,5))
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=60)
        self.url_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(url_frame, text="Add", command=self.add_url).pack(side="left", padx=5)

        # Format and quality selectors
        options_frame = ttk.Frame(self)
        options_frame.pack(fill="x", padx=15, pady=(0,10))

        ttk.Label(options_frame, text="Format:").pack(side="left", padx=(0,5))
        self.format_var = tk.StringVar(value="mp4")
        ttk.Radiobutton(options_frame, text="MP4 (Video)", variable=self.format_var, value="mp4").pack(side="left")
        ttk.Radiobutton(options_frame, text="MP3 (Audio)", variable=self.format_var, value="mp3").pack(side="left")

        ttk.Label(options_frame, text="Quality:").pack(side="left", padx=(20,5))
        self.quality_var = tk.StringVar(value="720p")
        quality_options = ["144p", "240p", "360p", "480p", "720p", "1080p"]
        self.quality_combo = ttk.Combobox(options_frame, values=quality_options, width=7, textvariable=self.quality_var, state="readonly")
        self.quality_combo.pack(side="left")

        # Videos list container
        self.videos_frame = ttk.Frame(self)
        self.videos_frame.pack(fill="both", expand=True, padx=15, pady=(0,10))

        # Scrollable canvas for video items
        canvas = tk.Canvas(self.videos_frame, bg="#2e2e2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.videos_frame, orient="vertical", command=canvas.yview)
        self.videos_container = ttk.Frame(canvas)

        self.videos_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.videos_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=15, pady=(5, 10))

        ttk.Button(btn_frame, text="Select All", command=self.select_all).pack(side="left", expand=True, padx=5)
        ttk.Button(btn_frame, text="Deselect All", command=self.deselect_all).pack(side="left", expand=True, padx=5)
        self.download_btn = ttk.Button(btn_frame, text="Download Selected", command=self.start_downloads)
        self.download_btn.pack(side="left", expand=True, padx=5)

        self.pause_btn = ttk.Button(btn_frame, text="Pause", command=self.pause_downloads, state="disabled")
        self.pause_btn.pack(side="left", expand=True, padx=5)

        self.resume_btn = ttk.Button(btn_frame, text="Resume", command=self.resume_downloads, state="disabled")
        self.resume_btn.pack(side="left", expand=True, padx=5)

        self.cancel_btn = ttk.Button(btn_frame, text="Cancel Download", command=self.cancel_downloads, state="disabled")
        self.cancel_btn.pack(side="left", expand=True, padx=5)

        # Overall progress bar and status label
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill="x", padx=15, pady=(0,15))

        self.overall_progress = ttk.Progressbar(bottom_frame, length=600)
        self.overall_progress.pack(side="top", pady=5)

        self.status_label = ttk.Label(bottom_frame, text="Idle")
        self.status_label.pack(side="top", pady=2)

        self.video_items = []
        self.downloading = False
        self.pause_event = threading.Event()
        self.cancel_event = threading.Event()
        self.pause_event.set()
        self.current_download_thread = None

    def add_url(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a YouTube URL.")
            return
        # Fetch title to display nicely
        def fetch_title():
            self.status_label.config(text="Fetching video info...")
            try:
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'Unknown title')
                self.status_label.config(text="Video info fetched.")
                self.add_video_item(title, url)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to fetch video info: {e}")
                self.status_label.config(text="Idle")

        threading.Thread(target=fetch_title, daemon=True).start()
        self.url_var.set("")

    def add_video_item(self, title, url):
        item = VideoItem(self.videos_container, title, url)
        item.pack(fill="x", pady=3)
        self.video_items.append(item)

    def select_all(self):
        for item in self.video_items:
            item.var_selected.set(True)

    def deselect_all(self):
        for item in self.video_items:
            item.var_selected.set(False)

    def start_downloads(self):
        if self.downloading:
            messagebox.showinfo("Download in progress", "Downloads are already in progress.")
            return

        selected = [item for item in self.video_items if item.is_selected()]
        if not selected:
            messagebox.showinfo("No selection", "Please select videos to download.")
            return

        folder = filedialog.askdirectory(title="Select Download Folder")
        if not folder:
            return

        self.pause_event.set()
        self.cancel_event.clear()
        self.downloading = True
        self.download_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.resume_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.status_label.config(text="Starting downloads...")
        self.overall_progress['value'] = 0

        self.current_download_thread = threading.Thread(target=self.download_videos, args=(selected, folder), daemon=True)
        self.current_download_thread.start()

    def pause_downloads(self):
        if not self.downloading:
            return
        self.pause_event.clear()
        self.pause_btn.config(state="disabled")
        self.resume_btn.config(state="normal")
        self.status_label.config(text="Paused. Waiting to stop current chunk...")

    def resume_downloads(self):
        if not self.downloading:
            return
        self.pause_event.set()
        self.pause_btn.config(state="normal")
        self.resume_btn.config(state="disabled")
        self.status_label.config(text="Resuming downloads...")

    def cancel_downloads(self):
        if not self.downloading:
            return
        # Set cancel event to stop ASAP
        self.cancel_event.set()
        self.pause_event.set()  # in case paused, allow thread to continue and check cancel

        self.status_label.config(text="Cancelling downloads...")
        self.pause_btn.config(state="disabled")
        self.resume_btn.config(state="disabled")
        self.cancel_btn.config(state="disabled")

    def make_hook(self, item):
        def hook(d):
            if self.cancel_event.is_set():
                # This will not forcibly kill yt-dlp, but the next iteration will stop
                raise yt_dlp.utils.DownloadError("Download cancelled by user.")

            if d['status'] == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
                downloaded_bytes = d.get('downloaded_bytes', 0)
                percent = int(downloaded_bytes / total_bytes * 100)
                item.set_progress(percent)
            elif d['status'] == 'finished':
                item.set_progress(100)
                item.set_status("Processing...")
        return hook

    def download_videos(self, items, folder):
        total = len(items)
        done = 0

        for item in items:
            item.set_status("Waiting")
            item.set_progress(0)

        for item in items:
            if self.cancel_event.is_set():
                self.status_label.config(text="Downloads cancelled.")
                break

            # Pause check before each video
            while not self.pause_event.is_set():
                if self.cancel_event.is_set():
                    self.status_label.config(text="Downloads cancelled.")
                    break
                self.status_label.config(text="Paused. Waiting to resume...")
                threading.Event().wait(0.5)

            if self.cancel_event.is_set():
                break

            item.set_status("Downloading")

            ydl_opts = {
                'outtmpl': os.path.join(folder, '%(title)s.%(ext)s'),
                'quiet': True,
                'progress_hooks': [self.make_hook(item)],
                'continuedl': True,  # enable resuming
            }
            if self.format_var.get() == 'mp3':
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            else:
                quality_num = self.quality_var.get().replace('p','')
                ydl_opts['format'] = f'bestvideo[ext=mp4][height<={quality_num}]+bestaudio/best/best'

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([item.url])
                item.set_status("Done")
                item.set_progress(100)
            except yt_dlp.utils.DownloadError as e:
                item.set_status("Cancelled" if self.cancel_event.is_set() else "Error")
            except Exception as e:
                item.set_status("Error")
                print(f"Download error for {item.title}: {e}")

            done += 1
            self.overall_progress['value'] = (done / total) * 100

            # Pause check after each video
            while not self.pause_event.is_set():
                if self.cancel_event.is_set():
                    self.status_label.config(text="Downloads cancelled.")
                    break
                self.status_label.config(text="Paused. Waiting to resume...")
                threading.Event().wait(0.5)

            if self.cancel_event.is_set():
                break

        if self.cancel_event.is_set():
            # Reset progress/status for unfinished items
            for item in items:
                if item.status_label.cget("text") not in ["Done", "Cancelled"]:
                    item.set_status("Idle")
                    item.set_progress(0)

            self.status_label.config(text="Downloads cancelled.")
        else:
            self.status_label.config(text="All downloads finished.")

        self.download_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.resume_btn.config(state="disabled")
        self.cancel_btn.config(state="disabled")
        self.downloading = False

if __name__ == "__main__":
    app = YouTubeDownloaderGUI()
    app.mainloop()
