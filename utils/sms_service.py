import requests
from config import Config

class DreamSMS:
    BASE_URL = "https://sms.dreampartners.online/api/sms"
    
    def __init__(self):
        self.api_key = Config.SMS_API_KEY

    def _parse_error_message(self, response_data):
        """Парсит ошибку API и возвращает понятное сообщение для пользователя"""
        error_msg = response_data.get('message', 'Неизвестная ошибка')
        error_msg_lower = error_msg.lower()
        
        # Проверяем, что номер не зарегистрирован в боте
        if any(keyword in error_msg_lower for keyword in ['не зарегистрирован', 'not registered', 'не найден', 'not found', 'не найден в боте', 'user not found']):
            return "Этот номер не зарегистрирован в боте. Пожалуйста, сначала запустите бота @dream_smsbot и зарегистрируйтесь с этим номером телефона."
        
        # Проверяем другие типичные ошибки
        if 'неверный номер' in error_msg_lower or 'invalid phone' in error_msg_lower:
            return "Неверный формат номера телефона. Используйте формат +79991234567"
        
        # Возвращаем исходное сообщение или общее
        return error_msg if error_msg != 'Неизвестная ошибка' else "Ошибка отправки кода. Попробуйте позже."

    def send_code(self, phone, code):
        """Send verification code to Telegram via DreamSMS"""
        try:
            payload = {
                "api_key": self.api_key,
                "phone": phone,
                "code": str(code)
            }
            resp = requests.post(f"{self.BASE_URL}/send", json=payload, timeout=10)
            result = resp.json()
            
            # Если ошибка, обрабатываем сообщение
            if not result.get('success'):
                result['message'] = self._parse_error_message(result)
            
            return result
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Превышено время ожидания. Проверьте подключение к интернету."}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": "Ошибка соединения с сервисом. Попробуйте позже."}
        except Exception as e:
            return {"success": False, "message": "Неожиданная ошибка. Попробуйте позже."}

    def verify_code(self, phone, code):
        """Verify code (optional, mainly used if we want user data)"""
        try:
            payload = {
                "phone": phone,
                "code": str(code),
                "api_key": self.api_key
            }
            resp = requests.post(f"{self.BASE_URL}/verify", json=payload, timeout=10)
            result = resp.json()
            
            # Если ошибка, обрабатываем сообщение
            if not result.get('success'):
                result['message'] = self._parse_error_message(result)
            
            return result
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Превышено время ожидания. Проверьте подключение к интернету."}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": "Ошибка соединения с сервисом. Попробуйте позже."}
        except Exception as e:
            return {"success": False, "message": "Неожиданная ошибка. Попробуйте позже."}



