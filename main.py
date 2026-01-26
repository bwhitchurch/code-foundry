import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw, ImageFilter, ImageTk, ImageOps
from ttkthemes import ThemedTk
import tkinter.font as tkfont
import platform

# Optional: OpenCV-based decoding (if OpenCV is installed)
try:
    import cv2
    import numpy as np

    HAS_OPENCV = True
except Exception:
    HAS_OPENCV = False

APP_TITLE = "Code-Foundry QR Generator"


def make_qr_image(data: str, size_px: int, fg: str, bg: str) -> Image.Image:
    """Generate a QR code image from the provided data."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fg, back_color=bg).convert("RGB")
    img = img.resize((size_px, size_px), Image.Resampling.NEAREST)
    return img

def get_platform_font() -> str:
    """Return a default font name based on the platform."""
    system = platform.system()
    if system == "Windows":
        return "Segoe UI"
    elif system == "Darwin":
        return "SF Pro Text"
    else:
        return "DejaVu Sans"


def place_on_rounded_card(
    qr_img: Image.Image, bg: str, pad_px: int = 80, radius_px: int = 60
) -> Image.Image:
    """
    Put the QR on a rounded rectangle background with extra padding.
    Keeps quiet zone safe by adding margin outside the QR.
    """
    W, H = qr_img.size
    out_w, out_h = W + 2 * pad_px, H + 2 * pad_px

    card = Image.new("RGBA", (out_w, out_h), (0,0,0,0))
    mask = Image.new("L", (out_w, out_h), 0)

    # Draw rounded rect "card" (same bg color looks trivial; you can change later if desired)
    # If you want the card to be a different color than bg, add a separate 'card_color'.
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle([0, 0, out_w - 1, out_h - 1], radius=radius_px, fill=bg)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle([0, 0, out_w - 1, out_h - 1], radius=radius_px, fill=255)

    card.paste(qr_img, (pad_px, pad_px))
    card.putalpha(mask)
    return card


def add_center_logo(
    qr_img: Image.Image,
    logo_path: str,
    bg: str,
    logo_scale: float = 0.25,
    pad_scale: float = 0.10,
    round_radius_scale: float = 0.12,
) -> Image.Image:
    """Overlay a logo centered with white padded rounded rectangle behind it.

    Args:
        qr_img: The QR code image.
        logo_path: Path to the logo image file.
        logo_scale: Scale of the logo relative to the QR code size.
        pad_scale: Padding scale around the logo.
        round_radius_scale: Corner radius scale for rounded rectangle.
    """
    base = qr_img.convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    W, H = base.size
    logo_w = max(1, int(W * logo_scale))
    aspect = logo.height / max(1, logo.width)
    logo_h = max(1, int(logo_w * aspect))

    logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)

    pad = max(1, int(logo_w * pad_scale))
    box_w, box_h = logo_w + 2 * pad, logo_h + 2 * pad

    x0 = (W - box_w) // 2
    y0 = (H - box_h) // 2
    x1 = x0 + box_w
    y1 = y0 + box_h

    rr = int(min(box_w, box_h) * round_radius_scale)

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=rr, fill=bg)

    base = Image.alpha_composite(base, overlay)
    base.paste(logo, (x0 + pad, y0 + pad), mask=logo)

    return base.convert("RGB")

def decode_opencv_robust(pil_img: Image.Image) -> str:
    if not HAS_OPENCV:
        return ""

    rgb = np.array(pil_img.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    det = cv2.QRCodeDetector()

    def try_decode(img_bgr) -> str:
        text, pts, _ = det.detectAndDecode(img_bgr)
        return text or ""

    # 1) raw
    t = try_decode(bgr)
    if t:
        return t

    # 2) explicit invert (BGR)
    inv = 255 - bgr
    t = try_decode(inv)
    if t:
        return t

    # 3) thresholded (sometimes helps QRCodeDetector)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    t = try_decode(cv2.cvtColor(th, cv2.COLOR_GRAY2BGR))
    if t:
        return t

    # 4) inverted thresholded
    th_inv = 255 - th
    t = try_decode(cv2.cvtColor(th_inv, cv2.COLOR_GRAY2BGR))
    if t:
        return t

    return ""

def stress_tests(img: Image.Image) -> list[tuple[str, Image.Image]]:
    """Generate a few mild distortions to simulate real-world scanning."""

    out: list[tuple[str, Image.Image]] = []

    out.append(("original", img))

    # Downscale then upscale (printing/resizing artifacts)
    # w, h = img.size
    # for s in (0.75, 0.5):
    #     iw, ih = max(1, int(w * s)), max(1, int(h * s))
    #     resized = img.resize((iw, ih), Image.Resampling.LANCZOS)
    #     restored = resized.resize((w, h), Image.Resampling.NEAREST)
    #     out.append((f"resized_{s:.2f}", restored))

    # Slight blur
    out.append(("blur", img.filter(ImageFilter.GaussianBlur(radius=1.5))))

    # Tiny rotation with white background
    # out.append(
    #     (
    #         "rotate_3deg",
    #         img.rotate(3, expand=True, fillcolor=(255, 255, 255)).resize(
    #             img.size, Image.Resampling.NEAREST
    #         ),
    #     )
    # )
    # out.append(
    #     (
    #         "rotate_-3deg",
    #         img.rotate(-3, expand=True, fillcolor=(255, 255, 255)).resize(
    #             img.size, Image.Resampling.NEAREST
    #         ),
    #     )
    # )

    return out


class CodeFoundryApp(ThemedTk):
    def __init__(self):
        super().__init__(theme="arc")
        style = ttk.Style(self)
        style.configure(".", font=(get_platform_font(), 10))
        self.title(APP_TITLE)
        self.minsize(860, 520)

        self._qr_img_pil: Image.Image | None = None
        self._qr_img_tk: ImageTk.PhotoImage | None = None

        self.logo_path = tk.StringVar(value="")
        self.size_var = tk.IntVar(value=1200)
        self.logo_scale_var = tk.IntVar(value=25)
        self.fg_var = tk.StringVar(value="#000000")
        self.bg_var = tk.StringVar(value="#ffffff")
        self.card_enable_var = tk.BooleanVar(value=True)
        self.card_pad_var = tk.IntVar(value=80)
        self.card_radius_var = tk.IntVar(value=60)

        self._build_ui()
        self._update_color_swatches()

        self.text.insert("1.0", "https://example.com")

        self._set_status("Ready.", "muted")

    def pick_fg_color(self):
        _, hexcolor = colorchooser.askcolor(
            title="Choose foreground color (QR squares)",
            initialcolor=self.fg_var.get() or "#000000",
            parent=self,
        )
        if hexcolor:
            self.fg_var.set(hexcolor)
            self._update_color_swatches()

        self.generate()

    def pick_bg_color(self):
        _, hexcolor = colorchooser.askcolor(
            title="Choose background color",
            initialcolor=self.bg_var.get() or "#ffffff",
            parent=self,
        )
        if hexcolor:
            self.bg_var.set(hexcolor)
            self._update_color_swatches()
        self.generate()

    def _update_color_swatches(self):
        self.fg_swatch.configure(background=self.fg_var.get())
        self.bg_swatch.configure(background=self.bg_var.get())

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(
            self,
            padding=12,
        )
        right = ttk.Frame(self, padding=12)
        left.grid(row=0, column=0, sticky="nsew")
        right.grid(row=0, column=1, sticky="nsew")

        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        ttk.Label(left, text="Text / URL to encode:").grid(row=0, column=0, sticky="w")
        self.text = tk.Text(left, height=8, wrap="word")
        self.text.grid(row=1, column=0, sticky="nsew", pady=(6, 12))

        options = ttk.LabelFrame(left, text="Options", padding=10)
        options.grid(row=2, column=0, sticky="ew")
        options.columnconfigure(1, weight=1)

        # Foreground
        ttk.Label(options, text="Foreground:").grid(row=3, column=0, sticky="w", pady=(10, 0))
        fg_row = ttk.Frame(options)
        fg_row.grid(row=3, column=1, sticky="w", padx=(10, 0), pady=(10, 0))

        self.fg_swatch = tk.Label(fg_row, width=3, height=1, relief="solid")
        self.fg_swatch.grid(row=0, column=0, padx=(0, 8))
        ttk.Button(fg_row, text="Pick…", command=self.pick_fg_color).grid(row=0, column=1)

        # Background
        ttk.Label(options, text="Background:").grid(row=4, column=0, sticky="w", pady=(10, 0))
        bg_row = ttk.Frame(options)
        bg_row.grid(row=4, column=1, sticky="w", padx=(10, 0), pady=(10, 0))

        self.bg_swatch = tk.Label(bg_row, width=3, height=1, relief="solid")
        self.bg_swatch.grid(row=0, column=0, padx=(0, 8))
        ttk.Button(bg_row, text="Pick…", command=self.pick_bg_color).grid(row=0, column=1)

        ttk.Checkbutton(
            options, text="Rounded card background", variable=self.card_enable_var
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 0))

        card_row = ttk.Frame(options)
        card_row.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Label(card_row, text="Pad:").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            card_row,
            from_=20,
            to=300,
            increment=10,
            textvariable=self.card_pad_var,
            width=6,
        ).grid(row=0, column=1, padx=(6, 16))
        ttk.Label(card_row, text="Radius:").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(
            card_row,
            from_=0,
            to=200,
            increment=5,
            textvariable=self.card_radius_var,
            width=6,
        ).grid(row=0, column=3, padx=(6, 0))

        ttk.Label(options, text="QR size (px):").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            options,
            from_=900,
            to=2400,
            increment=50,
            textvariable=self.size_var,
            width=10,
        ).grid(row=0, column=1, sticky="w", padx=(10, 0))

        # Logo chooser
        ttk.Label(options, text="Logo:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        logo_row = ttk.Frame(options)
        logo_row.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(10, 0))
        logo_row.columnconfigure(0, weight=1)

        self.logo_entry = ttk.Entry(logo_row, textvariable=self.logo_path)
        self.logo_entry.grid(row=0, column=0, sticky="ew")

        ttk.Button(logo_row, text="Choose…", command=self.choose_logo).grid(
            row=0, column=1, padx=(8, 0)
        )
        ttk.Button(logo_row, text="Clear", command=self.clear_logo).grid(
            row=0, column=2, padx=(8, 0)
        )

        # Logo size slider
        self.logo_scale_label = ttk.Label(options, text=f"{self.logo_scale_var.get()}%")
        self.logo_scale_label.grid(
            row=2, column=2, sticky="w", padx=(10, 0), pady=(10, 0)
        )

        ttk.Label(options, text="Logo size (% of width):").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        slider = ttk.Scale(
            options,
            from_=10,
            to=50,
            orient="horizontal",
            command=self._on_logo_scale_slider,
        )
        slider.set(self.logo_scale_var.get())
        slider.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=(10, 0))


        # Buttons
        btns = ttk.Frame(left)
        btns.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        btns.columnconfigure((0, 1, 2), weight=1)

        ttk.Button(btns, text="Generate", command=self.generate).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(btns, text="Save PNG…", command=self.save_png).grid(
            row=0, column=1, sticky="ew", padx=(0, 8)
        )
        ttk.Button(btns, text="Validate", command=self.validate_current).grid(
            row=0, column=2, sticky="ew"
        )

        # Status
        self.status = ttk.Label(left, text="", anchor="w")
        self.status.grid(row=4, column=0, sticky="ew", pady=(10, 0))

        # Preview
        ttk.Label(right, text="Preview:").grid(row=0, column=0, sticky="w")
        self.preview = ttk.Label(right, anchor="center", relief="solid")
        self.preview.grid(row=1, column=0, sticky="nsew", pady=(6, 0))

    def _on_logo_scale_slider(self, value: str):
        # ttk.Scale gives a float-as-string
        v = int(float(value))
        self.logo_scale_var.set(v)
        self.logo_scale_label.configure(text=f"{v}%")

    def _set_status(self, msg: str, kind: str):
        # keep it simple: prefix icon-ish
        prefix = {
            "ok": "✅ ",
            "warn": "⚠️ ",
            "bad": "❌ ",
            "muted": "ℹ️ ",
        }.get(kind, "")
        self.status.configure(text=prefix + msg)

    def choose_logo(self):
        path = filedialog.askopenfilename(
            title="Choose logo image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")],
        )
        if path:
            self.logo_path.set(path)

    def clear_logo(self):
        self.logo_path.set("")

    def generate(self):
        data = self.text.get("1.0", "end").strip()
        if not data:
            messagebox.showwarning(
                "Missing text", "Please enter a URL or text to encode."
            )
            return

        fg = self.fg_var.get().strip() or "#000000"
        bg = self.bg_var.get().strip() or "#ffffff"

        size_px = int(self.size_var.get())
        img = make_qr_image(data, size_px, fg, bg)

        logo = self.logo_path.get().strip()
        if logo:
            try:
                img = add_center_logo(
                    img, logo, logo_scale=self.logo_scale_var.get() / 100.0
                )
            except Exception as e:
                self._set_status(f"Logo load/overlay failed: {e}", "warn")

        if self.card_enable_var.get():
            img = place_on_rounded_card(
                img,
                bg,
                pad_px=self.card_pad_var.get(),
                radius_px=self.card_radius_var.get(),
            )

        self._qr_img_pil = img
        self._update_preview()

        # Auto-validate after generation (if available)
        if HAS_OPENCV:
            self.validate_current()
        else:
            self._set_status(
                "Generated. (Install opencv-python to enable validation.)", "muted"
            )

    def _update_preview(self):
        if self._qr_img_pil is None:
            return

        # Fit to preview panel
        max_side = 360
        w, h = self._qr_img_pil.size
        scale = min(max_side / w, max_side / h, 1.0)
        disp = self._qr_img_pil.resize((int(w * scale), int(h * scale)), Image.NEAREST)

        self.preview.configure(background="#cccccc")
        self._qr_img_tk = ImageTk.PhotoImage(disp)
        self.preview.configure(image=self._qr_img_tk)

    def save_png(self):
        if self._qr_img_pil is None:
            self.generate()
            if self._qr_img_pil is None:
                return

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")],
            title="Save QR Code",
        )
        if not path:
            return

        try:
            self._qr_img_pil.save(path, format="PNG", optimize=True)
            self._set_status(f"Saved to {path}", "ok")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

    def validate_current(self):
        if self._qr_img_pil is None:
            self._set_status("Nothing to validate yet. Click Generate first.", "warn")
            return

        expected = self.text.get("1.0", "end").strip()
        if not expected:
            self._set_status("No input text to compare against.", "warn")
            return

        if not HAS_OPENCV:
            self._set_status("Validation unavailable (install opencv-python).", "muted")
            return

        # Run decode on stress tests and require all pass
        failures: list[str] = []
        for name, test_img in stress_tests(self._qr_img_pil):
            decoded = decode_opencv_robust(test_img)
            if decoded != expected:
                failures.append(name)

        if not failures:
            self._set_status("Validation passed (original + stress tests).", "ok")
        else:
            self._set_status(
                "Validation FAILED on: "
                + ", ".join(failures)
                + " (Try smaller logo or larger QR size.)",
                "bad",
            )


if __name__ == "__main__":
    app = CodeFoundryApp()
    app.mainloop()
