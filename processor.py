import cv2
import numpy as np
from PIL import Image

class ImageProcessor:
    def __init__(self):
        self.original_image = None
        self.processed_image = None
        self.edges = None
        self.paths = []
        
    def load_image(self, path):
        """Loads an image from path."""
        self.original_image = cv2.imread(path)
        if self.original_image is None:
            raise ValueError("Could not load image")
        # Convert to RGB for display if needed later (OpenCV is BGR)
        return self.original_image

    def process(self, target_width=None, low_threshold=50, high_threshold=150, approx_epsilon=1.0, remove_bg=False):
        """
        Processes the loaded image to find drawing paths.
        
        Args:
            target_width: Resize image to this width (maintain aspect ratio).
            low_threshold: Canny edge detection lower bound.
            high_threshold: Canny edge detection upper bound.
            approx_epsilon: Douglas-Peucker approximation accuracy.
            remove_bg: Boolean, whether to use rembg to remove background.
            
        Returns:
            preview_image: A PIL Image of the edges for display.
            paths: List of list of points [(x,y), (x,y),...] representing lines to draw.
        """
        if self.original_image is None:
            return None, []

        img = self.original_image.copy()
        
        if remove_bg:
            try:
                from rembg import remove
                # Convert to PIL
                pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                output = remove(pil_img)
                
                # Composite on white background
                if output.mode == 'RGBA':
                    background = Image.new('RGB', output.size, (255, 255, 255))
                    background.paste(output, mask=output.split()[3])
                    img = np.array(background)
                    # Convert back to BGR for OpenCV
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            except ImportError:
                print("rembg not installed, skipping background removal")
            except Exception as e:
                print(f"Error removing background: {e}")
        
        # Resize
        h, w = img.shape[:2]
        if target_width and target_width < w:
            scale = target_width / w
            new_h = int(h * scale)
            img = cv2.resize(img, (target_width, new_h), interpolation=cv2.INTER_AREA)
        
        # Try GPU acceleration via OpenCL (UMat)
        try:
            gpu_img = cv2.UMat(img)
            
            # Grayscale
            gray = cv2.cvtColor(gpu_img, cv2.COLOR_BGR2GRAY)
            
            # Blur slightly to remove noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Canny Edge Detection
            edges_gpu = cv2.Canny(blurred, low_threshold, high_threshold)
            
            # Back to CPU for contour finding
            self.edges = edges_gpu.get()
        except Exception:
            # Fallback to CPU
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            self.edges = cv2.Canny(blurred, low_threshold, high_threshold)
        
        # Find Contours
        contours, _ = cv2.findContours(self.edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        self.paths = []
        for cnt in contours:
            # Approximate the contour to reduce number of points (smoother drawing, less ADB commands)
            if len(cnt) < 5: # Skip very small dots
                continue
                
            epsilon = approx_epsilon # 0.1% of arc length is usually good, but fixed value is more predictable for drawing
            approx = cv2.approxPolyDP(cnt, epsilon, False)
            
            # Convert to simple list of tuples
            points = []
            for p in approx:
                points.append((p[0][0], p[0][1]))
            
            self.paths.append(points)
            
        # Create preview image (White background, Black lines) for UI
        preview_h, preview_w = self.edges.shape
        preview_img = np.ones((preview_h, preview_w, 3), dtype=np.uint8) * 255
        
        # Draw contours on preview
        cv2.drawContours(preview_img, contours, -1, (0, 0, 0), 1)
        
        # Convert to PIL for CustomTkinter
        pil_image = Image.fromarray(preview_img)
        
        return pil_image, self.paths
