#!/usr/bin/env python3
"""
FIXED YouTube Downloader - Normal YouTube API (Non-Async)
========================================================

FIXES APPLIED:
- Removed all async YouTube functionality
- Replaced AsyncYouTube with normal YouTube
- Used synchronous download patterns
- Fixed progress callbacks for normal YouTube objects
- Added automatic file extension detection and appending
- Fixed downloaded files to have proper extensions (.mp4, .webm, etc.)
- Maintained same UI and user experience

DEPENDENCIES:
pip install textual rich pytubefix

RUN:
python YoutubeFixed_Normal.py
"""

from rich.table import Table

from textual.app import ComposeResult, App
from textual.screen import Screen
from textual.widgets import Header, Footer, OptionList, Static, Input, ProgressBar
from textual.containers import Container, Horizontal, Vertical, Center, Middle
from textual.binding import Binding
from textual.color import Gradient
from pytubefix import YouTube
import threading
import time

# Global variables
VideoURL = ""
DownloadIDTag = ""
FileName = ""


class MetadataSelector(Screen):
    BINDINGS = [
        Binding(
            key="ctrl+x",
            action="close",
            description="Close This Screen",
            show=True,
            key_display="^x",
        ),
        Binding(
            key="ctrl+d",
            action="download",
            description="Start Download",
            show=True,
            key_display="^d",
        ),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        # Status line + two OptionLists (video / audio) in a Horizontal container
        yield Container(
            Vertical(
                Static("Loading streams...", id="Status"),
                Horizontal(
                    OptionList(id="VideoOptions"),
                    OptionList(id="AudioOptions"),
                    id="OptionsRow",
                ),
                id="TablesWrap",
            ),
            id="FetchContainer",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Show UI immediately and spawn background fetch task."""
        # prepare UI
        fetch_container = self.query_one("#FetchContainer")
        fetch_container.styles.border = ("heavy", "green")
        fetch_container.border_title = "Download Options — Fetching..."
        fetch_container.border_subtitle = "Please wait..."
        self.video_opts = self.query_one("#VideoOptions", OptionList)
        self.audio_opts = self.query_one("#AudioOptions", OptionList)

        # clear any existing options safely
        try:
            self.video_opts.clear()
            self.audio_opts.clear()
        except Exception:
            pass

        self._video_streams: list = []
        self._audio_streams: list = []
        self._last_selected = None

        # start background fetch in a thread
        threading.Thread(target=self._fetch_and_populate, daemon=True).start()

    def _fetch_and_populate(self) -> None:
        """Fetch metadata in a thread and populate the OptionLists."""
        global VideoURL, DownloadIDTag, FileName

        # Update UI from main thread
        def update_ui():
            status = self.query_one("#Status", Static)
            status.update("Fetching metadata...")

        self.app.call_from_thread(update_ui)

        try:
            # FIXED: Use normal YouTube (not AsyncYouTube)
            yt = YouTube(VideoURL)
        except Exception as e:

            def show_error():
                fetch_container = self.query_one("#FetchContainer")
                fetch_container.border_title = "Error Occurred"
                fetch_container.border_subtitle = "Check VideoURL or report the issue"
                status = self.query_one("#Status", Static)
                status.update(f"Error: {e}\nVideoURL: {VideoURL}")
                self.video_opts.display = False
                self.audio_opts.display = False

            self.app.call_from_thread(show_error)
            return

        # success — update header and hide status
        Title = "_".join(getattr(yt, "title", "Unknown title").split()[:6]) + "..."
        FileName = Title

        def update_success_ui():
            fetch_container = self.query_one("#FetchContainer")
            fetch_container.border_title = f"Download Options — {Title}"
            fetch_container.border_subtitle = "Select a stream"
            status = self.query_one("#Status", Static)
            status.display = False

        self.app.call_from_thread(update_success_ui)

        streams = list(getattr(yt, "streams", []))

        # Build video option tables: index, mimetype, resolution, vcodec, size
        def populate_video_streams():
            try:
                self.video_opts.clear()
            except Exception:
                pass

            video_stream_count = 0
            for i in range(0, len(streams)):
                s = streams[i]
                if getattr(s, "type", "") == "video":
                    mimetype = getattr(s, "mime_type", "-")
                    VideoID = getattr(s, "itag", "-")
                    resolution = getattr(s, "resolution", "")
                    vcodec = getattr(s, "codecs", "")
                    size = getattr(s, "filesize_mb", "")
                    size_str = f"{size} MB"

                    t = Table(expand=True)
                    t.add_column("Index", justify="right", no_wrap=True, width=5)
                    t.add_column("VideoID", justify="right", no_wrap=True, width=5)
                    t.add_column("MIME Type", no_wrap=True, width=12)
                    t.add_column("Resolution", no_wrap=True, width=10)
                    t.add_column("Video Codec", no_wrap=True, width=22)
                    t.add_column("Size [MB]", justify="right", no_wrap=True, width=8)

                    t.add_row(
                        str(i + 1),
                        str(VideoID),
                        str(mimetype),
                        str(resolution),
                        str(vcodec),
                        size_str,
                    )
                    self._video_streams.append(s)
                    self.video_opts.add_option(t)
                    video_stream_count += 1

        # Build audio option tables: index, mimetype, abr, acodec, size
        def populate_audio_streams():
            try:
                self.audio_opts.clear()
            except Exception:
                pass

            audio_stream_count = 0
            for i in range(0, len(streams)):
                s = streams[i]
                if getattr(s, "type", "") == "audio":
                    mimetype = getattr(s, "mime_type", "-")
                    AudioID = getattr(s, "itag", "-")
                    abr = getattr(s, "abr", "-")
                    acodec = getattr(s, "codecs", "")
                    size = getattr(s, "filesize_mb", "")
                    size_str = f"{size} MB"

                    t = Table(expand=True)
                    t.add_column("Index", justify="right", no_wrap=True, width=5)
                    t.add_column("AudioID", justify="right", no_wrap=True, width=5)
                    t.add_column("MIME Type", no_wrap=True, width=12)
                    t.add_column("ABR", no_wrap=True, width=10)
                    t.add_column("Audio Codec", no_wrap=True, width=22)
                    t.add_column("Size [MB]", justify="right", no_wrap=True, width=8)

                    t.add_row(
                        str(i + 1),
                        str(AudioID),
                        str(mimetype),
                        str(abr),
                        str(acodec),
                        size_str,
                    )
                    self._audio_streams.append(s)
                    self.audio_opts.add_option(t)
                    audio_stream_count += 1

        # Handle case with no streams
        def handle_no_streams():
            if len(streams) == 0:
                vt = Table(expand=True)
                vt.add_column("Info")
                vt.add_row("No video streams available")
                self.video_opts.add_option(vt)
                at = Table(expand=True)
                at.add_column("Info")
                at.add_row("No audio streams available")
                self.audio_opts.add_option(at)

        # Execute UI updates from main thread
        self.app.call_from_thread(populate_video_streams)
        self.app.call_from_thread(populate_audio_streams)
        self.app.call_from_thread(handle_no_streams)

    def action_close(self) -> None:
        self.app.pop_screen()

    # keep track of highlighted option (keyboard navigation / mouse hover)
    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        optlist = event.option_list
        idx = event.option_index  # index within that OptionList

        if optlist.id == "VideoOptions":
            # store as zero-based index into self._video_streams
            if 0 <= idx < len(self._video_streams):
                self._last_selected = ("video", idx)
            else:
                self._last_selected = None
        elif optlist.id == "AudioOptions":
            if 0 <= idx < len(self._audio_streams):
                self._last_selected = ("audio", idx)
            else:
                self._last_selected = None
        else:
            self._last_selected = None

    # handle activation (Enter / double click) — open DownloadUI and set global DownloadIDTag
    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        global DownloadIDTag
        optlist = event.option_list
        idx = event.option_index

        selected_stream = None
        kind = None
        if optlist.id == "VideoOptions" and 0 <= idx < len(self._video_streams):
            selected_stream = self._video_streams[idx]
            kind = "video"
        elif optlist.id == "AudioOptions" and 0 <= idx < len(self._audio_streams):
            selected_stream = self._audio_streams[idx]
            kind = "audio"

        if selected_stream is None:
            # nothing mapped — ignore
            return

        # set global DownloadIDTag to the selected stream's itag
        DownloadIDTag = getattr(selected_stream, "itag", "")

        # Always create a fresh DownloadUI instance
        self.app.push_screen(DownloadUI())

    def action_download(self) -> None:
        """Called by Ctrl+D binding. Use last highlighted selection; if none present,
        show a notification and do not open the download screen."""
        global DownloadIDTag

        if self._last_selected is None:
            # no selection — notify and don't open
            self.notify("No Data Selected Please select One from the Table", timeout=2)
            return

        kind, idx = self._last_selected
        selected_stream = None
        if kind == "video" and 0 <= idx < len(self._video_streams):
            selected_stream = self._video_streams[idx]
        elif kind == "audio" and 0 <= idx < len(self._audio_streams):
            selected_stream = self._audio_streams[idx]

        if selected_stream is None:
            self.notify("No Data Selected Please select One from the Table", timeout=2)
            return

        # update global tag and create fresh DownloadUI
        DownloadIDTag = getattr(selected_stream, "itag", "")
        self.app.push_screen(DownloadUI())


class DownloadUI(Screen):
    # NO BINDINGS - Cannot close manually during download

    def compose(self) -> ComposeResult:
        global VideoURL, DownloadIDTag, FileName

        # Create gradient for progress bar
        gradient = Gradient.from_colors(
            "#881177",
            "#aa3355",
            "#cc6666",
            "#ee9944",
            "#eedd00",
            "#99dd55",
            "#44dd88",
            "#22ccbb",
            "#00bbcc",
            "#0099cc",
            "#3366bb",
            "#663399",
        )

        yield Header()
        yield Container(
            Vertical(
                Static(f"📹 Video: {FileName}", id="video-info"),
                Static(f"🔗 URL: {VideoURL}", id="url-info"),
                Static(f"🏷️  Stream ID: {DownloadIDTag}", id="tag-info"),
                Static("Initializing download...", id="status-text"),
                # Beautiful gradient progress bar
                Container(
                    Center(
                        Middle(ProgressBar(total=100, gradient=gradient, id="progress"))
                    ),
                    id="progress-container",
                ),
                Static("⏱️  Time remaining: --:--", id="time-remaining"),
                Static("📊 Download speed: -- MB/s", id="download-speed"),
                id="download-content",
            ),
            id="DownloadContainer",
        )
        yield Footer()

    def on_mount(self) -> None:
        # container styling
        DownloadContainer = self.query_one("#DownloadContainer")
        DownloadContainer.styles.border = ("heavy", "green")
        DownloadContainer.border_title = "🔄 Downloading in Progress"
        DownloadContainer.border_subtitle = "Please wait, do not close this window"
        DownloadContainer.styles.border_title_align = "center"
        DownloadContainer.styles.border_title_style = "bold"
        DownloadContainer.styles.border_subtitle_align = "center"
        DownloadContainer.styles.border_subtitle_style = "italic"

        # Start the download process in a thread
        threading.Thread(target=self.start_download, daemon=True).start()

    def start_download(self):
        """Start the download process with progress tracking"""
        global VideoURL, DownloadIDTag, FileName

        try:
            # Clean up filename - remove trailing "..."
            clean_filename = FileName
            if clean_filename.endswith("..."):
                clean_filename = clean_filename[:-3]

            # Update status
            def update_status(message):
                status_text = self.query_one("#status-text", Static)
                status_text.update(message)

            self.app.call_from_thread(
                lambda: update_status("🔄 Connecting to YouTube...")
            )

            # FIXED: Use normal YouTube object (not AsyncYouTube)
            yt = YouTube(VideoURL)

            # Get the specific stream first to determine extension
            stream = yt.streams.get_by_itag(int(DownloadIDTag))

            # Get the file extension from the stream
            mime_type = getattr(stream, "mime_type", "")
            subtype = getattr(stream, "subtype", "")

            # Determine file extension based on stream properties
            if subtype:
                file_extension = f".{subtype}"
            elif mime_type:
                # Fallback: extract extension from MIME type
                if "mp4" in mime_type:
                    file_extension = ".mp4"
                elif "webm" in mime_type:
                    file_extension = ".webm"
                elif "ogg" in mime_type:
                    file_extension = ".ogg"
                elif "mp3" in mime_type:
                    file_extension = ".mp3"
                elif "m4a" in mime_type:
                    file_extension = ".m4a"
                elif "wav" in mime_type:
                    file_extension = ".wav"
                else:
                    # Generic fallback
                    file_extension = ".video"
            else:
                file_extension = ".video"

            # Add extension to filename
            final_filename = f"{clean_filename}{file_extension}"

            # Variables for progress tracking
            start_time = time.time()
            last_update_time = start_time
            last_bytes_downloaded = 0

            def on_progress(stream, chunk, bytes_remaining):
                nonlocal last_update_time, last_bytes_downloaded
                current_time = time.time()
                elapsed = current_time - last_update_time

                if elapsed >= 0.5:  # Update every 0.5 seconds to avoid UI lag
                    total = stream.filesize
                    downloaded = total - bytes_remaining
                    percent = (downloaded / total) * 100

                    # Calculate download speed
                    bytes_diff = downloaded - last_bytes_downloaded
                    speed_bps = bytes_diff / elapsed if elapsed > 0 else 0
                    speed_mbps = speed_bps / (1024 * 1024)

                    # Calculate estimated time remaining
                    remaining_bytes = bytes_remaining
                    if speed_bps > 0:
                        eta_seconds = remaining_bytes / speed_bps
                        eta_mins = int(eta_seconds // 60)
                        eta_secs = int(eta_seconds % 60)
                        eta_str = f"{eta_mins:02d}:{eta_secs:02d}"
                    else:
                        eta_str = "--:--"

                    def update_progress():
                        progress_bar = self.query_one("#progress", ProgressBar)
                        time_remaining = self.query_one("#time-remaining", Static)
                        download_speed = self.query_one("#download-speed", Static)

                        progress_bar.update(progress=percent)
                        time_remaining.update(f"⏱️  Time remaining: {eta_str}")
                        download_speed.update(
                            f"📊 Download speed: {speed_mbps:.2f} MB/s"
                        )

                        # Update status with current action
                        if percent < 25:
                            update_status("🔄 Downloading video data...")
                        elif percent < 50:
                            update_status("📹 Processing video stream...")
                        elif percent < 75:
                            update_status("🎵 Finalizing download...")
                        elif percent < 100:
                            update_status("✅ Almost done!")

                    # Update UI from main thread
                    self.app.call_from_thread(update_progress)

                    last_update_time = current_time
                    last_bytes_downloaded = downloaded

            def on_complete(stream, file_path):
                """Called when download is complete"""

                def update_completion():
                    self.on_download_complete(file_path)

                self.app.call_from_thread(update_completion)

            # Register callbacks
            yt.register_on_progress_callback(on_progress)
            yt.register_on_complete_callback(on_complete)

            # Start the actual download (blocking call)
            stream.download(filename=final_filename)

        except Exception as e:
            # Handle any errors
            def show_error():
                status_text = self.query_one("#status-text", Static)
                status_text.update(f"❌ Download failed: {str(e)}")

                # Wait a moment then pop the screen
                self.set_timer(3.0, self.close_screen)

            self.app.call_from_thread(show_error)

    def on_download_complete(self, file_path):
        """Handle successful download completion"""
        try:
            status_text = self.query_one("#status-text", Static)
            progress_bar = self.query_one("#progress", ProgressBar)

            # Update to show completion
            status_text.update("🎉 Download completed successfully!")
            progress_bar.update(progress=100)

            # Wait 3 seconds, then show congratulations screen
            self.set_timer(3.0, lambda: self.show_congratulations(file_path))
        except Exception as e:
            print(f"Error in on_download_complete: {e}")
            self.app.pop_screen()

    def show_congratulations(self, file_path):
        """Show the congratulations screen"""
        try:
            self.app.pop_screen()  # Close current download screen
            self.app.push_screen(CongratulationsScreen(file_path))
        except Exception as e:
            print(f"Error showing congratulations: {e}")
            self.app.pop_screen()

    def close_screen(self):
        """Close the download screen"""
        try:
            self.app.pop_screen()
        except Exception as e:
            print(f"Error closing screen: {e}")


class CongratulationsScreen(Screen):
    """Screen shown after successful download"""

    BINDINGS = [
        Binding(
            key="ctrl+x",
            action="close",
            description="Close This Screen",
            show=True,
            key_display="^x",
        ),
    ]

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def compose(self) -> ComposeResult:
        global FileName

        # Clean filename for display
        clean_filename = FileName
        if clean_filename.endswith("..."):
            clean_filename = clean_filename[:-3]

        yield Header()
        yield Container(
            Vertical(
                Static("🎉 Congratulations! 🎉", id="congrats-title", classes="title"),
                Static(
                    f"✅ Your download has been completed successfully!",
                    id="success-message",
                ),
                Static(f"📁 Filename: Loading...", id="filename"),
                Static(f"📂 Downloaded to: {self.file_path}", id="filepath"),
                Static(
                    "✨ You can now close this screen or download another video",
                    id="instruction",
                ),
                id="congrats-content",
            ),
            id="congrats-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        # Styling for congratulations screen
        try:
            # Clean filename for display and add extension
            clean_filename = FileName
            if clean_filename.endswith("..."):
                clean_filename = clean_filename[:-3]

            # Get the file extension from the file path if available
            if self.file_path and "." in self.file_path:
                # Extract extension from the actual downloaded file path
                file_extension = "." + self.file_path.split(".")[-1]
                display_filename = f"{clean_filename}{file_extension}"
            else:
                display_filename = clean_filename

            # Update the congratulations display
            filename_widget = self.query_one("#filename")
            filename_widget.update(f"📁 Filename: {display_filename}")

            # Apply styling changes
            congrats_container = self.query_one("#congrats-container")
            congrats_container.styles.border = ("heavy", "bright_green")
            congrats_container.border_title = "🎊 Download Complete 🎊"
            congrats_container.border_subtitle = (
                f"Total download time: Download completed"
            )
            congrats_container.styles.border_title_align = "center"
            congrats_container.styles.border_title_style = "bold"

            # Style the title
            title = self.query_one("#congrats-title")
            title.styles.text_align = "center"
            title.styles.text_style = "bold"
            title.styles.color = "bright_green"

            # Add auto-close timer (optional)
            self.set_timer(10.0, self.close_screen)
        except Exception as e:
            print(f"Error in congratulations on_mount: {e}")

    def action_close(self) -> None:
        """Close the congratulations screen"""
        try:
            self.app.pop_screen()
        except Exception as e:
            print(f"Error closing congratulations: {e}")

    def close_screen(self):
        """Close the congratulations screen"""
        try:
            self.app.pop_screen()
        except Exception as e:
            print(f"Error closing congratulations: {e}")


class Help(Screen):
    BINDINGS = [
        Binding(
            key="ctrl+x",
            action="close",
            description="Close This Screen",
            show=True,
            key_display="^x",
        )
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            "Hello from the Help Screen\n\nPress Ctrl+x to close.", id="help-message"
        )
        yield Footer()

    def action_close(self) -> None:
        self.app.pop_screen()


class MainScreen(Screen):
    CSS_PATH = "css/FinalMain.tcss"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Container(
            Input(
                placeholder="Enter the Youtube Video/Playlist/Channel Link",
                id="main-input",
            ),
            id="MainContainer",
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        global VideoURL
        VideoURL = event.value.strip()
        self.app.push_screen("MetadataSelector")

    def on_mount(self) -> None:
        # container styling
        MainContainer = self.query_one("#MainContainer")
        MainContainer.styles.border = ("heavy", "green")
        MainContainer.border_title = "UI Wrapper Over the PyTubeFix Library"
        MainContainer.border_subtitle = "Design & Build by Sombit Pramanik"
        MainContainer.styles.border_title_align = "center"
        MainContainer.styles.border_title_style = "bold"
        MainContainer.styles.border_subtitle_align = "center"
        MainContainer.styles.border_subtitle_style = "italic"


class PytubeFixTui(App):

    BINDINGS = [
        Binding(
            key="ctrl+underscore",
            action="help",
            description="Open Help",
            key_display="^/",
            show=True,
        ),
        Binding(
            key="ctrl+q", action="quit", description="Quit", show=True, key_display="^q"
        ),
        Binding(
            key="ctrl+t",
            action="theme",
            description="Change Theme",
            key_display="^t",
            show=True,
        ),
    ]
    THEMES = [
        "textual-dark",
        "textual-light",
        "nord",
        "gruvbox",
        "catppuccin-mocha",
        "dracula",
        "tokyo-night",
        "monokai",
        "flexoki",
        "catppuccin-latte",
        "solarized-light",
    ]
    SCREENS = {
        "MainScreen": MainScreen,
        "help": Help,
        "MetadataSelector": MetadataSelector,
    }

    def on_mount(self) -> None:
        self.theme = "nord"
        self._theme_index = 2
        self.push_screen("MainScreen")

    def action_help(self) -> None:
        self.app.push_screen("help")

    def action_theme(self) -> None:
        self._theme_index = (self._theme_index + 1) % len(self.THEMES)
        next_theme = self.THEMES[self._theme_index]
        self.theme = next_theme
        self.notify(f"Theme Changed to {next_theme}", timeout=2)


if __name__ == "__main__":
    PytubeFixTui().run()
