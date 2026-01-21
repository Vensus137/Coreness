"""
Submodule for handling buttons
"""


class ButtonMapper:
    """
    Submodule for handling Telegram buttons
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        
        # Maximum length of callback_data for Telegram
        self.callback_data_limit = 60
    
    def _normalize_button_text(self, text: str) -> str:
        """Normalize button text to callback_data"""
        try:
            # Lazy imports of libraries
            import re

            import emoji
            from unidecode import unidecode
            
            # Remove emoji
            text = emoji.replace_emoji(text, replace='')
            
            # Convert to lowercase and strip spaces
            text = text.lower().strip()
            
            # Transliteration
            text = unidecode(text)
            
            # Remove everything except letters, numbers, spaces, hyphens and underscores
            text = re.sub(r'[^a-z0-9 _-]', '', text)
            
            # Replace spaces with underscores
            text = re.sub(r'\s+', '_', text)
            
            # Remove multiple underscores
            text = re.sub(r'_+', '_', text).strip('_')
            
            # Limit length
            return text[:self.callback_data_limit]
            
        except Exception as e:
            self.logger.error(f"Error normalizing button text: {e}")
            return "unknown_button"
    
    def build_reply_markup(self, inline=None, reply=None):
        """Builds keyboard markup for message"""
        try:
            # Priority: inline > reply
            if inline:
                markup = {
                    "inline_keyboard": [
                        [
                            self._build_inline_button(btn) for btn in row
                        ]
                        for row in inline
                    ]
                }
                return markup
            
            # Handle reply keyboard
            if reply is not None:  # Check for None, not truthiness
                if reply == []:  # Empty list = remove keyboard
                    return {"remove_keyboard": True}
                elif reply:  # Non-empty list = show keyboard
                    markup = {
                        "keyboard": [
                            [{"text": btn} for btn in row]
                            for row in reply
                        ],
                        "resize_keyboard": True
                    }
                    return markup
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error creating keyboard markup: {e}")
            return None
    
    def _build_inline_button(self, btn):
        """Builds InlineKeyboardButton with universal logic"""
        try:
            if isinstance(btn, str):
                # Simple string -> callback_data with normalized text
                callback_data = self._normalize_button_text(btn)
                return {
                    "text": btn,
                    "callback_data": callback_data
                }
            elif isinstance(btn, dict):
                text = list(btn.keys())[0]
                value = btn[text]
                
                if isinstance(value, str):
                    # Check if value is a link
                    if value.startswith(("http://", "https://", "tg://")):
                        return {
                            "text": text,
                            "url": value
                        }
                    else:
                        # Otherwise use as callback_data
                        return {
                            "text": text,
                            "callback_data": value
                        }
                else:
                    # Unknown value type -> fallback
                    self.logger.warning(f"[ButtonMapper] Unknown button value type: {type(value)}, value: {repr(value)}")
                    callback_data = self._normalize_button_text(text)
                    return {
                        "text": text,
                        "callback_data": callback_data
                    }
            else:
                # Unknown type -> fallback
                self.logger.warning(f"[ButtonMapper] Unknown button type: {type(btn)}, value: {repr(btn)}")
                callback_data = self._normalize_button_text(str(btn))
                return {
                    "text": str(btn),
                    "callback_data": callback_data
                }
                
        except Exception as e:
            self.logger.error(f"Error creating inline button: {e}, button: {repr(btn)}")
            # Fallback
            return {
                "text": str(btn),
                "callback_data": "unknown_button"
            }
