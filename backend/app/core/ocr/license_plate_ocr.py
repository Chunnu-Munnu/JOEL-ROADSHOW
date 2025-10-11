import easyocr
import cv2
import numpy as np
import re
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

class LicensePlateOCR:
    """OCR engine for Indian vehicle license plates"""
    
    def __init__(self):
        logger.info("Initializing EasyOCR for license plate recognition...")
        
        # Initialize EasyOCR with English (works for Indian plates)
        self.reader = easyocr.Reader(['en'], gpu=True)
        
        # Indian license plate patterns
        self.patterns = {
            'new_format': re.compile(r'[A-Z]{2}\s?\d{2}\s?[A-Z]{1,2}\s?\d{4}'),  # KA 05 MH 1234
            'old_format': re.compile(r'[A-Z]{2}\s?\d{2}\s?\d{4}'),  # KA 01 1234
            'military': re.compile(r'\d{2}\s?[A-Z]{2,3}\s?\d{4}'),  # 01 MH 1234
            'government': re.compile(r'[A-Z]{2}\s?\d{2}\s?G\s?\d{4}')  # DL 01 G 1234
        }
        
        logger.info("License plate OCR initialized")
    
    def extract_plate_from_vehicle(self, frame: np.ndarray, 
                                   vehicle_bbox: List[int]) -> Optional[str]:
        """
        Extract license plate text from a vehicle detection
        
        Args:
            frame: Full video frame
            vehicle_bbox: [x1, y1, x2, y2] bounding box of vehicle
        
        Returns:
            License plate string or None
        """
        try:
            x1, y1, x2, y2 = vehicle_bbox
            
            # Crop vehicle region
            vehicle_crop = frame[y1:y2, x1:x2]
            
            if vehicle_crop.size == 0:
                return None
            
            # Enhance image for better OCR
            enhanced = self._enhance_for_ocr(vehicle_crop)
            
            # Run OCR
            results = self.reader.readtext(enhanced)
            
            # Process results to find plate
            plate_text = self._find_plate_in_results(results)
            
            if plate_text:
                # Clean and validate
                plate_text = self._clean_plate_text(plate_text)
                if self._validate_plate_format(plate_text):
                    logger.info(f"Detected plate: {plate_text}")
                    return plate_text
            
            return None
            
        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            return None
    
    def _enhance_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """Enhance image for better OCR accuracy"""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Resize to larger size for better OCR
        height, width = gray.shape
        scale_factor = max(2.0, 400 / width)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        resized = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            resized,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(binary)
        
        return denoised
    
    def _find_plate_in_results(self, ocr_results: List) -> Optional[str]:
        """Find license plate text from OCR results"""
        if not ocr_results:
            return None
        
        # Concatenate all detected text
        all_text = ' '.join([result[1] for result in ocr_results])
        
        # Try to match against known patterns
        for pattern_name, pattern in self.patterns.items():
            match = pattern.search(all_text.upper())
            if match:
                return match.group(0)
        
        # If no pattern match, return the longest alphanumeric string
        candidates = re.findall(r'[A-Z0-9]{8,}', all_text.upper())
        if candidates:
            return max(candidates, key=len)
        
        return None
    
    def _clean_plate_text(self, text: str) -> str:
        """Clean and normalize plate text"""
        # Remove extra spaces
        text = re.sub(r'\s+', '', text.upper())
        
        # Common OCR mistakes for Indian plates
        replacements = {
            'O': '0',  # Letter O to digit 0
            'I': '1',  # Letter I to digit 1
            'S': '5',  # Sometimes S looks like 5
            'B': '8',  # Sometimes B looks like 8
        }
        
        # Apply replacements intelligently (only for digit positions)
        # Indian format: AA11AA1111
        result = []
        for i, char in enumerate(text):
            # First 2 chars should be letters
            if i < 2:
                result.append(char if char.isalpha() else char)
            # Next 2 should be digits
            elif i < 4:
                if char in replacements and not char.isdigit():
                    result.append(replacements[char])
                else:
                    result.append(char)
            # Next 1-2 chars can be letters
            elif i < 6:
                result.append(char)
            # Last 4 should be digits
            else:
                if char in replacements and not char.isdigit():
                    result.append(replacements[char])
                else:
                    result.append(char)
        
        return ''.join(result)
    
    def _validate_plate_format(self, plate: str) -> bool:
        """Validate if the plate matches Indian format"""
        # Check against patterns
        for pattern in self.patterns.values():
            if pattern.match(plate):
                return True
        
        # Basic validation: should have both letters and numbers
        has_letters = any(c.isalpha() for c in plate)
        has_digits = any(c.isdigit() for c in plate)
        proper_length = 8 <= len(plate) <= 12
        
        return has_letters and has_digits and proper_length
    
    def detect_plate_format(self, plate: str) -> str:
        """Determine the format/type of the license plate"""
        if self.patterns['military'].match(plate):
            return 'military'
        elif self.patterns['government'].match(plate):
            return 'government'
        elif self.patterns['new_format'].match(plate):
            return 'civilian_new'
        elif self.patterns['old_format'].match(plate):
            return 'civilian_old'
        else:
            return 'unknown'