from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
import logging

logger = logging.getLogger('apps')

def _extract_clean_message(data, fallback_exc):
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        for k, v in data.items():
            if isinstance(v, list) and len(v) > 0:
                return str(v[0])
            elif isinstance(v, str):
                return v
            elif isinstance(v, dict):
                sub = _extract_clean_message(v, fallback_exc)
                if sub:
                    return sub
    elif isinstance(data, list) and len(data) > 0:
        return str(data[0])
    
    msg = str(fallback_exc)
    if 'ErrorDetail' in msg or msg.startswith('{') or msg.startswith('['):
        return 'Validation failed. Please check your inputs.'
    return msg

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        clean_msg = _extract_clean_message(response.data, exc)
        response.data = {
            'success': False,
            'status_code': response.status_code,
            'message': clean_msg,
            'errors': response.data,
            'data': None
        }
    else:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return response
