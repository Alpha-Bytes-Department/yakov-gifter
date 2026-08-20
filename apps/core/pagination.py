from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination, CursorPagination
from rest_framework.response import Response

class StandardPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Success',
            'data': data,
            'meta': {
                'pagination': {
                    'count': self.page.paginator.count,
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link(),
                    'current_page': self.page.number,
                    'total_pages': self.page.paginator.num_pages
                }
            }
        })

class StandardLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Success',
            'data': data,
            'meta': {
                'pagination': {
                    'count': self.count,
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link(),
                    'limit': self.limit,
                    'offset': self.offset
                }
            }
        })

class StandardCursorPagination(CursorPagination):
    page_size = 20
    ordering = '-created_at'
    
    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Success',
            'data': data,
            'meta': {
                'pagination': {
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link()
                }
            }
        })
