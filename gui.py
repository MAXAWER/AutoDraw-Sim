import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import threading
import time

from processor import ImageProcessor
from adb_handler import ADBController

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ADB Drawing Bot")
        self.geometry("1200x800")

        self.processor = ImageProcessor()
        self.adb = ADBController()
        self.is_drawing = False
        self.current_image_path = None
        
        # Interactive Canvas State
        self.canvas_image_item = None
        self.tk_image = None # Keep reference
        self.img_scale = 1.0
        self.img_x = 0
        self.img_y = 0
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        
        # Phone Screen Representation
        self.phone_w = 1080
        self.phone_h = 2400
        self.view_scale = 0.25 # Scale factor from Real Phone px to Canvas px
        self.phone_rect = (0,0,0,0)
        self.bg_image = None # PIL
        self.bg_image_tk = None # TK

        # Grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._init_sidebar()
        self._init_canvas_area()
        
    def _init_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)

        # Title
        label = ctk.CTkLabel(self.sidebar, text="ADB Painter", font=ctk.CTkFont(size=20, weight="bold"))
        label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # ADB
        self.btn_connect = ctk.CTkButton(self.sidebar, text="Connect ADB", command=self.connect_adb)
        self.btn_connect.grid(row=1, column=0, padx=20, pady=10)
        
        self.btn_capture = ctk.CTkButton(self.sidebar, text="Capture Screen", command=self.capture_screen_thread, fg_color="#3B8ED0")
        self.btn_capture.grid(row=2, column=0, padx=20, pady=(0, 10))
        
        self.lbl_status = ctk.CTkLabel(self.sidebar, text="Status: Disconnected", text_color="gray")
        self.lbl_status.grid(row=3, column=0, padx=20, pady=(0, 10))

        # 2. Config (Res + Speed)
        self.frm_config = ctk.CTkFrame(self.sidebar)
        self.frm_config.grid(row=4, column=0, padx=10, pady=5)
        
        # Row 0 of config: W x H
        ctk.CTkLabel(self.frm_config, text="Phone:").grid(row=0, column=0, padx=2)
        self.ent_phone_w = ctk.CTkEntry(self.frm_config, width=50)
        self.ent_phone_w.insert(0, "1080")
        self.ent_phone_w.grid(row=0, column=1, padx=2)
        ctk.CTkLabel(self.frm_config, text="x").grid(row=0, column=2)
        self.ent_phone_h = ctk.CTkEntry(self.frm_config, width=50)
        self.ent_phone_h.insert(0, "2400")
        self.ent_phone_h.grid(row=0, column=3, padx=2)
        self.btn_upd_res = ctk.CTkButton(self.frm_config, text="Set", width=40, command=self.update_resolution)
        self.btn_upd_res.grid(row=0, column=4, padx=5)
        
        # Row 1 of config: Speed slider
        ctk.CTkLabel(self.frm_config, text="Speed:").grid(row=1, column=0, padx=2, pady=5)
        self.slider_speed = ctk.CTkSlider(self.frm_config, from_=10, to=100, width=100)
        self.slider_speed.set(50) # Default 50ms
        self.slider_speed.grid(row=1, column=1, columnspan=3, padx=2, pady=5)

        # 3. Image Controls
        self.btn_load = ctk.CTkButton(self.sidebar, text="Load Image", command=self.load_image)
        self.btn_load.grid(row=5, column=0, padx=20, pady=(10, 5))
        
        self.btn_center = ctk.CTkButton(self.sidebar, text="Center Image", command=self.center_image, fg_color="gray")
        self.btn_center.grid(row=6, column=0, padx=20, pady=5)

        # 4. Processing
        self.lbl_thresh = ctk.CTkLabel(self.sidebar, text="Edge Sensitivity")
        self.lbl_thresh.grid(row=7, column=0, padx=20, pady=(10,0))
        
        # Single sensitivity slider: 1 = lots of edges, 10 = few edges
        self.slider_sens = ctk.CTkSlider(self.sidebar, from_=1, to=10, command=self.update_preview_event)
        self.slider_sens.set(5) # Default medium
        self.slider_sens.grid(row=8, column=0, padx=20, pady=5)
        
        self.chk_bg = ctk.CTkCheckBox(self.sidebar, text="Remove Background", command=self.update_preview_event)
        self.chk_bg.grid(row=9, column=0, padx=20, pady=5)
        
        # Detail Slider
        ctk.CTkLabel(self.sidebar, text="Detail (Low=Fast, High=Precise)").grid(row=10, column=0, padx=20, pady=(10,0))
        self.slider_detail = ctk.CTkSlider(self.sidebar, from_=1, to=10, command=self.update_preview_event)
        self.slider_detail.set(5) # Default mid-level
        self.slider_detail.grid(row=11, column=0, padx=20, pady=5)
        
        # 5. Controls
        self.btn_start = ctk.CTkButton(self.sidebar, text="START DRAWING", command=self.start_drawing, fg_color="green", height=40)
        self.btn_start.grid(row=12, column=0, padx=20, pady=10)
        
        self.btn_stop = ctk.CTkButton(self.sidebar, text="STOP", command=self.stop_drawing, fg_color="red")
        self.btn_stop.grid(row=13, column=0, padx=20, pady=5)
        
        self.btn_border = ctk.CTkButton(self.sidebar, text="Test: Draw Border", command=self.draw_border_thread, fg_color="gray")
        self.btn_border.grid(row=14, column=0, padx=20, pady=5)
        
        # 6. Adjustments
        self.frm_cal = ctk.CTkFrame(self.sidebar)
        self.frm_cal.grid(row=15, column=0, padx=10, pady=10)
        self.chk_pointer = ctk.CTkCheckBox(self.frm_cal, text="Show Touches", text_color="cyan")
        self.chk_pointer.grid(row=0, column=0, columnspan=2, pady=5)
        
        ctk.CTkLabel(self.frm_cal, text="Manual Offset X/Y:").grid(row=1, column=0, columnspan=2)
        self.ent_cal_x = ctk.CTkEntry(self.frm_cal, width=50)
        self.ent_cal_x.insert(0, "0")
        self.ent_cal_x.grid(row=2, column=0, padx=2, pady=5)
        self.ent_cal_y = ctk.CTkEntry(self.frm_cal, width=50)
        self.ent_cal_y.insert(0, "0")
        self.ent_cal_y.grid(row=2, column=1, padx=2, pady=5)

    def _init_canvas_area(self):
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Use Standard Tkinter Canvas for interaction
        self.canvas = tk.Canvas(self.canvas_frame, bg="#202020", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)    # Linux
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)    # Linux

        # Draw the phone screen area
        self.update_resolution()

    def capture_screen_thread(self):
        if not self.adb.device_id: return
        self.lbl_status.configure(text="Capturing...", text_color="yellow")
        threading.Thread(target=self._capture_logic).start()

    def _capture_logic(self):
        try:
            path = "screen_tmp.png"
            if self.adb.get_screenshot(path):
                self.bg_image = Image.open(path)
                self.lbl_status.configure(text="Captured", text_color="green")
                self.after(0, self.update_resolution) # Redraw with BG
        except Exception as e:
            print(f"Capture error: {e}")

    def update_resolution(self):
        try:
            self.phone_w = int(self.ent_phone_w.get())
            self.phone_h = int(self.ent_phone_h.get())
        except:
            pass
            
        # Recalculate view scale to fit canvas
        canvas_w = 800 # Approx
        canvas_h = 700 
        
        scale_w = canvas_w / self.phone_w
        scale_h = canvas_h / self.phone_h
        self.view_scale = min(scale_w, scale_h) * 0.8
        
        # Center the phone rect
        cw = int(self.phone_w * self.view_scale)
        ch = int(self.phone_h * self.view_scale)
        cx = 50
        cy = 50
        
        self.canvas.delete("phone_frame")
        
        # Draw BG if exists
        if self.bg_image:
            self.bg_image_tk = ImageTk.PhotoImage(self.bg_image.resize((cw, ch), Image.BICUBIC))
            self.canvas.create_image(cx, cy, image=self.bg_image_tk, anchor="nw", tags="phone_frame")
            
        self.canvas.create_rectangle(cx, cy, cx+cw, cy+ch, outline="white", width=2, tags="phone_frame")
        self.canvas.create_text(cx, cy-15, text=f"Phone Screen ({self.phone_w}x{self.phone_h})", fill="white", anchor="nw", tags="phone_frame")
        
        # Draw Center Crosshair
        mid_x = cx + cw/2
        mid_y = cy + ch/2
        self.canvas.create_line(mid_x, cy, mid_x, cy+ch, fill="#404040", dash=(4, 4), tags="phone_frame")
        self.canvas.create_line(cx, mid_y, cx+cw, mid_y, fill="#404040", dash=(4, 4), tags="phone_frame")
        
        self.phone_rect = (cx, cy, cw, ch) # Screen on canvas x,y,w,h

    def connect_adb(self):
        result = self.adb.check_connection()
        if self.adb.device_id:
            self.lbl_status.configure(text=f"Connected: {self.adb.device_id}", text_color="green")
            size = self.adb.get_screen_size()
            print(f"DEBUG: ADB Screen Size: {size}")
            if size:
                self.ent_phone_w.delete(0, "end")
                self.ent_phone_w.insert(0, str(size[0]))
                self.ent_phone_h.delete(0, "end")
                self.ent_phone_h.insert(0, str(size[1]))
                self.update_resolution()
        elif result:
             self.lbl_status.configure(text=f"Error: {result}", text_color="orange")
        else:
            self.lbl_status.configure(text="No Device Found", text_color="red")

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")])
        if path:
            self.current_image_path = path
            self.processor.load_image(path)
            self.img_scale = 1.0 # Reset scale
            self.update_preview()

    def center_image(self):
        if not self.preview_image: return
        
        # Phone Rect x,y,w,h
        px, py, pw, ph = self.phone_rect
        
        # Image w, h (scaled)
        iw = int(self.preview_image.width * self.img_scale)
        ih = int(self.preview_image.height * self.img_scale)
        
        self.img_x = px + (pw - iw) / 2
        self.img_y = py + (ph - ih) / 2
        
        self.redraw_canvas_image()

    def update_preview_event(self, _=None):
        if self.current_image_path:
            self.update_preview()

    def update_preview(self):
        # Heavy processing in thread
        self.lbl_status.configure(text="Processing image...", text_color="yellow")
        threading.Thread(target=self._threaded_process, daemon=True).start()

    def _threaded_process(self):
        try:
            low = int(self.slider_low.get())
            high = int(self.slider_high.get())
            # Safely get checkbox value in thread? Tkinter vars are not thread safe usually.
            # Ideally read them in main thread before spawning.
            # But let's try reading or pass args.
            # Better: read in update_preview and pass as args.
            pass
        except:
            pass

        # Since we can't easily pass args to the target without lambda or args=(), let's reorganize.
        # Actually reading .get() from main thread is safer.
        pass

    def update_preview(self):
        # Sensitivity: 1 = lots of edges (low=20, high=60), 10 = few edges (low=100, high=200)
        sens = self.slider_sens.get()
        low = int(20 + (sens - 1) * 10)  # 20 to 110
        high = int(60 + (sens - 1) * 15) # 60 to 195
        
        rem_bg = bool(self.chk_bg.get())
        detail_val = self.slider_detail.get()
        approx_eps = 0.5 + (10 - detail_val) * 0.5
        
        self.lbl_status.configure(text="Processing...", text_color="yellow")
        
        def run():
            # Higher quality preview (1000px instead of 500)
            pil_img, _ = self.processor.process(target_width=1000, low_threshold=low, high_threshold=high, approx_epsilon=approx_eps, remove_bg=rem_bg)
            self.after(0, self._on_process_complete, pil_img)
            
        threading.Thread(target=run, daemon=True).start()

    def _on_process_complete(self, pil_img):
        self.preview_image = pil_img
        self.lbl_status.configure(text="Ready", text_color="green")
        self.redraw_canvas_image()

    def redraw_canvas_image(self):
        if not self.preview_image:
            return
            
        # Resize for display based on img_scale
        # Original preview is 500w. Scaled by img_scale.
        w = int(self.preview_image.width * self.img_scale)
        h = int(self.preview_image.height * self.img_scale)
        
        if w > 1 and h > 1:
            resized = self.preview_image.resize((w, h), Image.NEAREST)
            self.tk_image = ImageTk.PhotoImage(resized)
            
            # If explicit position not set yet, center it
            if self.img_x == 0 and self.img_y == 0:
                self.img_x = self.phone_rect[0] + 20
                self.img_y = self.phone_rect[1] + 20
                
            if self.canvas_image_item:
                self.canvas.delete(self.canvas_image_item)
            self.canvas_image_item = self.canvas.create_image(self.img_x, self.img_y, image=self.tk_image, anchor="nw", tags="image")

    def on_mouse_down(self, event):
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

    def on_mouse_drag(self, event):
        dx = event.x - self.last_mouse_x
        dy = event.y - self.last_mouse_y
        
        if self.canvas_image_item:
            self.canvas.move(self.canvas_image_item, dx, dy)
            self.img_x += dx
            self.img_y += dy
            
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

    def on_mouse_wheel(self, event):
        # Determine scroll direction
        if event.num == 5 or event.delta < 0:
            factor = 0.9
        else:
            factor = 1.1
            
        mouse_x = event.x
        mouse_y = event.y
        
        # Offset of mouse relative to image origin
        rel_x = (mouse_x - self.img_x)
        rel_y = (mouse_y - self.img_y)
        
        # Update Scale
        self.img_scale *= factor
        
        # Update Position to keep mouse relative pos constant
        # new_x = mouse_x - (rel_x * factor)
        self.img_x = mouse_x - (rel_x * factor)
        self.img_y = mouse_y - (rel_y * factor)
        
        # Only redraw the visual item, DO NOT re-process the image
        self.redraw_canvas_image()

    def start_drawing(self):
        if self.is_drawing: return
        if not self.adb.device_id:
            self.lbl_status.configure(text="Connect ADB first!", text_color="orange")
            return

        # Pointer Location
        if self.chk_pointer.get():
            self.adb.set_pointer_location(True)

        self.is_drawing = True
        threading.Thread(target=self._drawing_thread).start()

    def stop_drawing(self):
        self.is_drawing = False
        # Disable pointer location on stop
        self.adb.set_pointer_location(False)

    def draw_border_thread(self):
        if self.is_drawing: return
        threading.Thread(target=self._border_logic).start()

    def _border_logic(self):
        if not self.adb.device_id:
            self.lbl_status.configure(text="No Device!", text_color="red")
            return
            
        try:
            w = int(self.ent_phone_w.get()) - 1
            h = int(self.ent_phone_h.get()) - 1
            
            # Pointer Location for border too?
            if self.chk_pointer.get():
                 self.adb.set_pointer_location(True)
            
            self.lbl_status.configure(text="Drawing Border...", text_color="yellow")
            
            # Top
            self.adb.swipe(0, 0, w, 0, 500)
            # Right
            self.adb.swipe(w, 0, w, h, 500)
            # Bottom
            self.adb.swipe(w, h, 0, h, 500)
            # Left
            self.adb.swipe(0, h, 0, 0, 500)
            
            self.lbl_status.configure(text="Border Done", text_color="green")
            
            if self.chk_pointer.get():
                time.sleep(2) # Let user see
                self.adb.set_pointer_location(False)
                
        except Exception as e:
            print(e)
            
    def _drawing_thread(self):
        try:
            if not self.canvas_image_item:
                print("No image on canvas")
                return

            # Get true visual coordinates from canvas
            coords = self.canvas.coords(self.canvas_image_item)
            if not coords:
                print("Image item coords not found")
                return
            
            vis_img_x, vis_img_y = coords
            
            # Calibration Offsets
            try:
                cal_x = int(self.ent_cal_x.get())
                cal_y = int(self.ent_cal_y.get())
            except:
                cal_x = 0
                cal_y = 0
            
            # 1. Calculate Real World Offset
            px, py, pw, ph = self.phone_rect
            
            # Recalculate ratio dynamically based on current resolution settings
            # just in case
            if pw == 0 or ph == 0:
                print("Phone rect Invalid")
                return

            ratio_w = self.phone_w / pw
            ratio_h = self.phone_h / ph
            
            # Offset in phone pixels (where image top-left corner is on phone screen)
            real_x = ((vis_img_x - px) * ratio_w) + cal_x
            real_y = ((vis_img_y - py) * ratio_h) + cal_y
            
            self.lbl_status.configure(text="Processing...", text_color="yellow")
            
            # Sensitivity settings
            sens = self.slider_sens.get()
            low = int(20 + (sens - 1) * 10)
            high = int(60 + (sens - 1) * 15)
            rem_bg = bool(self.chk_bg.get())
            
            # Detail settings
            detail_val = self.slider_detail.get()
            approx_eps = 0.5 + (10 - detail_val) * 0.5
            
            # Process at preview size (consistent with what's shown)
            # Paths will be in preview-pixel coordinates (0 to 1000 or original width)
            _, paths = self.processor.process(target_width=1000, low_threshold=low, high_threshold=high, approx_epsilon=approx_eps, remove_bg=rem_bg)
            
            self.lbl_status.configure(text=f"Generating {len(paths)} paths...", text_color="yellow")
            
            # Scale factor: convert preview coords to phone coords
            # Preview image is displayed at: preview_w * img_scale canvas pixels
            # This corresponds to: preview_w * img_scale * ratio phone pixels
            # So each preview pixel maps to: img_scale * ratio phone pixels
            preview_w = self.preview_image.width if hasattr(self, 'preview_image') and self.preview_image else 1000
            preview_h = self.preview_image.height if hasattr(self, 'preview_image') and self.preview_image else 1000
            
            scale_x = self.img_scale * ratio_w
            scale_y = self.img_scale * ratio_h
            
            print(f"DEBUG: preview={preview_w}x{preview_h}, scale={scale_x:.2f}x{scale_y:.2f}, offset={real_x:.0f},{real_y:.0f}")
            
            # Get Duration from speed slider
            draw_duration = int(self.slider_speed.get())
            
            commands = []
            
            for path in paths:
                if not self.is_drawing: break
                
                if len(path) < 2: continue
                
                # Scale preview coords to phone coords, then add offset
                final_points = []
                for x, y in path:
                    fx = int(real_x + x * scale_x)
                    fy = int(real_y + y * scale_y)
                    final_points.append((fx, fy))
                
                # Draw segments
                for i in range(len(final_points) - 1):
                    p1 = final_points[i]
                    p2 = final_points[i+1]
                    
                    dist = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
                    if dist < 5: continue # Skip small jitters to reduce artifacts
                    
                    cmd = f"input swipe {p1[0]} {p1[1]} {p2[0]} {p2[1]} {draw_duration}"
                    commands.append(cmd)
            
            if not self.is_drawing:
                self.after(0, lambda: self.lbl_status.configure(text="Stopped", text_color="red"))
                self.adb.set_pointer_location(False)
                return

            self.after(0, lambda c=len(commands): self.lbl_status.configure(text=f"Sending {c} cmds...", text_color="yellow"))
            
            # Standard batch execution (stable)
            chunk_size = 2000
            for i in range(0, len(commands), chunk_size):
                if not self.is_drawing: break
                chunk = commands[i:i+chunk_size]
                self.adb.execute_batch(chunk)
                
            self.after(0, lambda: self.lbl_status.configure(text="Done!", text_color="green"))
            self.is_drawing = False
            self.adb.set_pointer_location(False)
            
        except Exception as e:
            print(e)
            self.after(0, lambda err=str(e): self.lbl_status.configure(text=f"Error: {err}", text_color="red"))
            self.is_drawing = False
            self.adb.set_pointer_location(False)

if __name__ == "__main__":
    app = App()
    app.mainloop()
