from rest_framework.renderers import JSONRenderer

class StandardJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context and renderer_context['response'].status_code >= 400:
            if isinstance(data, dict) and 'success' in data:
                return super().render(data, accepted_media_type, renderer_context)
            response_data = {
                'success': False,
                'status_code': renderer_context['response'].status_code,
                'message': 'Error',
                'errors': data,
                'data': None
            }
            return super().render(response_data, accepted_media_type, renderer_context)
            
        if isinstance(data, dict) and 'success' in data:
            return super().render(data, accepted_media_type, renderer_context)
            
        response_data = {
            'success': True,
            'status_code': 200,
            'message': 'Success',
            'data': data,
            'meta': {}
        }
        return super().render(response_data, accepted_media_type, renderer_context)
